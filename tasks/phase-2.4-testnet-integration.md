---
phase: 2.4
title: Testnet Integration Test
status: ready
depends_on: phase-2.3, phase-2.3b
---

# PRD: Testnet Integration Test

## Goal
Run the full system end-to-end on Binance testnet for 24-48 hours. Validate that all agents work together, risk rules hold, notifications fire, and OpenClaw commands work via Telegram.

## Requirements

### Integration run
- Start all agents: analyst, trader, reporter/notifier
- OpenClaw workspace active with Telegram channel
- Connect to Binance Futures testnet
- Let the system run for 24-48 hours unattended
- Monitor via Telegram only (simulating real operation)

### Validation checklist
- [ ] Analyst produces signals at expected interval
- [ ] Trader executes trades within risk bounds
- [ ] Stop losses are placed on every position
- [ ] Daily loss limit is respected
- [ ] Push notifications arrive for all trade events
- [ ] Approval flow works for out-of-bounds proposals
- [ ] Daily report is accurate (matches actual positions/P&L)
- [ ] OpenClaw responds to natural language queries via Telegram
- [ ] Pause/resume via OpenClaw toggles policy correctly
- [ ] System recovers from agent restart without losing position state
- [ ] No unhandled exceptions in logs over 24h

### Bug tracking
- Document all issues found during integration run
- Fix critical issues (positions not tracked, risk rules bypassed, notifications missing)
- Defer non-critical issues (formatting, timing)

### Performance baseline
- Record: signals per day, trades per day, win rate, average P&L per trade
- This is testnet data so not meaningful for strategy evaluation, but validates throughput

## Acceptance criteria
- [ ] System runs 24h without crashing
- [ ] All risk rules enforced correctly
- [ ] Push notifications are timely and accurate
- [ ] OpenClaw conversational queries work via Telegram
- [ ] No position state lost on restart
- [ ] Issues documented and critical ones fixed

> **Note:** Status set to `ready`. Scripts and runbook are built; the actual 24-48h integration run has not yet been executed.

## Out of scope
- Strategy performance evaluation (testnet prices aren't real)
- Optimization
- Load testing

## Implementation notes

### Files created

- **`docs/runbooks/integration-test.md`** -- Step-by-step operational runbook covering prerequisites, pre-flight checks, starting/stopping the test, monitoring via Telegram, log inspection, success criteria checklist, and post-run analysis.

- **`infra/scripts/integration-test.sh`** -- POSIX sh runner script that verifies prerequisites (Docker, env vars, smoke checks), starts all three agents (analyst, trader, reporter) in the background, saves PIDs to `runtime/integration-test-pids.txt`, traps SIGINT/SIGTERM for clean shutdown, and monitors for unexpected agent exits.

- **`infra/scripts/integration-test-report.sh`** -- POSIX sh post-run analysis script that parses JSONL logs to count signals, trades opened/closed/rejected, calculates win rate and total realized P&L, counts errors, and outputs a formatted summary.

### Makefile targets added

- `make integration-test` -- runs `infra/scripts/integration-test.sh`
- `make integration-report` -- runs `infra/scripts/integration-test-report.sh`

### Agent entry points used

- `python3 -m agents.analyst.agent` (continuous mode, no `--once` flag)
- `python3 -m agents.trader.agent` (continuous mode, no `--once` flag)
- `python3 -m agents.reporter.agent`

### Log paths parsed

- `runtime/analyst/*.jsonl` -- events: `analysis_started`, `signal_generated`, `signal_filtered`
- `runtime/trader/*.jsonl` -- events: `trade_opened`, `position_closed`, `position_held`, `trade_rejected`, `approval_resolved`
- `runtime/audit/policy.jsonl` -- policy enforcement audit trail
