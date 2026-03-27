#!/usr/bin/env sh
set -eu

ROOT_DIR="$(CDPATH='' cd -- "$(dirname -- "$0")/../.." && pwd)"
API_ENV="$ROOT_DIR/infra/env/api.env"
MCP_ENV="$ROOT_DIR/infra/env/mcp.env"

generate_secret() {
  python3 - <<'PY'
import secrets

print(secrets.token_urlsafe(24))
PY
}

extract_postgres_password() {
  database_url="$1"

  python3 - "$database_url" <<'PY'
import sys
from urllib.parse import urlsplit

parsed = urlsplit(sys.argv[1])
print(parsed.password or "")
PY
}

read_env_value() {
  key="$1"
  path="$2"

  while IFS='=' read -r current_key current_value; do
    case "$current_key" in
      ''|\#*)
        continue
        ;;
    esac

    if [ "$current_key" = "$key" ]; then
      printf '%s' "$current_value"
      return 0
    fi
  done <"$path"

  return 1
}

if [ ! -f "$API_ENV" ]; then
  API_PASSWORD="$(generate_secret)"
  CONFIG_PASSWORD="$(generate_secret)"
  POSTGRES_PASSWORD="$(generate_secret)"

  cat >"$API_ENV" <<EOF
USERNAME=admin
PASSWORD=$API_PASSWORD
CONFIG_PASSWORD=$CONFIG_PASSWORD
POSTGRES_PASSWORD=$POSTGRES_PASSWORD
DATABASE_URL=postgresql+asyncpg://hbot:$POSTGRES_PASSWORD@postgres:5432/hummingbot_api
BROKER_HOST=emqx
BROKER_PORT=1883
BROKER_USERNAME=admin
BROKER_PASSWORD=public
EOF
  printf 'Created %s with local development defaults.\n' "$API_ENV"
fi

if ! read_env_value POSTGRES_PASSWORD "$API_ENV" >/dev/null 2>&1; then
  DATABASE_URL="$(read_env_value DATABASE_URL "$API_ENV" || printf '')"
  POSTGRES_PASSWORD="$(extract_postgres_password "$DATABASE_URL")"
  if [ -z "$POSTGRES_PASSWORD" ]; then
    POSTGRES_PASSWORD="$(generate_secret)"
  fi

  printf '\nPOSTGRES_PASSWORD=%s\n' "$POSTGRES_PASSWORD" >>"$API_ENV"
  printf 'Updated %s with POSTGRES_PASSWORD for local compose usage.\n' "$API_ENV"
fi

if [ ! -f "$MCP_ENV" ]; then
  HUMMINGBOT_USERNAME="$(read_env_value USERNAME "$API_ENV" || printf 'admin')"
  HUMMINGBOT_PASSWORD="$(read_env_value PASSWORD "$API_ENV" || printf 'admin')"

  cat >"$MCP_ENV" <<EOF
HUMMINGBOT_API_URL=http://hummingbot-api:8000
HUMMINGBOT_USERNAME=$HUMMINGBOT_USERNAME
HUMMINGBOT_PASSWORD=$HUMMINGBOT_PASSWORD
HUMMINGBOT_TIMEOUT=30.0
HUMMINGBOT_MAX_RETRIES=3
HUMMINGBOT_RETRY_DELAY=2.0
HUMMINGBOT_LOG_LEVEL=INFO
EOF
  printf 'Created %s with local development defaults.\n' "$MCP_ENV"
fi
