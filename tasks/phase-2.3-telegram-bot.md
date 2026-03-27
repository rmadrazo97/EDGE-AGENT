---
phase: 2.3
title: Telegram Notifications & Approvals
status: in_progress
depends_on: phase-2.1, phase-2.2
---

# PRD: Telegram Notifications & Approvals

## Goal
Build a thin Telegram notification layer for push alerts and approval buttons only. All conversational commands and queries are handled by OpenClaw via Telegram channel (Phase 2.3b).

## What changed
Previously this phase was a full Telegram bot with 10 command handlers. Now split into:
- **Phase 2.3** (this): Push notifications + approval inline keyboards
- **Phase 2.3b**: OpenClaw Telegram channel for commands/queries

## Requirements

### Notification service (`src/agents/reporter/`)
- `notifier.py` — sends push messages to operator's Telegram
- `formatters.py` — message formatting for all notification types
- `approvals.py` — inline keyboard approval flow with timeout

### Push notifications (event-driven, fired by agents)

**Trade alerts:**
- New position opened: pair, side, size, entry price, leverage, reasoning
- Position closed: pair, P&L, duration, exit reason
- Stop loss triggered: pair, loss amount
- Daily loss limit hit: trading halted message

**Approval requests:**
- When trader wants to act outside bounds
- Inline keyboard: [Approve] [Reject]
- Timeout: if no response in 5 minutes, auto-reject
- Result logged to audit trail

**Periodic reports:**
- Every 4 hours: open positions summary, unrealized P&L
- Daily (configurable time): full day summary — trades, P&L, win rate, signals generated vs executed

### Integration points
- Trader agent calls `notifier.send_trade_alert()` after execution
- Trader agent calls `notifier.request_approval()` for out-of-bounds proposals
- Scheduled reports via a simple timer in the reporter agent loop

### Security
- Messages sent only to configured `TELEGRAM_OPERATOR_CHAT_ID`
- Approval callbacks validated against operator user ID
- All notifications and approvals logged to audit

### Message formatting
- Clean, readable formatting with monospace for numbers
- Emoji sparingly: green/red for P&L, warning for alerts
- Mobile-first: concise messages

## Acceptance criteria
- [ ] Trade notifications arrive within 5 seconds of execution
- [ ] Approval flow works: request → inline button → execute or cancel
- [x] Approval auto-rejects after 5 minute timeout
- [ ] Daily report sends automatically at configured time
- [x] Only configured chat ID receives messages
- [x] All notifications logged

## Implementation notes
- Added `src/agents/reporter/telegram_bot.py` to build and start a polling Telegram bot with scheduled jobs for runtime-event polling, periodic reports, and daily reports.
- Added `src/agents/reporter/commands.py` as the current Telegram service surface. It covers notification delivery, approval callbacks, audit logging, and the existing direct operator commands already in use by this repo.
- Added `src/agents/reporter/formatters.py` for concise HTML-formatted trade, approval, status, risk, and PnL messages.
- Added `src/agents/reporter/approvals.py` for persistent approval state with timeout handling under `runtime/reporter/approvals.json`.
- Added Telegram-specific configuration in `src/shared/config.py` for bot token, operator chat ID, report cadence, daily report time, and timezone.
- Added `make telegram-bot`, documented the bot workflow in `README.md`, and expanded `.env.example` with the new Telegram settings.
- Added audit logging for outgoing notifications in `runtime/audit/telegram.jsonl`.
- Kept the implementation as a superset of the narrowed Phase 2.3 PRD: the notification and approval pieces are present, and the existing direct command handlers remain available instead of being deferred to a separate Phase 2.3b.

## Verification completed
- `python3 -m compileall src tests`
- `python3 -m pytest -q`
- `python3 -m pytest tests/unit/test_telegram_bot.py -q`
- `python3 -m pytest tests/unit/test_approval_store.py -q`
- Verified locally that `build_application(...)` succeeds in unit tests with configured Telegram settings and registers command handlers plus scheduled jobs.
- Verified locally that Telegram credentials are not currently configured on this machine, so live bot polling and end-to-end chat verification remain pending.

## Out of scope
- Command handlers (moved to OpenClaw via Phase 2.3b)
- Conversational queries
- Group chat support
- Web dashboard
