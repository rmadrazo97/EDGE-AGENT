---
phase: 3.2
title: Signal Quality Iteration
status: pending
depends_on: phase-3.0
---

# PRD: Signal Quality Iteration

## Goal
After the first week of live trading, review signal quality and improve the analyst agent. This is the most important ongoing work — the edge lives or dies here.

## Requirements

### Signal review process
1. Export all signals from first week (generated + executed + skipped)
2. For each executed signal, calculate actual P&L outcome
3. Categorize: winning signals, losing signals, missed opportunities
4. Identify patterns in wins vs losses

### Metrics to track
- Signal generation rate (per day)
- Execution rate (signals that passed policy / total signals)
- Win rate (profitable trades / total trades)
- Average win size vs average loss size (reward-to-risk ratio)
- Sharpe-like metric: average daily return / std dev of daily returns
- Max drawdown
- Time in position (average, distribution)

### Signal improvement levers
- **Prompt tuning**: adjust analyst system prompt based on what worked
- **Data inputs**: add or weight data differently (e.g., funding rate more important than volume?)
- **Confidence threshold**: raise or lower the 0.7 cutoff
- **Timing**: adjust analysis interval
- **Pair selection**: if ETH signals are better than BTC, allocate more

### Signal journal (`openclaw/workspace/memory/signals.md`)
- Maintained as Markdown for OpenClaw memory indexing
- Updated weekly with learnings
- Format: what changed, why, result

### Reporting enhancement
- Add weekly summary to Telegram (vs just daily)
- Include win rate, best/worst trade, net P&L

## Acceptance criteria
- [ ] Signal export tool produces clean data
- [ ] Metrics calculated for first week
- [ ] At least one round of prompt/parameter adjustment
- [ ] Signal journal started in OpenClaw memory
- [ ] Weekly Telegram report added

## Implementation notes (Phase 3.2 tooling)

Tooling implemented on 2026-03-27:

### Files created
- `tools/__init__.py` — empty package init
- `tools/signal_export.py` — reads `runtime/analyst/*.jsonl` and `runtime/trader/*.jsonl`, matches signals to trade outcomes by pair + timestamp proximity (5 min window), outputs CSV
- `tools/signal_metrics.py` — reads exported CSV, computes metrics (signal count, execution rate, win rate, avg win/loss, R:R, max drawdown, avg duration), breaks down by pair, side, and confidence bucket
- `tools/signal_journal_update.py` — runs full pipeline and appends dated entry to `openclaw/workspace/memory/signals.md`

### Makefile targets
- `make signal-export` — export signals to `signals.csv`
- `make signal-metrics` — export then print metrics table
- `make signal-journal` — full pipeline including journal update

### Design decisions
- Stdlib + json/csv only (no pandas/numpy). All tools work with zero data.
- Signal-to-trade matching uses pair + side + 5-minute timestamp window.
- Confidence buckets: 0.70-0.80, 0.80-0.90, 0.90-1.00.
- Journal appends (never overwrites) and removes placeholder text on first run.
- All tools are importable as modules and runnable as CLI scripts.

## This is ongoing
This phase doesn't "complete" — it's the continuous improvement loop. Mark done after the first iteration cycle, then it repeats.
