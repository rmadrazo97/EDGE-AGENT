# Rollback: Live to Testnet

This runbook reverts EDGE-AGENT from real Binance Futures back to testnet operation.

---

## Step 1: Stop All Agents

Kill all running agent processes:

```bash
# If running in foreground, Ctrl+C each terminal

# If running in background, find and kill:
pkill -f "agents.analyst.agent"
pkill -f "agents.trader.agent"
pkill -f "agents.reporter.agent"
```

Verify no agents are running:

```bash
ps aux | grep "agents\." | grep -v grep
```

---

## Step 2: Close All Live Positions

Before switching credentials, close every open position on the real exchange.

```bash
python3 -c "
from clients.trading import TradingClient
from shared.config import ClientSettings

s = ClientSettings.from_env()
t = TradingClient(settings=s)

positions = t.get_positions()
for pos in positions:
    if abs(pos.amount) > 0:
        print(f'Closing {pos.trading_pair}...')
        result = t.close_position(pos.trading_pair)
        print(f'  -> {result.status}')

print('Done. Verify on Binance web UI that no positions remain.')
"
```

**Also verify manually on [Binance Futures](https://www.binance.com/en/futures)** that no positions or open orders remain.

---

## Step 3: Switch Credentials Back to Testnet

Edit the `.env` file at the repo root:

```bash
# .env

# Comment out or remove real keys:
# BINANCE_API_KEY=...
# BINANCE_SECRET=...

# Restore testnet keys:
BINANCE_TESTNET_API_KEY=your_testnet_api_key
BINANCE_TESTNET_API_SECRET=your_testnet_api_secret

# Switch connector back to testnet:
EDGE_AGENT_MARKET_DATA_CONNECTOR=binance_perpetual_testnet
```

---

## Step 4: Restore Testnet Policy

If you modified `configs/risk/policy.yml` for live trading, restore it to the standard defaults:

```bash
cat > configs/risk/policy.yml << 'EOF'
trading_enabled: true
max_risk_per_trade_pct: 0.02
max_daily_loss_pct: 0.05
max_total_exposure_pct: 0.30
max_single_position_pct: 0.10
max_leverage: 3
require_stop_loss: true
max_stop_loss_pct: 0.03
allowed_sides:
  - long
  - short
allowed_pairs:
  - BTC-USDT
  - ETH-USDT
EOF
```

---

## Step 5: Restore Testnet Guards in TradingClient

If you modified `src/clients/trading.py` for live trading (removed `_ensure_testnet_only()` or changed `max_test_position_size`), revert those changes:

```bash
git checkout src/clients/trading.py
```

---

## Step 6: Restart Agents

```bash
make up
make smoke
```

Verify infrastructure is healthy, then start the agents:

```bash
make analyst-once   # Single cycle to verify connectivity
make trader-once    # Single cycle to verify trading works
make reporter       # Start Telegram reporter
```

---

## Step 7: Verify Testnet Connectivity

```bash
python3 -c "
from clients.portfolio import PortfolioClient
from shared.config import ClientSettings

s = ClientSettings.from_env()
print(f'Connector: {s.market_data_connector}')
assert 'testnet' in s.market_data_connector, 'NOT on testnet!'

c = PortfolioClient(settings=s)
balances = c.get_balances()
print(f'Balances: {balances}')
print('Testnet connectivity confirmed.')
"
```

Check the audit log to confirm the policy engine reloaded:

```bash
tail -5 runtime/audit/policy.jsonl
```
