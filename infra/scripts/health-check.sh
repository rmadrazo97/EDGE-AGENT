#!/usr/bin/env sh
set -eu

usage() {
  printf 'Usage: %s user@host\n' "$(basename "$0")" >&2
  exit 1
}

if [ $# -lt 1 ]; then
  usage
fi

VPS_HOST="$1"
REMOTE_DIR="/opt/edge-agent"
COMPOSE_FILE="$REMOTE_DIR/infra/compose/docker-compose.prod.yml"
ERRORS=0

printf '=== Edge-Agent Health Report: %s ===\n' "$VPS_HOST"
printf 'Timestamp: %s\n\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"

# 1. Check container status
printf '--- Container Status ---\n'
CONTAINER_STATUS=$(ssh "$VPS_HOST" "docker compose -f $COMPOSE_FILE ps --format '{{.Name}}\t{{.State}}\t{{.Health}}' 2>/dev/null" || echo "FAILED")
if [ "$CONTAINER_STATUS" = "FAILED" ]; then
  printf 'ERROR: Could not query container status\n'
  ERRORS=$((ERRORS + 1))
else
  printf '%s\n' "$CONTAINER_STATUS"
  NOT_RUNNING=$(printf '%s\n' "$CONTAINER_STATUS" | grep -cv 'running' || true)
  if [ "$NOT_RUNNING" -gt 0 ]; then
    printf 'WARNING: %s container(s) not in running state\n' "$NOT_RUNNING"
    ERRORS=$((ERRORS + 1))
  fi
  UNHEALTHY=$(printf '%s\n' "$CONTAINER_STATUS" | grep -c 'unhealthy' || true)
  if [ "$UNHEALTHY" -gt 0 ]; then
    printf 'WARNING: %s container(s) unhealthy\n' "$UNHEALTHY"
    ERRORS=$((ERRORS + 1))
  fi
fi
printf '\n'

# 2. Check API health
printf '--- API Health ---\n'
API_HEALTH=$(ssh "$VPS_HOST" "docker compose -f $COMPOSE_FILE exec -T hummingbot-api python -c \"import urllib.request; print(urllib.request.urlopen('http://localhost:8000/health', timeout=5).read().decode())\" 2>/dev/null" || echo "UNREACHABLE")
if [ "$API_HEALTH" = "UNREACHABLE" ]; then
  printf 'ERROR: API health endpoint unreachable\n'
  ERRORS=$((ERRORS + 1))
else
  printf 'API: OK (%s)\n' "$API_HEALTH"
fi
printf '\n'

# 3. Check disk space
printf '--- Disk Space ---\n'
DISK_INFO=$(ssh "$VPS_HOST" "df -h / | tail -1" 2>/dev/null || echo "FAILED")
if [ "$DISK_INFO" = "FAILED" ]; then
  printf 'ERROR: Could not query disk space\n'
  ERRORS=$((ERRORS + 1))
else
  printf '%s\n' "$DISK_INFO"
  DISK_PCT=$(printf '%s' "$DISK_INFO" | awk '{gsub(/%/,""); print $5}')
  if [ "$DISK_PCT" -gt 85 ] 2>/dev/null; then
    printf 'WARNING: Disk usage at %s%%\n' "$DISK_PCT"
    ERRORS=$((ERRORS + 1))
  fi
fi
printf '\n'

# 4. Check agent process
printf '--- Agent Processes ---\n'
AGENT_PROCS=$(ssh "$VPS_HOST" "docker compose -f $COMPOSE_FILE exec -T edge-agent-agents pgrep -fa 'agents\.' 2>/dev/null" || echo "NONE")
if [ "$AGENT_PROCS" = "NONE" ]; then
  printf 'WARNING: No agent processes detected\n'
  ERRORS=$((ERRORS + 1))
else
  printf '%s\n' "$AGENT_PROCS"
fi
printf '\n'

# 5. Docker disk usage
printf '--- Docker Disk Usage ---\n'
ssh "$VPS_HOST" "docker system df 2>/dev/null" || printf 'Could not query docker disk usage\n'
printf '\n'

# Summary
printf '=== Summary ===\n'
if [ "$ERRORS" -eq 0 ]; then
  printf 'STATUS: HEALTHY (all checks passed)\n'
else
  printf 'STATUS: DEGRADED (%s issue(s) detected)\n' "$ERRORS"
  exit 1
fi
