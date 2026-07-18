#!/usr/bin/env sh
set -u

AQUANTAI_PORT="${AQUANTAI_PORT:-8000}"
export AQUANTAI_PORT
DASHBOARD_URL="http://127.0.0.1:${AQUANTAI_PORT}/dashboard"
HEALTH_URL="http://127.0.0.1:${AQUANTAI_PORT}/health"
MAX_ATTEMPTS=30

fail() {
  printf '%s\n' "$1" >&2
  exit 1
}

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd) || fail "Could not find the AQuantAI folder. Run this script from the repository checkout."
cd "$SCRIPT_DIR" || fail "Could not open the AQuantAI folder."

command -v docker >/dev/null 2>&1 || fail "Docker was not found. Install Docker Desktop, then run this script again."
docker compose version >/dev/null 2>&1 || fail "Docker Compose was not found. Update Docker Desktop so the docker compose command is available."
docker info >/dev/null 2>&1 || fail "Docker Desktop is not running or is still starting. Start Docker Desktop, then try again."
command -v curl >/dev/null 2>&1 || fail "curl is needed to check the local Dashboard. Install curl, then try again."

if [ ! -f .env ]; then
  [ -f .env.example ] || fail ".env.example was not found. Restore it from the repository before starting AQuantAI."
  cp .env.example .env || fail "Could not create .env. Check that you can write to this repository folder, then try again."
  printf '%s\n' "Created .env from .env.example."
else
  printf '%s\n' "Keeping your existing .env file unchanged."
fi

docker compose config --quiet >/dev/null 2>&1 || fail "Docker Compose could not read the local configuration. Check .env against .env.example; your existing .env was not changed."

printf '%s\n' "Starting AQuantAI. The first launch may take a few minutes while Docker builds the local services."
if ! docker compose up --build -d; then
  printf '%s\n' "Docker could not build or start AQuantAI. Review the Docker error above." >&2
  printf '%s\n' "If it mentions pip, setuptools, or package downloads, check the internet or proxy used by Docker and retry." >&2
  printf '%s\n' "If it mentions port $AQUANTAI_PORT, close the conflicting service or set AQUANTAI_PORT to another available local port." >&2
  fail "No volumes, images, .env files, or user files were deleted."
fi

attempt=1
while [ "$attempt" -le "$MAX_ATTEMPTS" ]; do
  status=$(curl --silent --show-error --output /dev/null --write-out '%{http_code}' --max-time 2 "$HEALTH_URL" 2>/dev/null || true)
  if [ "$status" = "200" ]; then
    if command -v open >/dev/null 2>&1; then
      open "$DASHBOARD_URL"
    elif command -v xdg-open >/dev/null 2>&1; then
      xdg-open "$DASHBOARD_URL" >/dev/null 2>&1 || true
    else
      printf '%s\n' "AQuantAI is ready. Open $DASHBOARD_URL in your browser."
      exit 0
    fi
    printf '%s\n' "AQuantAI is ready. The Dashboard is opening at $DASHBOARD_URL"
    exit 0
  fi
  printf '%s\n' "Waiting for AQuantAI to become ready (attempt $attempt of $MAX_ATTEMPTS)..."
  sleep 2
  attempt=$((attempt + 1))
done

printf '%s\n' "AQuantAI did not become ready before the health-check timeout." >&2
printf '%s\n' "Current Docker Compose status:" >&2
docker compose ps >&2 || true
printf '%s\n' "Recent app logs:" >&2
docker compose logs --tail 30 app >&2 || true
printf '%s\n' "Use ./stop-aquantai.sh to stop partially started services without deleting data." >&2
fail "Check the messages above, confirm port $AQUANTAI_PORT is available, then run this launcher again."
