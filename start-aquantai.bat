@echo off
setlocal EnableExtensions DisableDelayedExpansion

set "SCRIPT_DIR=%~dp0"
set "DASHBOARD_URL=http://127.0.0.1:8000/dashboard"
set "HEALTH_URL=http://127.0.0.1:8000/health"
set "MAX_ATTEMPTS=30"
set "RESULT_WAIT_SECONDS=10"
set "PUSHD_OK=0"
set "EXIT_CODE=1"
if /I "%~1"=="--no-wait" set "RESULT_WAIT_SECONDS=0"

pushd "%SCRIPT_DIR%" >nul 2>&1
if errorlevel 1 (
  echo Could not open the AQuantAI folder. Move this file back into the repository folder and try again.
  goto :finish
)
set "PUSHD_OK=1"

where docker >nul 2>&1
if errorlevel 1 goto :docker_missing

"%ComSpec%" /d /c docker compose version >nul 2>&1
if errorlevel 1 goto :compose_missing

"%ComSpec%" /d /c docker info >nul 2>&1
if errorlevel 1 goto :daemon_unavailable

if not exist ".env" (
  if not exist ".env.example" goto :env_template_missing
    copy /-y ".env.example" ".env" >nul
  if errorlevel 1 goto :env_create_failed
  echo Created .env from .env.example.
) else (
  echo Keeping your existing .env file unchanged.
)

"%ComSpec%" /d /c docker compose config --quiet >nul 2>&1
if errorlevel 1 goto :compose_config_invalid

echo Starting AQuantAI. The first launch may take a few minutes while Docker builds the local services.
"%ComSpec%" /d /c docker compose up --build -d
if errorlevel 1 goto :compose_start_failed

for /L %%I in (1,1,%MAX_ATTEMPTS%) do (
  call :check_health
  if not errorlevel 1 goto :dashboard_ready
  echo Waiting for AQuantAI to become ready ^(attempt %%I of %MAX_ATTEMPTS%^)...
  "%ComSpec%" /d /c timeout /t 2 /nobreak >nul
)

echo AQuantAI did not become ready before the health-check timeout.
echo Current Docker Compose status:
"%ComSpec%" /d /c docker compose ps
echo Recent app logs:
"%ComSpec%" /d /c docker compose logs --tail 30 app
echo Check the messages above, confirm port 8000 is available, then run this launcher again.
echo You can use stop-aquantai.bat to stop any partially started services without deleting data.
goto :failure

:dashboard_ready
call :open_dashboard
if errorlevel 1 (
  echo AQuantAI is ready, but Windows could not open the browser. Open %DASHBOARD_URL%
) else (
  echo AQuantAI is ready. The Dashboard is opening at %DASHBOARD_URL%
)
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

:compose_config_invalid
echo Docker Compose could not read the local configuration. Check .env against .env.example, then try again.
echo Your existing .env was not changed.
goto :failure

:compose_start_failed
echo Docker could not build or start AQuantAI. Review the Docker error above.
echo If it mentions pip, setuptools, or package downloads, check the internet or proxy used by Docker Desktop and retry.
echo If it mentions port 8000, close the program using port 8000, then run this launcher again.
echo To find the process, run: netstat -ano ^| findstr :8000
echo No volumes, images, .env files, or user files were deleted.
goto :failure

:failure
set "EXIT_CODE=1"
goto :finish

:success
set "EXIT_CODE=0"
goto :finish

:finish
if "%PUSHD_OK%"=="1" popd
if not "%RESULT_WAIT_SECONDS%"=="0" (
  echo.
  echo This window will close in %RESULT_WAIT_SECONDS% seconds.
  "%ComSpec%" /d /c timeout /t %RESULT_WAIT_SECONDS% /nobreak >nul 2>&1
)
exit /b %EXIT_CODE%

:check_health
"%ComSpec%" /d /c powershell -NoProfile -Command "$response = Invoke-WebRequest -UseBasicParsing -Uri 'http://127.0.0.1:8000/health' -TimeoutSec 2 -ErrorAction Stop; if ($response.StatusCode -eq 200) { exit 0 }; exit 1" >nul 2>&1
exit /b %errorlevel%

:open_dashboard
"%ComSpec%" /d /c powershell -NoProfile -Command "Start-Process 'http://127.0.0.1:8000/dashboard'" >nul 2>&1
exit /b %errorlevel%
