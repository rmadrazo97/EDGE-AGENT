# Emergency Stop: Disable Trading

Use any of the methods below to halt trading immediately. Methods are listed from fastest to most thorough.

---

## Method 1: Telegram `/kill` Command

If the Telegram reporter agent is running and connected:

```
/kill
```

This sets `trading_enabled: false` in `configs/risk/policy.yml` via the `PolicyEngine.update_config()` method. The policy engine hot-reloads on every evaluation cycle, so new trades will be blocked immediately.

**Limitation:** This only prevents *new* trades. It does not close existing positions.

---

## Method 2: Edit Policy File Directly

Edit `configs/risk/policy.yml` and set:

```yaml
trading_enabled: false
```

Save the file. The `PolicyEngine` in `src/policy/engine.py` checks the file modification time on every call to `evaluate()` and reloads automatically. No agent restart is needed.

To verify the change was picked up, check the audit log:

```bash
tail -5 runtime/audit/policy.jsonl
```

You should see a `config_reloaded` event.

---

## Method 3: Close Positions via Hummingbot API

Use the `TradingClient` to close all open positions programmatically:

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

print('All positions closed.')
"
```

---

## Method 4: Close Positions Directly on Binance

1. Log in to [Binance Futures](https://www.binance.com/en/futures)
2. Go to **Positions** tab
3. Click **Close All Positions** or close each position individually
4. Cancel all open orders

This is the nuclear option -- use it if the API or agents are unresponsive.

---

## Verify Trading Is Halted

After using any method above, confirm:

1. **Policy is disabled:**
   ```bash
   cat configs/risk/policy.yml | head -1
   # Should show: trading_enabled: false
   ```

2. **No open positions remain:**
   ```bash
   python3 -c "
   from clients.trading import TradingClient
   from shared.config import ClientSettings
   s = ClientSettings.from_env()
   t = TradingClient(settings=s)
   positions = t.get_positions()
   print(f'Open positions: {len([p for p in positions if abs(p.amount) > 0])}')
   "
   ```

3. **Audit log confirms kill:**
   ```bash
   tail -5 runtime/audit/policy.jsonl
   ```

---

## How to Resume Trading

1. Confirm the issue that triggered the emergency stop is resolved
2. Re-enable trading in `configs/risk/policy.yml`:
   ```yaml
   trading_enabled: true
   ```
3. Verify the policy engine picks up the change:
   ```bash
   tail -3 runtime/audit/policy.jsonl
   ```
4. Optionally restart the agents:
   ```bash
   make up
   make analyst-once
   make trader-once
   make reporter
   ```
