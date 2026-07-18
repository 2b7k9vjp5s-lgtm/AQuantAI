#!/usr/bin/env sh
set -u

fail() {
  printf '%s\n' "$1" >&2
  exit 1
}

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd) || fail "Could not find the AQuantAI folder. Run this script from the repository checkout."
cd "$SCRIPT_DIR" || fail "Could not open the AQuantAI folder."

command -v docker >/dev/null 2>&1 || fail "Docker was not found. Install or start Docker Desktop before stopping AQuantAI."
docker compose version >/dev/null 2>&1 || fail "Docker Compose was not found. Update Docker Desktop so the docker compose command is available."
docker info >/dev/null 2>&1 || fail "Docker Desktop is not running. Start Docker Desktop and try again."
docker compose config --quiet >/dev/null 2>&1 || fail "Docker Compose could not read the local configuration. Check .env against .env.example. No volumes, images, .env files, or user files were deleted."

printf '%s\n' "Stopping AQuantAI services. Your .env file, Docker volumes, images, and local files will be kept."
docker compose down || fail "Docker could not stop AQuantAI. Check Docker Desktop and try again."
printf '%s\n' "AQuantAI services have stopped."
