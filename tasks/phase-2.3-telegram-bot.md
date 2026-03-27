---
phase: 2.3
title: Telegram Bot
status: pending
depends_on: phase-2.1, phase-2.2
---

# PRD: Telegram Bot

## Goal
Build the Telegram bot that serves as the primary operator interface: reports, alerts, trade approvals, and quick commands.

## Requirements

### Bot setup (`src/agents/reporter/`)
- `telegram_bot.py` — bot initialization and handlers
- `formatters.py` — message formatting for reports and alerts
- `commands.py` — command handlers

### Notifications (push to operator)

**Trade alerts:**
- New position opened: pair, side, size, entry price, leverage, reasoning
- Position closed: pair, P&L, duration, exit reason
- Stop loss triggered: pair, loss amount
- Daily loss limit hit: trading halted message

**Approval requests:**
- When trader wants to act outside bounds
- Inline keyboard: [Approve] [Reject] [Modify]
- Timeout: if no response in 5 minutes, auto-reject

**Periodic reports:**
- Every 4 hours: open positions summary, unrealized P&L
- Daily (configurable time): full day summary — trades, P&L, win rate, signals generated vs executed

### Commands (operator to system)

| Command | Action |
|---|---|
| `/status` | Current positions, balance, daily P&L |
| `/positions` | Detailed view of all open positions |
| `/balance` | Account equity and available margin |
| `/signals` | Recent signals (last 6h) |
| `/pause` | Halt new trades (keep positions open) |
| `/resume` | Resume trading |
| `/kill` | Close all positions and halt trading |
| `/risk` | Show current risk limits and usage |
| `/pnl` | Today's realized + unrealized P&L |

### Security
- Bot responds only to configured Telegram user ID (your account)
- All commands logged to audit log
- `/kill` requires confirmation ("Type CONFIRM to close all positions")

### Message formatting
- Clean, readable formatting with monospace for numbers
- Use emoji sparingly: green/red for P&L, warning for alerts
- Keep messages concise — this is mobile-first

## Acceptance criteria
- [ ] Bot starts and responds to `/status`
- [ ] Trade notifications arrive within 5 seconds of execution
- [ ] Approval flow works: request → approve/reject → execution or cancellation
- [ ] Daily report sends automatically at configured time
- [ ] Only authorized user ID can interact
- [ ] `/pause` and `/resume` toggle trading
- [ ] `/kill` with confirmation closes all positions

## Out of scope
- Group chat support
- Multiple authorized users
- Voice/media messages
- Web dashboard
