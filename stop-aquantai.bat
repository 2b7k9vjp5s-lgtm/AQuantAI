@echo off
setlocal EnableExtensions DisableDelayedExpansion

set "SCRIPT_DIR=%~dp0"
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
if errorlevel 1 (
  echo Docker was not found. Install or start Docker Desktop before stopping AQuantAI.
  goto :failure
)

"%ComSpec%" /d /c docker compose version >nul 2>&1
if errorlevel 1 (
  echo Docker Compose was not found. Update Docker Desktop so the "docker compose" command is available.
  goto :failure
)

"%ComSpec%" /d /c docker info >nul 2>&1
if errorlevel 1 (
  echo Docker Desktop is not running. Start Docker Desktop and try again.
  goto :failure
)

"%ComSpec%" /d /c docker compose config --quiet >nul 2>&1
if errorlevel 1 (
  echo Docker Compose could not read the local configuration. Check .env against .env.example and try again.
  echo No volumes, images, .env files, or user files were deleted.
  goto :failure
)

echo Stopping AQuantAI services. Your .env file, Docker volumes, images, and local files will be kept.
"%ComSpec%" /d /c docker compose down
if errorlevel 1 (
  echo Docker could not stop AQuantAI. Check Docker Desktop and try again.
  goto :failure
)

echo AQuantAI services have stopped.
set "EXIT_CODE=0"
goto :finish

:failure
set "EXIT_CODE=1"

:finish
if "%PUSHD_OK%"=="1" popd
if not "%RESULT_WAIT_SECONDS%"=="0" (
  echo.
  echo This window will close in %RESULT_WAIT_SECONDS% seconds.
  "%ComSpec%" /d /c timeout /t %RESULT_WAIT_SECONDS% /nobreak >nul 2>&1
)
exit /b %EXIT_CODE%
