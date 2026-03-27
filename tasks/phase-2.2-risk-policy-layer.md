---
phase: 2.2
title: Risk Policy Layer
status: completed
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
- [x] All 9 rules implemented and unit tested
- [x] Policy rejects trades that violate any rule
- [x] Policy warns when approaching limits (e.g., 80% of daily loss)
- [x] Config changes take effect without restart
- [x] Every evaluation is audit logged
- [x] Kill switch works immediately
- [x] 100% unit test coverage on rules

## Implementation notes
- Added `src/policy/models.py` with typed `RiskPolicyConfig`, `TradeProposal`, `AccountState`, `PolicyDecision`, and audit record models.
- Added `src/policy/rules.py` with pure helpers for stop-loss distance, risk amount, exposure caps, and daily-loss calculations.
- Added `src/policy/engine.py` with YAML-backed config loading, automatic reload-on-change, append-only audit logging to `runtime/audit/policy.jsonl`, size adjustment, warnings, and approval/rejection logic.
- Added the committed default config at `configs/risk/policy.yml`.
- Exported the policy surfaces from `src/policy/__init__.py`.

## Verification completed
- `python3 -m pytest tests/unit/test_policy_engine.py -q`
- Verified rule helpers, kill switch, pair/leverage/stop-loss violations, size adjustment, warning thresholds, zero remaining exposure rejection, and config reload audit logging.

## Out of scope
- Approval workflow (Phase 2.3 — policy just says approved/rejected)
- Position management (that's the trader agent's job)
- Historical risk analytics
