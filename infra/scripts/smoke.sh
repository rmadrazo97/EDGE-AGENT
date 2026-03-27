#!/usr/bin/env sh
set -eu

ROOT_DIR="$(CDPATH='' cd -- "$(dirname -- "$0")/../.." && pwd)"
COMPOSE_FILE="$ROOT_DIR/infra/compose/docker-compose.dev.yml"

wait_for_http() {
  url="$1"
  timeout_seconds="$2"
  elapsed=0

  while [ "$elapsed" -lt "$timeout_seconds" ]; do
    if curl -fsS "$url" >/dev/null 2>&1; then
      return 0
    fi
    sleep 2
    elapsed=$((elapsed + 2))
  done

  printf 'Timed out waiting for %s\n' "$url" >&2
  return 1
}

wait_for_http "http://localhost:8000/health" 120
wait_for_http "http://localhost:8000/docs" 120
wait_for_http "http://localhost:18083" 120

docker compose -f "$COMPOSE_FILE" exec -T postgres pg_isready -U hbot -d hummingbot_api >/dev/null
docker compose -f "$COMPOSE_FILE" ps --status running --services | grep -qx 'hummingbot-mcp'

printf 'Infrastructure smoke checks passed.\n'

