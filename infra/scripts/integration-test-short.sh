#!/usr/bin/env sh
set -u

# Short integration test: runs 2 analyst+trader cycles, validates the full
# pipeline end-to-end on Binance testnet. Takes ~5 minutes.
#
# Usage: ./integration-test-short.sh [--cycles N]

ROOT_DIR="$(CDPATH='' cd -- "$(dirname -- "$0")/../.." && pwd)"
CYCLES="${1:-2}"

log() { printf '[integration-test] %s\n' "$*"; }
die() { printf '[integration-test] ERROR: %s\n' "$*" >&2; exit 1; }
# grep -c returns exit 1 on zero matches; write to temp to avoid set -e issues
jcount() {
  _tmp=$(mktemp)
  cat $2 2>/dev/null | grep -c "$1" > "$_tmp" 2>/dev/null || true
  cat "$_tmp"
  rm -f "$_tmp"
}

# ── prerequisite checks ────────────────────────────────────────────
log "Checking prerequisites ..."
docker info >/dev/null 2>&1 || die "Docker is not running."

# ── smoke check (before loading .env to avoid credential conflicts) ─
log "Running smoke checks ..."
"$ROOT_DIR/infra/scripts/smoke.sh" || die "Smoke checks failed. Run 'make up' first."
log "Smoke checks passed."

# ── load env (after smoke so API creds don't conflict) ─────────────
if [ -f "$ROOT_DIR/.env" ]; then
  set -a; . "$ROOT_DIR/.env"; set +a
fi

[ -n "${BINANCE_TESTNET_API_KEY:-}" ]    || die "BINANCE_TESTNET_API_KEY is not set."
[ -n "${BINANCE_TESTNET_API_SECRET:-}" ] || die "BINANCE_TESTNET_API_SECRET is not set."
[ -n "${MOONSHOT_API_KEY:-}" ]           || die "MOONSHOT_API_KEY is not set."
log "Environment OK. (Telegram is optional for short test.)"

# ── prepare runtime ────────────────────────────────────────────────
mkdir -p "$ROOT_DIR/runtime/analyst" \
         "$ROOT_DIR/runtime/trader" \
         "$ROOT_DIR/runtime/audit"

# ── run cycles ─────────────────────────────────────────────────────
PASS=0
FAIL=0
TOTAL_SIGNALS=0
TOTAL_TRADES=0
TOTAL_REVIEWS=0

cycle=1
while [ "$cycle" -le "$CYCLES" ]; do
  log "━━━ Cycle $cycle/$CYCLES ━━━"

  # -- Analyst --
  log "Running analyst ..."
  if python3 -m agents.analyst.agent --once 2>&1; then
    log "  analyst: OK"
  else
    log "  analyst: FAILED"
    FAIL=$((FAIL + 1))
    cycle=$((cycle + 1))
    continue
  fi

  # Count signals from this cycle
  SIGNALS_NOW=$(jcount '"signal_generated"' "$ROOT_DIR"/runtime/analyst/*.jsonl)
  NEW_SIGNALS=$((SIGNALS_NOW - TOTAL_SIGNALS))
  TOTAL_SIGNALS=$SIGNALS_NOW
  log "  signals generated this cycle: $NEW_SIGNALS"

  # -- Trader --
  log "Running trader ..."
  if python3 -m agents.trader.agent --once 2>&1; then
    log "  trader: OK"
  else
    log "  trader: FAILED"
    FAIL=$((FAIL + 1))
    cycle=$((cycle + 1))
    continue
  fi

  # Count trades and reviews
  TRADES_NOW=$(jcount '"trade_opened"' "$ROOT_DIR"/runtime/trader/*.jsonl)
  REVIEWS_NOW=$(jcount '"position_held"\|"position_closed"' "$ROOT_DIR"/runtime/trader/*.jsonl)
  NEW_TRADES=$((TRADES_NOW - TOTAL_TRADES))
  NEW_REVIEWS=$((REVIEWS_NOW - TOTAL_REVIEWS))
  TOTAL_TRADES=$TRADES_NOW
  TOTAL_REVIEWS=$REVIEWS_NOW
  log "  trades opened this cycle: $NEW_TRADES"
  log "  positions reviewed this cycle: $NEW_REVIEWS"

  # -- Policy audit --
  if [ -f "$ROOT_DIR/runtime/audit/policy.jsonl" ]; then
    AUDIT_COUNT=$(wc -l < "$ROOT_DIR/runtime/audit/policy.jsonl" | tr -d ' ')
    log "  policy audit entries: $AUDIT_COUNT"
  fi

  # -- State persistence --
  if [ -f "$ROOT_DIR/runtime/trader/state.json" ]; then
    OPEN_POSITIONS=$(python3 -c "import json; d=json.load(open('$ROOT_DIR/runtime/trader/state.json')); print(len(d.get('open_positions',{})))" 2>/dev/null || echo "?")
    CLOSED_TRADES=$(python3 -c "import json; d=json.load(open('$ROOT_DIR/runtime/trader/state.json')); print(len(d.get('closed_trades',[])))" 2>/dev/null || echo "?")
    log "  state: $OPEN_POSITIONS open, $CLOSED_TRADES closed"
  fi

  PASS=$((PASS + 1))
  cycle=$((cycle + 1))

  # Brief pause between cycles
  if [ "$cycle" -le "$CYCLES" ]; then
    log "Waiting 10s before next cycle ..."
    sleep 10
  fi
done

# ── cleanup: close any open testnet positions ──────────────────────
log "Checking for open positions to clean up ..."
OPEN=$(python3 -c "
import json
try:
    d = json.load(open('$ROOT_DIR/runtime/trader/state.json'))
    pairs = list(d.get('open_positions', {}).keys())
    print(' '.join(pairs))
except Exception:
    print('')
" 2>/dev/null || echo "")

if [ -n "$OPEN" ]; then
  log "Closing testnet positions: $OPEN"
  for pair in $OPEN; do
    python3 -c "
from clients.trading import TradingClient
with TradingClient() as t:
    try:
        t.close_position('$pair')
        print(f'  closed $pair')
    except Exception as e:
        print(f'  failed to close $pair: {e}')
" 2>&1 || true
  done
fi

# ── summary ────────────────────────────────────────────────────────
log ""
log "━━━ Integration Test Summary ━━━"
log "  Cycles:     $CYCLES"
log "  Passed:     $PASS"
log "  Failed:     $FAIL"
log "  Signals:    $TOTAL_SIGNALS"
log "  Trades:     $TOTAL_TRADES"
log "  Reviews:    $TOTAL_REVIEWS"

if [ -f "$ROOT_DIR/runtime/audit/policy.jsonl" ]; then
  log "  Audit log:  $(wc -l < "$ROOT_DIR/runtime/audit/policy.jsonl" | tr -d ' ') entries"
fi

if [ "$FAIL" -gt 0 ]; then
  log ""
  log "RESULT: FAIL ($FAIL/$CYCLES cycles failed)"
  exit 1
fi

log ""
log "RESULT: PASS (all $CYCLES cycles completed)"
exit 0
