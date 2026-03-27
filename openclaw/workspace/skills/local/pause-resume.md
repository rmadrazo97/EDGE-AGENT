# Skill: Pause / Resume Trading

## Description

Toggle the `trading_enabled` flag in `configs/risk/policy.yml` to pause or resume automated trading.

## When to use

- Operator says "Pause trading", "Stop trading", "Hold off on trades"
- Operator says "Resume trading", "Start trading again", "Unpause"

## Steps

### Pause

1. Read current value of `trading_enabled` from `configs/risk/policy.yml`
2. If already `false`, inform operator: "Trading is already paused."
3. Set `trading_enabled: false` in `configs/risk/policy.yml`
4. Log the change to `runtime/audit/policy.jsonl` with timestamp and reason
5. Confirm to operator: "Trading paused. Open positions and stops remain active."

### Resume

1. Read current value of `trading_enabled` from `configs/risk/policy.yml`
2. If already `true`, inform operator: "Trading is already active."
3. Set `trading_enabled: true` in `configs/risk/policy.yml`
4. Log the change to `runtime/audit/policy.jsonl` with timestamp and reason
5. Confirm to operator: "Trading resumed."

## Audit log format

```json
{
  "timestamp": "2026-03-27T12:00:00Z",
  "action": "policy_change",
  "field": "trading_enabled",
  "old_value": true,
  "new_value": false,
  "reason": "Operator requested pause via Telegram",
  "confirmed_by": "operator"
}
```

## Notes

- Pausing does NOT close open positions. Stops remain active on the exchange.
- The analyst continues generating signals while paused. They accumulate in the log.
- To close all positions and pause, use the "Kill everything" command (requires confirmation).
