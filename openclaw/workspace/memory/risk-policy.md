# Risk Policy

## Current parameters

Source: `configs/risk/policy.yml`

| Parameter | Value | Rationale |
|---|---|---|
| `trading_enabled` | `true` | Master switch. Set to `false` to halt all trading. |
| `max_risk_per_trade_pct` | 2% | Limits loss on any single trade to 2% of equity |
| `max_daily_loss_pct` | 5% | Circuit breaker: stops trading for the day at 5% drawdown |
| `max_total_exposure_pct` | 30% | Total notional across all positions capped at 30% of equity |
| `max_single_position_pct` | 10% | No single position exceeds 10% of equity |
| `max_leverage` | 3x | Hard cap on leverage. Conservative for crypto perpetuals. |
| `require_stop_loss` | `true` | Every position must have a stop loss at entry |
| `max_stop_loss_pct` | 3% | Stop loss no wider than 3% from entry price |
| `allowed_sides` | long, short | Both directions enabled |
| `allowed_pairs` | BTC-USDT, ETH-USDT | Only these pairs until manually expanded |

## Hard rule

These limits are **human-set**. No agent, LLM, or automated process may change them without explicit operator confirmation. The AI optimizes strategy within these bounds; it does not set the bounds.

## How changes are made

1. Operator requests a change via Telegram or OpenClaw
2. System shows current value, proposed value, and impact
3. Operator confirms
4. Change is written to `configs/risk/policy.yml`
5. Change is logged to `runtime/audit/policy.jsonl` with timestamp and reason
