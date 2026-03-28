# Tools

## IMPORTANT: How EDGE-AGENT works

EDGE-AGENT runs as **standalone Python processes**, NOT as Hummingbot bots. The Hummingbot API is only the execution layer (market data + order placement). Do NOT check Hummingbot's bot-orchestration endpoints to determine trading status.

### Check if agents are running

```bash
# Check running agent processes
ps aux | grep -E 'agents\.(analyst|trader|reporter)' | grep -v grep

# Check PID file from integration test
cat runtime/integration-test-pids.txt 2>/dev/null
```

If processes are listed, the agents ARE running even if Hummingbot shows "0 bots".

### Check agent output

```bash
# Latest analyst signals (most recent file)
ls -t runtime/analyst/*.jsonl | head -1 | xargs tail -5

# Latest trader events
ls -t runtime/trader/*.jsonl | head -1 | xargs tail -5

# Policy audit log
tail -5 runtime/audit/policy.jsonl 2>/dev/null
```

### Start/stop agents

```bash
# Start all agents (analyst + trader + reporter)
make integration-test

# Run single cycles
make analyst-once    # one analyst cycle
make trader-once     # one trader cycle

# Stop all agents
kill $(cat runtime/integration-test-pids.txt)
```

## Hummingbot API

Interface to Hummingbot API at `http://localhost:8000` for exchange operations. Credentials: read from `.env` and `infra/env/api.env`.

| Capability | Endpoint | Description |
|---|---|---|
| Get balances | `POST /portfolio/state` | Account equity, available margin, USDT balance |
| Get positions | `POST /trading/positions` | Open positions with entry price, size, unrealized P&L |
| Get price | `POST /market-data/prices` | Current price for a trading pair |
| Get candles | `POST /market-data/candles` | OHLCV candle data (uses OKX perpetual connector) |
| Get funding | `POST /market-data/funding-info` | Current funding rate |
| Get orderbook | `POST /market-data/order-book` | Bid/ask depth |
| Accounts | `GET /accounts/master_account/credentials` | Check stored connector credentials |

All endpoints require basic auth (`admin:<password from infra/env/api.env>`).

**Access:** All agents can read. Only Trader can write (through PolicyEngine).

## Policy engine

Risk evaluation gate at `src/policy/engine.py`.

| Capability | Description |
|---|---|
| Evaluate proposal | Check a trade proposal against all risk rules, return approve/reject |
| Read risk config | Load current values from `configs/risk/policy.yml` |

**Access:** Trader submits proposals. All agents can read config.

## Runtime logs

| Directory | Content |
|---|---|
| `runtime/analyst/*.jsonl` | Signal logs — one file per analyst cycle with events: `analysis_started`, `signal_generated`, `no_signal`, `signal_filtered` |
| `runtime/trader/*.jsonl` | Trade logs — events: `trade_opened`, `position_held`, `position_closed`, `trade_rejected` |
| `runtime/audit/policy.jsonl` | Policy audit trail — every evaluation logged |
| `runtime/audit/telegram.jsonl` | Telegram notification audit |

## Risk config

**Source:** `configs/risk/policy.yml`

Current hard limits (non-negotiable):
- Max 2% risk per trade
- Max 5% daily loss
- Max 30% total exposure
- Max 10% single position
- Max 3x leverage
- Stop loss required, max 3% from entry
- Allowed pairs: BTC-USDT, ETH-USDT

**Audit:** All writes logged to `runtime/audit/policy.jsonl`
