#!/usr/bin/env bash
# Local launcher for the MakeMyTrip Autonomous Web Operations Agent stack.
#
# Ports/paths below are verified against the repo's actual docker-compose.yml
# and backend/app/main.py (Phase 36 of the internal project blueprint). Do not
# change them without re-checking those files first.
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

COMPOSE_PROJECT_NAME="${COMPOSE_PROJECT_NAME:-}"
WAIT_TIMEOUT_SECONDS="${WAIT_TIMEOUT_SECONDS:-600}"
NO_BUILD=0
FOLLOW_LOGS=0
RESET_DATA=0

usage() {
  cat <<'USAGE'
MakeMyTrip Autonomous Web Operations Agent: local launcher

Usage:
  bash scripts/run-local.sh [options]

Options:
  --no-build       Start existing images without rebuilding.
  --logs           Follow service logs after startup.
  --reset-data     Remove local Docker volumes before starting (wipes Postgres/MinIO/Redis data).
  -h, --help       Show this help.

Environment:
  WAIT_TIMEOUT_SECONDS=600         Health wait timeout per service.
  COMPOSE_PROJECT_NAME=mmt-ops-agent
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --no-build) NO_BUILD=1 ;;
    --logs) FOLLOW_LOGS=1 ;;
    --reset-data) RESET_DATA=1 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown option: $1"; usage; exit 2 ;;
  esac
  shift
done

log()  { printf '\n\033[1;34m%s\033[0m\n' "$1"; }
fail() { printf '\n\033[1;31m%s\033[0m\n' "$1" >&2; exit 1; }
require_command() { command -v "$1" >/dev/null 2>&1 || fail "Missing required command: $1"; }
compose() {
  if [[ -n "$COMPOSE_PROJECT_NAME" ]]; then
    COMPOSE_PROJECT_NAME="$COMPOSE_PROJECT_NAME" docker compose "$@"
  else
    docker compose "$@"
  fi
}

ensure_env() {
  if [[ ! -f .env ]]; then
    [[ -f .env.example ]] || fail ".env.example is missing."
    cp .env.example .env
    log "Created .env from .env.example with local development defaults."
    log "NOTE: set GEMINI_API_KEY in .env for real AI planning/reasoning/chat."
    log "Without it, the system automatically falls back to Ollama (if configured) or"
    log "deterministic-only completion. The pipeline still runs, but AI narrative won't appear."
  else
    log "Using existing .env."
  fi
}

wait_for_url() {
  local name="$1" url="$2" started
  started="$(date +%s)"
  printf 'Waiting for %s' "$name"
  while true; do
    if curl -fsS "$url" >/dev/null 2>&1; then
      printf ' ready\n'; return 0
    fi
    if (( $(date +%s) - started > WAIT_TIMEOUT_SECONDS )); then
      printf '\n'; compose ps
      fail "$name did not become ready at $url within ${WAIT_TIMEOUT_SECONDS}s. Run: docker compose logs -f"
    fi
    printf '.'; sleep 3
  done
}

require_command docker
require_command curl
docker compose version >/dev/null 2>&1 || fail "Docker Compose is not available."
docker info >/dev/null 2>&1 || fail "Docker is not running or inaccessible."

ensure_env

if (( RESET_DATA == 1 )); then
  log "Removing local containers and volumes (Postgres/MinIO/Redis data will be wiped)."
  compose down -v --remove-orphans
fi

log "Starting MakeMyTrip Web Operations Agent stack."
if (( NO_BUILD == 1 )); then
  compose up -d --remove-orphans
else
  compose up -d --build --remove-orphans
fi

log "Waiting for services."
wait_for_url "API health"            "http://localhost:8000/api/health"
wait_for_url "Mock site"             "http://localhost:5050/"
wait_for_url "MinIO console"         "http://localhost:9001/"
wait_for_url "Frontend"              "http://localhost:5173"

log "Applying database migrations (idempotent, safe to re-run)."
compose exec -T api alembic -c backend/alembic.ini upgrade head \
  || fail "Migrations failed. Run: docker compose logs api"

log "Seeding demo users (idempotent, safe to re-run)."
compose exec -T api python -m backend.seed_users \
  || fail "Seeding demo users failed. Run: docker compose logs api"

log "Registering the mock site as an allowlisted Source (idempotent, safe to re-run)."
compose exec -T api python -m backend.seed_sources \
  || fail "Seeding source registry failed. Run: docker compose logs api"

log "Localhost is ready."
cat <<'URLS'

Open these URLs:
  Ops Agent UI (login):    http://localhost:5173
  Mock site (demo target): http://localhost:5050
  API health:               http://localhost:8000/api/health
  API docs:                 http://localhost:8000/docs
  MinIO console:            http://localhost:9001

Demo login accounts (seeded by backend/seed_users.py, one per role):
  ops@makemytrip.demo / growth@makemytrip.demo / reviewer@makemytrip.demo /
  owner@makemytrip.demo / admin@makemytrip.demo
  (see backend/seed_users.py for the shared demo password.)

Useful commands:
  docker compose ps
  docker compose logs -f frontend api worker browser-worker scheduler
  docker compose down

Fast restart after the first run:
  bash scripts/run-local.sh --no-build

Clean local data and start fresh:
  bash scripts/run-local.sh --reset-data
URLS

if (( FOLLOW_LOGS == 1 )); then
  log "Following app logs. Ctrl+C stops watching; services keep running."
  compose logs -f frontend api worker browser-worker scheduler
fi
