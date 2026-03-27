#!/usr/bin/env sh
set -eu

ROOT_DIR="$(CDPATH='' cd -- "$(dirname -- "$0")/../.." && pwd)"
COMPOSE_FILE="$ROOT_DIR/infra/compose/docker-compose.dev.yml"

"$ROOT_DIR/infra/scripts/ensure-dev-env.sh"
mkdir -p \
  "$ROOT_DIR/runtime/hummingbot-api/bots" \
  "$ROOT_DIR/runtime/hummingbot-api/credentials" \
  "$ROOT_DIR/runtime/hummingbot-mcp"

docker compose -f "$COMPOSE_FILE" up -d --remove-orphans "$@"

