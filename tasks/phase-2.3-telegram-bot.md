---
phase: 2.3
title: Telegram Notifications & Approvals
status: completed
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
- Added `src/agents/reporter/notifier.py` as the thin Telegram sender used by the trader and reporter agents. It no-ops safely when Telegram credentials are missing, logs outgoing sends to `runtime/audit/telegram.jsonl`, and supports trade alerts, close alerts, stop-loss alerts, daily-loss halts, periodic reports, and approval requests.
- Added `src/agents/reporter/approvals.py` for persistent approval request state, inline [Approve]/[Reject] buttons, timeout handling, callback validation against the configured operator user ID, and approval audit events appended to `runtime/audit/policy.jsonl`.
- Reworked `src/agents/reporter/formatters.py` to cover the Phase 2.3 alert/report shapes only: trade alerts, close alerts, stop-loss alerts, periodic reports, daily summaries, and approval prompts.
- Added `src/agents/reporter/agent.py` as the reporter loop. It runs Telegram polling for approval callbacks only and schedules the periodic/daily reports.
- Updated `src/agents/trader/agent.py` to send alerts after opens/closes, emit daily-loss halt notifications, and request operator approval before executing warning-level trades. Strong rejected signals can be escalated for review, but any eventual execution still re-runs the policy gate before sending an order.
- Added the new Phase 2.3 config keys in `src/shared/config.py` and `.env.example`:
  - `TELEGRAM_BOT_TOKEN`
  - `TELEGRAM_OPERATOR_CHAT_ID`
  - `EDGE_AGENT_REPORT_INTERVAL_HOURS`
  - `EDGE_AGENT_DAILY_REPORT_HOUR_UTC`
  - `EDGE_AGENT_APPROVAL_TIMEOUT_SECONDS`
- Added `make reporter` and updated `README.md` to document the narrower notification/approval scope.

## Verification completed
- `python3 -m compileall src tests`
- `python3 -m pytest tests/unit/ -q`
- `python3 -m pytest tests/unit/test_notifier.py tests/unit/test_config.py tests/unit/test_trader_agent.py -q`
- Verified locally that Telegram credentials are not currently configured on this machine, so the one manual end-to-end verification step with a real bot token and chat ID remains pending.

## Out of scope
- Command handlers (moved to OpenClaw via Phase 2.3b)
- Conversational queries
- Group chat support
- Web dashboard
