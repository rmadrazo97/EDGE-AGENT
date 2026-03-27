#!/usr/bin/env sh
set -eu

ROOT_DIR="$(CDPATH='' cd -- "$(dirname -- "$0")/../.." && pwd)"
COMPOSE_FILE="$ROOT_DIR/infra/compose/docker-compose.dev.yml"

docker compose -f "$COMPOSE_FILE" logs -f "$@"

