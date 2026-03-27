# Skill: Risk Override

## Description

Temporarily adjust risk parameters in `configs/risk/policy.yml`. Requires explicit operator confirmation before applying.

## When to use

- Operator asks to "Lower leverage to 2x", "Reduce max exposure", "Tighten stop losses"
- Part of go-live process (starting with conservative limits)

## Steps

1. Read current risk config from `configs/risk/policy.yml`
2. Present current value and proposed new value to operator
3. **Wait for explicit confirmation** -- do NOT apply without operator saying "yes" or "confirm"
4. If confirmed:
   a. Update `configs/risk/policy.yml` with new value
   b. Log the change to `runtime/audit/policy.jsonl`
   c. Confirm to operator with old and new values
5. If rejected, acknowledge and take no action

## Adjustable parameters

| Parameter | Min | Max | Notes |
|---|---|---|---|
| `max_risk_per_trade_pct` | 0.005 | 0.05 | 0.5% to 5% |
| `max_daily_loss_pct` | 0.01 | 0.10 | 1% to 10% |
| `max_total_exposure_pct` | 0.05 | 0.50 | 5% to 50% |
| `max_single_position_pct` | 0.02 | 0.20 | 2% to 20% |
| `max_leverage` | 1 | 5 | Integer only |
| `max_stop_loss_pct` | 0.01 | 0.05 | 1% to 5% |

## Safety

- **Confirmation is mandatory.** No parameter change without explicit operator approval.
- Values outside the min/max range above are rejected.
- Every change is logged to `runtime/audit/policy.jsonl` with timestamp, old value, new value, and reason.
- To revert, operator can request the original value or refer to the audit log.

## Audit log format

```json
{
  "timestamp": "2026-03-27T12:00:00Z",
  "action": "risk_override",
  "field": "max_leverage",
  "old_value": 3,
  "new_value": 2,
  "reason": "Operator requested lower leverage for go-live",
  "confirmed_by": "operator"
}
```
