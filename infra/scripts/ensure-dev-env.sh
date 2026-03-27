#!/usr/bin/env sh
set -eu

ROOT_DIR="$(CDPATH='' cd -- "$(dirname -- "$0")/../.." && pwd)"
API_ENV="$ROOT_DIR/infra/env/api.env"
MCP_ENV="$ROOT_DIR/infra/env/mcp.env"

if [ ! -f "$API_ENV" ]; then
  cat >"$API_ENV" <<'EOF'
USERNAME=admin
PASSWORD=admin
CONFIG_PASSWORD=local_dev_only_change_me
DATABASE_URL=postgresql+asyncpg://hbot:hummingbot-api@postgres:5432/hummingbot_api
BROKER_HOST=emqx
BROKER_PORT=1883
BROKER_USERNAME=admin
BROKER_PASSWORD=public
EOF
  printf 'Created %s with local development defaults.\n' "$API_ENV"
fi

if [ ! -f "$MCP_ENV" ]; then
  cat >"$MCP_ENV" <<'EOF'
HUMMINGBOT_API_URL=http://hummingbot-api:8000
HUMMINGBOT_USERNAME=admin
HUMMINGBOT_PASSWORD=admin
HUMMINGBOT_TIMEOUT=30.0
HUMMINGBOT_MAX_RETRIES=3
HUMMINGBOT_RETRY_DELAY=2.0
HUMMINGBOT_LOG_LEVEL=INFO
EOF
  printf 'Created %s with local development defaults.\n' "$MCP_ENV"
fi

