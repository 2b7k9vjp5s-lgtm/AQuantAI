@echo off
setlocal EnableExtensions DisableDelayedExpansion

set "SCRIPT_DIR=%~dp0"
if not defined AQUANTAI_PORT set "AQUANTAI_PORT=8200"
set "DASHBOARD_URL=http://127.0.0.1:%AQUANTAI_PORT%/dashboard"
set "HEALTH_URL=http://127.0.0.1:%AQUANTAI_PORT%/health"
set "MAX_ATTEMPTS=30"

pushd "%SCRIPT_DIR%" >nul 2>&1
if errorlevel 1 (
  echo Could not open the AQuantAI folder. Move this file back into the repository folder and try again.
  exit /b 1
)

where docker >nul 2>&1
if errorlevel 1 goto :docker_missing

docker compose version >nul 2>&1
if errorlevel 1 goto :compose_missing

docker info >nul 2>&1
if errorlevel 1 goto :daemon_unavailable

if not exist ".env" (
  if not exist ".env.example" goto :env_template_missing
    copy /-y ".env.example" ".env" >nul
  if errorlevel 1 goto :env_create_failed
  echo Created .env from .env.example.
) else (
  echo Keeping your existing .env file unchanged.
)

echo Starting AQuantAI. The first launch may take a few minutes while Docker builds the local services.
docker compose up --build -d
if errorlevel 1 goto :compose_start_failed

for /L %%I in (1,1,%MAX_ATTEMPTS%) do (
  call :check_health
  if not errorlevel 1 goto :dashboard_ready
  echo Waiting for AQuantAI to become ready (attempt %%I of %MAX_ATTEMPTS%)...
  timeout /t 2 /nobreak >nul
)

echo AQuantAI did not become ready. Check that Docker Desktop is running and that port %AQUANTAI_PORT% is available.
goto :failure

:dashboard_ready
start "" "%DASHBOARD_URL%"
echo AQuantAI is ready. The Dashboard is opening at %DASHBOARD_URL%
goto :success

:docker_missing
echo Docker was not found. Install Docker Desktop, then run this file again.
goto :failure

:compose_missing
echo Docker Compose was not found. Update Docker Desktop so the "docker compose" command is available.
goto :failure

:daemon_unavailable
echo Docker Desktop is not running or is still starting. Start Docker Desktop, wait for it to finish, then try again.
goto :failure

:env_template_missing
echo .env.example was not found. Restore it from the repository before starting AQuantAI.
goto :failure

:env_create_failed
echo Could not create .env. Check that you can write to this repository folder, then try again.
goto :failure

:compose_start_failed
echo Docker could not build or start AQuantAI. Check Docker Desktop, your internet connection for a first build, and whether port %AQUANTAI_PORT% is available, then try again.
goto :failure

:failure
popd
exit /b 1

:success
popd
exit /b 0

:check_health
powershell -NoProfile -Command "$response = Invoke-WebRequest -UseBasicParsing -Uri '%HEALTH_URL%' -TimeoutSec 2 -ErrorAction Stop; if ($response.StatusCode -eq 200) { exit 0 }; exit 1" >nul 2>&1
exit /b %errorlevel%
