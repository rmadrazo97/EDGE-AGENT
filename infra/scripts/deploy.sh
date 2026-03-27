#!/usr/bin/env sh
set -eu

usage() {
  printf 'Usage: %s [--with-env] user@host\n' "$(basename "$0")" >&2
  exit 1
}

WITH_ENV=0
VPS_HOST=""

while [ $# -gt 0 ]; do
  case "$1" in
    --with-env) WITH_ENV=1; shift ;;
    -*) printf 'Unknown option: %s\n' "$1" >&2; usage ;;
    *) VPS_HOST="$1"; shift ;;
  esac
done

if [ -z "$VPS_HOST" ]; then
  usage
fi

ROOT_DIR="$(CDPATH='' cd -- "$(dirname -- "$0")/../.." && pwd)"
REMOTE_DIR="/opt/edge-agent"

printf '==> Deploying to %s\n' "$VPS_HOST"

# Check if containers are already running on the remote host
RUNNING=$(ssh "$VPS_HOST" "docker compose -f $REMOTE_DIR/infra/compose/docker-compose.prod.yml ps --status running -q 2>/dev/null | wc -l" 2>/dev/null || echo "0")

if [ "$RUNNING" -gt 0 ]; then
  printf 'WARNING: %s containers are currently running on %s.\n' "$RUNNING" "$VPS_HOST"
  printf 'Continue and restart services? [y/N] '
  read -r CONFIRM
  case "$CONFIRM" in
    [yY]*) ;;
    *) printf 'Aborted.\n'; exit 0 ;;
  esac
fi

# Sync code to VPS
printf '==> Syncing code to %s:%s\n' "$VPS_HOST" "$REMOTE_DIR"
rsync -az --delete \
  --exclude='.env' \
  --exclude='runtime/' \
  --exclude='.git/' \
  --exclude='__pycache__/' \
  --exclude='.venv/' \
  --exclude='.mypy_cache/' \
  --exclude='*.pyc' \
  "$ROOT_DIR/" "$VPS_HOST:$REMOTE_DIR/"

# Optionally copy env files
if [ "$WITH_ENV" -eq 1 ]; then
  printf '==> Copying env files\n'
  rsync -az "$ROOT_DIR/infra/env/" "$VPS_HOST:$REMOTE_DIR/infra/env/"
fi

# Deploy on VPS
printf '==> Pulling images and starting services\n'
ssh "$VPS_HOST" "cd $REMOTE_DIR && \
  docker compose -f infra/compose/docker-compose.prod.yml pull && \
  docker compose -f infra/compose/docker-compose.prod.yml up -d --remove-orphans --build"

# Verify health
printf '==> Verifying deployment health\n'
ATTEMPTS=0
MAX_ATTEMPTS=30
while [ "$ATTEMPTS" -lt "$MAX_ATTEMPTS" ]; do
  HEALTHY=$(ssh "$VPS_HOST" "docker compose -f $REMOTE_DIR/infra/compose/docker-compose.prod.yml ps --format '{{.Health}}' 2>/dev/null | grep -c 'healthy'" || echo "0")
  TOTAL=$(ssh "$VPS_HOST" "docker compose -f $REMOTE_DIR/infra/compose/docker-compose.prod.yml ps -q 2>/dev/null | wc -l" || echo "0")
  if [ "$HEALTHY" -ge "$TOTAL" ] && [ "$TOTAL" -gt 0 ]; then
    printf '==> All %s services healthy. Deployment complete.\n' "$TOTAL"
    exit 0
  fi
  ATTEMPTS=$((ATTEMPTS + 1))
  sleep 5
done

printf 'WARNING: Not all services healthy after %s seconds. Check manually.\n' "$((MAX_ATTEMPTS * 5))" >&2
ssh "$VPS_HOST" "docker compose -f $REMOTE_DIR/infra/compose/docker-compose.prod.yml ps"
exit 1
