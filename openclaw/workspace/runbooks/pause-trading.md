# Runbook: Pause and Resume Trading

## Pause trading

### Option A: Via Telegram/OpenClaw

Tell OpenClaw: "Pause trading"

This sets `trading_enabled: false` in `configs/risk/policy.yml`. The Trader agent will skip all signal processing until resumed.

### Option B: Manual

Edit `configs/risk/policy.yml`:

```yaml
trading_enabled: false
```

The change takes effect on the next Trader cycle (within 30 seconds).

### What happens when paused

- Market Analyst continues generating signals (they accumulate in the log)
- Trader reads signals but skips execution (policy rejects all proposals)
- Reporter continues sending notifications
- Open positions remain open (stops and take-profits stay active on exchange)

### If you need to close positions too

Tell OpenClaw: "Kill everything" -- this closes all positions and pauses trading. Requires confirmation.

## Resume trading

### Option A: Via Telegram/OpenClaw

Tell OpenClaw: "Resume trading"

### Option B: Manual

Edit `configs/risk/policy.yml`:

```yaml
trading_enabled: true
```

### Post-resume checklist

- Verify balance and open positions: "What's my status?"
- Check if any signals accumulated during pause
- Monitor the first trade after resume
