#!/usr/bin/env sh
set -eu

ROOT_DIR="$(CDPATH='' cd -- "$(dirname -- "$0")/../.." && pwd)"
ANALYST_DIR="$ROOT_DIR/runtime/analyst"
TRADER_DIR="$ROOT_DIR/runtime/trader"
AUDIT_DIR="$ROOT_DIR/runtime/audit"

# ── helpers ──────────────────────────────────────────────────────────
log() { printf '%s\n' "$*"; }

count_events() {
  dir="$1"
  event="$2"
  if [ -d "$dir" ] && ls "$dir"/*.jsonl >/dev/null 2>&1; then
    grep -c "\"$event\"" "$dir"/*.jsonl 2>/dev/null | awk -F: '{s+=$NF} END {print s+0}'
  else
    printf '0\n'
  fi
}

# ── signal counts ────────────────────────────────────────────────────
signals_generated=$(count_events "$ANALYST_DIR" "signal_generated")
signals_filtered=$(count_events "$ANALYST_DIR" "signal_filtered")
analysis_cycles=$(count_events "$ANALYST_DIR" "analysis_started")

# ── trade counts ─────────────────────────────────────────────────────
trades_opened=$(count_events "$TRADER_DIR" "trade_opened")
trades_closed=$(count_events "$TRADER_DIR" "position_closed")
trades_rejected=$(count_events "$TRADER_DIR" "trade_rejected")
positions_held=$(count_events "$TRADER_DIR" "position_held")

# ── win rate and P&L ────────────────────────────────────────────────
win_count=0
total_pnl="0"

if [ -d "$TRADER_DIR" ] && ls "$TRADER_DIR"/*.jsonl >/dev/null 2>&1; then
  # Extract realized_pnl from position_closed events
  pnl_data=$(grep '"position_closed"' "$TRADER_DIR"/*.jsonl 2>/dev/null | \
    python3 -c "
import sys, json

wins = 0
total = 0
pnl_sum = 0.0
for line in sys.stdin:
    # Each line may have a filename prefix from grep; find the JSON part
    idx = line.find('{')
    if idx < 0:
        continue
    try:
        obj = json.loads(line[idx:])
    except json.JSONDecodeError:
        continue
    details = obj.get('details', {})
    rpnl = details.get('realized_pnl', 0.0)
    pnl_sum += rpnl
    total += 1
    if rpnl > 0:
        wins += 1

if total > 0:
    print(f'{wins} {total} {pnl_sum:.6f}')
else:
    print('0 0 0.000000')
" 2>/dev/null || printf '0 0 0.000000\n')

  win_count=$(printf '%s' "$pnl_data" | awk '{print $1}')
  closed_total=$(printf '%s' "$pnl_data" | awk '{print $2}')
  total_pnl=$(printf '%s' "$pnl_data" | awk '{print $3}')
fi

if [ "$trades_closed" -gt 0 ]; then
  win_rate=$(python3 -c "print(f'{$win_count / $trades_closed * 100:.1f}')" 2>/dev/null || printf '0.0')
else
  win_rate="N/A"
fi

# ── errors ───────────────────────────────────────────────────────────
error_count=0
if [ -d "$ANALYST_DIR" ] && ls "$ANALYST_DIR"/*.jsonl >/dev/null 2>&1; then
  analyst_errors=$(grep '"error"' "$ANALYST_DIR"/*.jsonl 2>/dev/null | grep -cv 'null' || true)
  error_count=$((error_count + analyst_errors))
fi
if [ -d "$TRADER_DIR" ] && ls "$TRADER_DIR"/*.jsonl >/dev/null 2>&1; then
  trader_errors=$(grep '"error"' "$TRADER_DIR"/*.jsonl 2>/dev/null | grep -cv 'null' || true)
  error_count=$((error_count + trader_errors))
fi
if [ -f "$AUDIT_DIR/policy.jsonl" ]; then
  policy_errors=$(grep -c '"error"' "$AUDIT_DIR/policy.jsonl" 2>/dev/null || true)
  if [ "$policy_errors" -gt 0 ]; then
    policy_real=$(grep '"error"' "$AUDIT_DIR/policy.jsonl" 2>/dev/null | grep -cv 'null' || true)
    error_count=$((error_count + policy_real))
  fi
fi

# ── output ───────────────────────────────────────────────────────────
log "============================================="
log "  EDGE-AGENT Integration Test Report"
log "============================================="
log ""
log "  Analyst"
log "  -------"
log "  Analysis cycles:    $analysis_cycles"
log "  Signals generated:  $signals_generated"
log "  Signals filtered:   $signals_filtered"
log ""
log "  Trader"
log "  ------"
log "  Trades opened:      $trades_opened"
log "  Trades closed:      $trades_closed"
log "  Trades rejected:    $trades_rejected"
log "  Positions held:     $positions_held"
log ""
log "  Performance"
log "  -----------"
log "  Win rate:           ${win_rate}%"
log "  Total realized P&L: $total_pnl"
log ""
log "  Health"
log "  ------"
log "  Errors in logs:     $error_count"
log ""
log "============================================="

if [ "$error_count" -gt 0 ]; then
  log ""
  log "  Errors found — review logs for details:"
  log "    runtime/analyst/*.jsonl"
  log "    runtime/trader/*.jsonl"
  log "    runtime/audit/policy.jsonl"
fi
