#!/usr/bin/env sh
set -eu

ROOT_DIR="$(CDPATH='' cd -- "$(dirname -- "$0")/../.." && pwd)"
PID_FILE="$ROOT_DIR/runtime/integration-test-pids.txt"

# ── helpers ──────────────────────────────────────────────────────────
log() { printf '[integration-test] %s\n' "$*"; }

die() {
  printf '[integration-test] ERROR: %s\n' "$*" >&2
  exit 1
}

cleanup() {
  log "Shutting down agents ..."
  if [ -f "$PID_FILE" ]; then
    while IFS= read -r pid; do
      if kill -0 "$pid" 2>/dev/null; then
        kill "$pid" 2>/dev/null || true
        log "  sent SIGTERM to PID $pid"
      fi
    done < "$PID_FILE"
    rm -f "$PID_FILE"
  fi
  log "All agents stopped."
}

# ── prerequisite checks ─────────────────────────────────────────────
log "Checking prerequisites ..."

# Docker must be running
docker info >/dev/null 2>&1 || die "Docker is not running."

# Required env vars (loaded from .env if present)
if [ -f "$ROOT_DIR/.env" ]; then
  # shellcheck disable=SC1091
  set -a; . "$ROOT_DIR/.env"; set +a
fi

[ -n "${BINANCE_TESTNET_API_KEY:-}" ]      || die "BINANCE_TESTNET_API_KEY is not set."
[ -n "${BINANCE_TESTNET_API_SECRET:-}" ]   || die "BINANCE_TESTNET_API_SECRET is not set."
[ -n "${MOONSHOT_API_KEY:-}" ]             || die "MOONSHOT_API_KEY is not set."
[ -n "${TELEGRAM_BOT_TOKEN:-}" ]           || die "TELEGRAM_BOT_TOKEN is not set."
[ -n "${TELEGRAM_OPERATOR_CHAT_ID:-}" ]    || die "TELEGRAM_OPERATOR_CHAT_ID is not set."

log "Environment variables OK."

# Infrastructure smoke check
log "Running smoke checks ..."
"$ROOT_DIR/infra/scripts/smoke.sh" || die "Smoke checks failed. Run 'make up' first."
log "Smoke checks passed."

# ── prepare runtime directories ─────────────────────────────────────
mkdir -p "$ROOT_DIR/runtime/analyst" \
         "$ROOT_DIR/runtime/trader" \
         "$ROOT_DIR/runtime/reporter" \
         "$ROOT_DIR/runtime/audit"

# ── start agents ─────────────────────────────────────────────────────
: > "$PID_FILE"
trap cleanup INT TERM

log "Starting analyst agent (continuous mode) ..."
python3 -m agents.analyst.agent &
ANALYST_PID=$!
printf '%s\n' "$ANALYST_PID" >> "$PID_FILE"
log "  analyst PID: $ANALYST_PID"

log "Starting trader agent (continuous mode) ..."
python3 -m agents.trader.agent &
TRADER_PID=$!
printf '%s\n' "$TRADER_PID" >> "$PID_FILE"
log "  trader  PID: $TRADER_PID"

log "Starting reporter bot ..."
python3 -m agents.reporter.agent &
REPORTER_PID=$!
printf '%s\n' "$REPORTER_PID" >> "$PID_FILE"
log "  reporter PID: $REPORTER_PID"

log "All agents running. PIDs saved to $PID_FILE"
log "Press Ctrl+C to stop."

# ── wait for any child to exit ───────────────────────────────────────
# If any agent exits unexpectedly, report and shut down the rest.
while true; do
  for pid in $ANALYST_PID $TRADER_PID $REPORTER_PID; do
    if ! kill -0 "$pid" 2>/dev/null; then
      log "Agent with PID $pid exited unexpectedly."
      cleanup
      exit 1
    fi
  done
  sleep 10
done
