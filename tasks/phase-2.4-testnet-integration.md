---
phase: 2.4
title: Testnet Integration Test
status: pending
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

## Out of scope
- Strategy performance evaluation (testnet prices aren't real)
- Optimization
- Load testing
