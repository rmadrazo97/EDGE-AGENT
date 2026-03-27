---
phase: 2.4
title: Testnet Integration Test
status: pending
depends_on: phase-2.0, phase-2.1, phase-2.2, phase-2.3
---

# PRD: Testnet Integration Test

## Goal
Run the full system end-to-end on Binance testnet for 24-48 hours. Validate that all agents work together, risk rules hold, and Telegram reporting works.

## Requirements

### Integration run
- Start all agents: analyst, trader, reporter
- Connect to Binance Futures testnet
- Let the system run for 24-48 hours unattended
- Monitor via Telegram only (simulating real operation)

### Validation checklist
- [ ] Analyst produces signals at expected interval
- [ ] Trader executes trades within risk bounds
- [ ] Stop losses are placed on every position
- [ ] Daily loss limit is respected
- [ ] Telegram notifications arrive for all events
- [ ] Daily report is accurate (matches actual positions/P&L)
- [ ] `/status`, `/positions`, `/pause`, `/resume` all work
- [ ] System recovers from agent restart without losing position state
- [ ] No unhandled exceptions in logs over 24h

### Bug tracking
- Document all issues found during integration run
- Fix critical issues (positions not tracked, risk rules bypassed)
- Defer non-critical issues (formatting, timing)

### Performance baseline
- Record: signals per day, trades per day, win rate, average P&L per trade
- This is testnet data so not meaningful for strategy evaluation, but validates throughput

## Acceptance criteria
- [ ] System runs 24h without crashing
- [ ] All risk rules enforced correctly
- [ ] Telegram is responsive and accurate
- [ ] No position state lost on restart
- [ ] Issues documented and critical ones fixed

## Out of scope
- Strategy performance evaluation (testnet prices aren't real)
- Optimization
- Load testing
