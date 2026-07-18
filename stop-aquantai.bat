@echo off
setlocal EnableExtensions DisableDelayedExpansion

set "SCRIPT_DIR=%~dp0"

pushd "%SCRIPT_DIR%" >nul 2>&1
if errorlevel 1 (
  echo Could not open the AQuantAI folder. Move this file back into the repository folder and try again.
  exit /b 1
)

where docker >nul 2>&1
if errorlevel 1 (
  echo Docker was not found. Install or start Docker Desktop before stopping AQuantAI.
  popd
  exit /b 1
)

docker compose version >nul 2>&1
if errorlevel 1 (
  echo Docker Compose was not found. Update Docker Desktop so the "docker compose" command is available.
  popd
  exit /b 1
)

docker info >nul 2>&1
if errorlevel 1 (
  echo Docker Desktop is not running. Start Docker Desktop and try again.
  popd
  exit /b 1
)

docker compose config --quiet >nul 2>&1
if errorlevel 1 (
  echo Docker Compose could not read the local configuration. Check .env against .env.example and try again.
  echo No volumes, images, .env files, or user files were deleted.
  popd
  exit /b 1
)

echo Stopping AQuantAI services. Your .env file, Docker volumes, images, and local files will be kept.
docker compose down
if errorlevel 1 (
  echo Docker could not stop AQuantAI. Check Docker Desktop and try again.
  popd
  exit /b 1
)

echo AQuantAI services have stopped.
popd
exit /b 0
