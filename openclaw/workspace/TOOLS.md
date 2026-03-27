# Tools

## Hummingbot MCP

Interface to Hummingbot API for exchange operations.

| Capability | Description |
|---|---|
| Get balances | Account equity, available margin, USDT balance |
| Get positions | Open positions with entry price, size, unrealized P&L |
| Get market data | Current price, 24h volume, orderbook snapshot |
| Place order | Submit limit/market orders (Trader agent only, through PolicyEngine) |
| Cancel order | Cancel open orders (Trader agent only, through PolicyEngine) |

**Access:** All agents can read. Only Trader can write (through PolicyEngine).

## Policy engine

Risk evaluation gate at `src/policy/engine.py`.

| Capability | Description |
|---|---|
| Evaluate proposal | Check a trade proposal against all risk rules, return approve/reject |
| Read risk config | Load current values from `configs/risk/policy.yml` |

**Access:** Trader submits proposals. All agents can read config.

## Trader state

Runtime state of the Trader agent.

| Capability | Description |
|---|---|
| Open positions | Current positions with entry, size, stop, unrealized P&L |
| Closed trades | Today's completed trades with realized P&L |
| Daily P&L | Aggregate realized + unrealized for the day |

**Source:** `runtime/state/trader.json` and Hummingbot MCP positions endpoint.

## Analyst logs

Signal history from the Market Analyst.

| Capability | Description |
|---|---|
| Recent signals | Last N signals from `runtime/signals/analyst.jsonl` |
| Cycle history | Full signal log with timestamps, pairs, direction, confidence |

**Source:** `runtime/signals/analyst.jsonl`

## Risk config

Policy configuration with audit trail.

| Capability | Description |
|---|---|
| Read policy | Current risk parameters from `configs/risk/policy.yml` |
| Write policy | Update parameters (requires operator confirmation, logged to audit) |

**Source:** `configs/risk/policy.yml`
**Audit:** All writes logged to `runtime/audit/policy.jsonl`
