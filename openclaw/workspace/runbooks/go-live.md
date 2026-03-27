# Runbook: Go Live

Checklist for switching from Binance testnet to real trading.

## Pre-flight checklist

- [ ] All tests pass on testnet (`make test`)
- [ ] Smoke tests pass (`make smoke`)
- [ ] At least 48 hours of testnet trading without errors
- [ ] Risk policy reviewed and confirmed (`configs/risk/policy.yml`)
- [ ] Stop losses verified on testnet (positions actually closed at stop)
- [ ] Daily loss circuit breaker tested (trading halts at 5% drawdown)
- [ ] Telegram notifications working (fills, errors, daily summary)
- [ ] Kill command tested (closes all positions and pauses)
- [ ] Operator has Binance mainnet API key with Futures permissions (no withdrawal)

## Switch steps

### 1. Update connector

Change Hummingbot connector from `binance_perpetual_testnet` to `binance_perpetual` in the environment config.

### 2. Update API credentials

Replace testnet API keys with mainnet keys in `infra/env/hummingbot.env`.

### 3. Start conservative

- Set `max_leverage: 1` initially
- Set `max_total_exposure_pct: 0.10` (10%)
- Monitor for 24 hours before relaxing to normal limits

### 4. Restart infrastructure

```bash
make down
make up
make smoke
```

### 5. Verify

- Ask OpenClaw: "What's my balance?" -- should show mainnet balance
- Confirm positions endpoint returns real data
- Place a minimum-size manual test trade and verify fill notification

### 6. Enable automated trading

```bash
make analyst-once
make trader-once
```

Monitor the first few trades closely.

## Rollback

If anything goes wrong:

1. "Pause trading" via Telegram
2. Close any open positions manually on Binance
3. Switch back to testnet connector
4. Investigate via `runbooks/incident-response.md`
