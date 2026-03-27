---
phase: 2.2
title: Risk Policy Layer
status: pending
depends_on: phase-1.4
---

# PRD: Risk Policy Layer

## Goal
Build the non-negotiable policy gate that sits between AI decisions and trade execution. No trade happens without passing policy.

## Requirements

### Policy service (`src/policy/`)
- `engine.py` — evaluates a proposed trade against all rules
- `rules.py` — individual rule implementations
- `models.py` — TradeProposal and PolicyDecision models

### Risk rules (all hard-coded limits, human-configured values)

| Rule | Parameter | Default |
|---|---|---|
| Max risk per trade | `max_risk_per_trade_pct` | 2% |
| Max daily loss | `max_daily_loss_pct` | 5% |
| Max total exposure | `max_total_exposure_pct` | 30% |
| Max single position | `max_single_position_pct` | 10% |
| Max leverage | `max_leverage` | 3 |
| Stop loss required | `require_stop_loss` | true |
| Max stop loss distance | `max_stop_loss_pct` | 3% |
| Allowed pairs | `allowed_pairs` | ["BTC-USDT", "ETH-USDT"] |
| Trading hours | `trading_enabled` | true (can be toggled) |

### Configuration
- Rules loaded from `configs/risk/policy.yml`
- Can be updated without restarting (file watch or reload endpoint)
- Changing risk config is logged as an audit event

### Policy evaluation
```python
class TradeProposal:
    pair: str
    side: str  # "short"
    size: float
    leverage: float
    entry_price: float
    stop_loss_price: float
    signal_confidence: float
    reasoning: str

class PolicyDecision:
    approved: bool
    violations: list[str]  # which rules failed
    warnings: list[str]    # close to limits
    adjusted_size: float | None  # if size was capped
```

### Audit logging
- Every policy evaluation logged (approved and rejected)
- Log includes: timestamp, proposal, decision, current account state
- Append-only log file: `runtime/audit/policy.jsonl`

### Kill switch
- `trading_enabled: false` in config immediately blocks all new trades
- Existing positions are NOT auto-closed (that's a separate decision)

## Acceptance criteria
- [ ] All 9 rules implemented and unit tested
- [ ] Policy rejects trades that violate any rule
- [ ] Policy warns when approaching limits (e.g., 80% of daily loss)
- [ ] Config changes take effect without restart
- [ ] Every evaluation is audit logged
- [ ] Kill switch works immediately
- [ ] 100% unit test coverage on rules

## Out of scope
- Approval workflow (Phase 2.3 — policy just says approved/rejected)
- Position management (that's the trader agent's job)
- Historical risk analytics
