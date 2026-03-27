# Agents

## Market Analyst

**Role:** Read-only signal generator.

- Reads market data (price, volume, orderbook, funding rates) via Hummingbot MCP
- Generates long and short trade signals using Moonshot.ai LLM inference
- Writes signals to `runtime/signals/analyst.jsonl`
- **Never** places orders or modifies positions
- **Never** writes to policy or risk config

**Trigger:** Runs on a configurable cycle (default: every 5 minutes via `make analyst-once`).

## Trader

**Role:** Signal executor and position manager.

- Reads signals from the analyst JSONL log
- Proposes trades to the PolicyEngine before every action
- If approved, executes orders via Hummingbot MCP
- Manages open positions: trailing stops, take-profit, dynamic exits
- Logs every decision to `runtime/audit/policy.jsonl`

**Hard constraint:** Every write action (open, close, modify) must pass through `src/policy/engine.py` first. No exceptions.

**Trigger:** Runs on a configurable cycle (default: every 30 seconds via `make trader-once`).

## Reporter

**Role:** Read-only notification agent.

- Reads trader state, positions, and P&L
- Formats summaries and pushes to Telegram
- Handles operator queries routed through OpenClaw
- **Never** places orders or modifies config

**Trigger:** Event-driven (trade fills, daily summaries) and on-demand via Telegram.

---

## Operating rules

1. **No agent can modify risk policy without operator confirmation.** Policy changes require explicit human approval.
2. **No agent can bypass the policy layer.** The PolicyEngine is the single gate between intent and execution.
3. **Trader must always go through policy evaluation.** Even if a signal looks valid, it must be proposed and approved.
4. **OpenClaw is the conversational interface, not the execution layer.** OpenClaw routes commands to agents; it does not execute trades directly.
5. **Agents communicate through typed Pydantic models**, not raw dicts. See `src/shared/models.py`.
