#!/usr/bin/env sh
set -eu

usage() {
  printf 'Usage: %s user@host [commit|tag]\n' "$(basename "$0")" >&2
  printf '  If no commit/tag given, rolls back to HEAD~1.\n' >&2
  exit 1
}

if [ $# -lt 1 ]; then
  usage
fi

VPS_HOST="$1"
TARGET="${2:-HEAD~1}"
REMOTE_DIR="/opt/edge-agent"
COMPOSE_FILE="$REMOTE_DIR/infra/compose/docker-compose.prod.yml"

printf '==> Rolling back %s to %s\n' "$VPS_HOST" "$TARGET"

# Stop current containers
printf '==> Stopping services\n'
ssh "$VPS_HOST" "docker compose -f $COMPOSE_FILE stop"

# Revert code
printf '==> Reverting to %s\n' "$TARGET"
ssh "$VPS_HOST" "cd $REMOTE_DIR && git checkout $TARGET"

# Restart services
printf '==> Restarting services\n'
ssh "$VPS_HOST" "cd $REMOTE_DIR && \
  docker compose -f $COMPOSE_FILE pull && \
  docker compose -f $COMPOSE_FILE up -d --remove-orphans --build"

# Verify health
printf '==> Verifying rollback health\n'
ATTEMPTS=0
MAX_ATTEMPTS=30
while [ "$ATTEMPTS" -lt "$MAX_ATTEMPTS" ]; do
  HEALTHY=$(ssh "$VPS_HOST" "docker compose -f $COMPOSE_FILE ps --format '{{.Health}}' 2>/dev/null | grep -c 'healthy'" || echo "0")
  TOTAL=$(ssh "$VPS_HOST" "docker compose -f $COMPOSE_FILE ps -q 2>/dev/null | wc -l" || echo "0")
  if [ "$HEALTHY" -ge "$TOTAL" ] && [ "$TOTAL" -gt 0 ]; then
    printf '==> All %s services healthy. Rollback complete.\n' "$TOTAL"
    exit 0
  fi
  ATTEMPTS=$((ATTEMPTS + 1))
  sleep 5
done

printf 'WARNING: Not all services healthy after %s seconds. Check manually.\n' "$((MAX_ATTEMPTS * 5))" >&2
ssh "$VPS_HOST" "docker compose -f $COMPOSE_FILE ps"
exit 1
