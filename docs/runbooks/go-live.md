# Go-Live Runbook: Real Binance Futures

This runbook covers every step to switch EDGE-AGENT from Binance testnet to real Binance Futures with conservative parameters.

---

## Prerequisites

- [ ] Real Binance Futures account created and verified (KYC complete)
- [ ] API key generated with **Futures trading** permission enabled
- [ ] API key does **not** have withdrawal permission (security best practice)
- [ ] Account funded with USDT (minimum recommended: enough to cover a few BTC-USDT trades at 2x leverage)
- [ ] Telegram bot connected and responding to `/status`
- [ ] All Phase 2.x acceptance criteria met on testnet

---

## Step 1: Credential Setup

Edit the `.env` file at the repo root. Replace the testnet credentials with real Binance credentials.

```bash
# .env (repo root)

# REMOVE or comment out testnet keys:
# BINANCE_TESTNET_API_KEY=...
# BINANCE_TESTNET_API_SECRET=...

# ADD real Binance Futures keys:
BINANCE_API_KEY=your_real_api_key
BINANCE_SECRET=your_real_api_secret

# Switch the connector from testnet to live:
EDGE_AGENT_MARKET_DATA_CONNECTOR=binance_perpetual
```

**Important:** The `ClientSettings.from_env()` in `src/shared/config.py` reads `BINANCE_API_KEY` / `BINANCE_SECRET` as fallbacks. Setting `EDGE_AGENT_MARKET_DATA_CONNECTOR=binance_perpetual` tells the system to use the real connector instead of `binance_perpetual_testnet`.

**Never commit `.env` to version control.**

---

## Step 2: Remove Testnet Safety Guards in TradingClient

The file `src/clients/trading.py` contains two testnet-only guards that must be updated for live trading:

1. **`max_test_position_size`** (line 76) -- Currently hardcoded to `Decimal("0.005")`. For live trading, either remove this cap entirely or increase it to a value appropriate for your account size.

2. **`_ensure_testnet_only()`** (line 78) -- This method raises an error if the connector is not `binance_perpetual_testnet`. For live trading, this guard must be removed or made conditional (e.g., check an environment variable like `EDGE_AGENT_LIVE_TRADING_ENABLED=true`).

**Do not remove these guards until you are ready to go live.** They exist to prevent accidental real-money trades.

---

## Step 3: Risk Parameter Switch

Copy the conservative live policy into the active policy file:

```bash
cp configs/risk/policy-live-conservative.yml configs/risk/policy.yml
```

Verify the contents:

```bash
cat configs/risk/policy.yml
```

Expected values:
- `max_risk_per_trade_pct: 0.01` (1%)
- `max_daily_loss_pct: 0.03` (3%)
- `max_total_exposure_pct: 0.15` (15%)
- `max_single_position_pct: 0.05` (5%)
- `max_leverage: 2`
- `allowed_pairs: [BTC-USDT]` (only BTC-USDT for first week)

---

## Step 4: Pre-Flight Verification

### 4a. Test API Connectivity

```bash
make up
make smoke
```

The smoke test (`infra/scripts/smoke.sh`) should confirm the Hummingbot API is reachable.

### 4b. Verify Account Balances

Use the portfolio endpoint to confirm your real account balance is visible:

```bash
python3 -c "
from clients.portfolio import PortfolioClient
from shared.config import ClientSettings
s = ClientSettings.from_env()
c = PortfolioClient(settings=s)
print(c.get_balances())
"
```

Confirm USDT balance matches what you deposited.

### 4c. Manual Limit Order Test

Place a small limit order well away from market price, verify it appears, then cancel:

```bash
python3 -c "
from clients.trading import TradingClient
from shared.config import ClientSettings
from decimal import Decimal
s = ClientSettings.from_env()
t = TradingClient(settings=s)

# Place a limit BUY far below market (will not fill)
# Adjust price to be well below current BTC price
orders = t.get_open_orders('BTC-USDT')
print('Open orders before:', len(orders))
# After placing, cancel the order and verify
"
```

Verify the order shows up on Binance web UI, then cancel it.

---

## Step 5: Go Live

Start the agents with conservative config:

```bash
# Terminal 1: Market analyst (30-minute interval for live)
EDGE_AGENT_ANALYST_INTERVAL_MINUTES=30 make analyst-once

# Terminal 2: Trader agent
make trader-once

# Terminal 3: Telegram reporter
make reporter
```

For continuous operation:

```bash
EDGE_AGENT_ANALYST_INTERVAL_MINUTES=30 python3 -m agents.analyst.agent &
python3 -m agents.trader.agent &
python3 -m agents.reporter.agent &
```

---

## Step 6: First Week Monitoring Protocol

- [ ] Monitor **every trade** via Telegram notifications
- [ ] Review daily P&L reports manually -- compare against Binance account
- [ ] Keep `/pause` command ready in Telegram at all times
- [ ] Check `runtime/audit/policy.jsonl` daily for any violations or warnings
- [ ] Verify stop losses fire correctly on at least one trade
- [ ] Compare P&L tracking in EDGE-AGENT vs actual Binance account balance

### Daily checklist:
1. Check Telegram for overnight trade notifications
2. Run `cat runtime/audit/policy.jsonl | tail -20` to review recent policy decisions
3. Compare reported P&L with Binance Futures account page
4. Verify no unexpected positions are open

---

## Step 7: Decision Points

### After 1 week of clean operation:

**Add ETH-USDT:**
```bash
# Edit configs/risk/policy.yml:
# allowed_pairs:
#   - BTC-USDT
#   - ETH-USDT
```

The `PolicyEngine` in `src/policy/engine.py` hot-reloads the config file on every evaluation cycle, so no restart is needed.

**Relax parameters (only if 1 week is profitable with no issues):**
- `max_risk_per_trade_pct`: 0.01 -> 0.02
- `max_total_exposure_pct`: 0.15 -> 0.20
- `max_daily_loss_pct`: 0.03 -> 0.05

**Do NOT relax all parameters at once.** Change one at a time and observe for 2-3 days.

### When to pause and rethink:
- Daily loss hits 3% on any single day
- More than 3 consecutive losing trades
- Any unexpected behavior vs testnet results
- Stop loss fails to fire

---

## Step 8: Rollback

If anything goes wrong, see [docs/runbooks/rollback.md](rollback.md) for the full rollback procedure.

Quick emergency stop: see [docs/runbooks/disable-trading.md](disable-trading.md).
