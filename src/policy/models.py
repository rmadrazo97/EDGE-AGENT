"""Typed models for risk policy configuration and decisions."""

from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, Field


class RiskPolicyConfig(BaseModel):
    trading_enabled: bool = True
    max_risk_per_trade_pct: float = 0.02
    max_daily_loss_pct: float = 0.05
    max_total_exposure_pct: float = 0.30
    max_single_position_pct: float = 0.10
    max_leverage: float = 3.0
    require_stop_loss: bool = True
    max_stop_loss_pct: float = 0.03
    allowed_sides: list[str] = Field(default_factory=lambda: ["long", "short"])
    allowed_pairs: list[str] = Field(default_factory=lambda: ["BTC-USDT", "ETH-USDT"])


class TradeProposal(BaseModel):
    pair: str
    side: str
    size: float
    leverage: float
    entry_price: float
    stop_loss_price: float | None = None
    signal_confidence: float
    reasoning: str


class AccountState(BaseModel):
    total_equity: float
    available_margin: float
    daily_realized_pnl: float = 0.0
    current_total_exposure: float = 0.0
    open_pairs: list[str] = Field(default_factory=list)


class PolicyDecision(BaseModel):
    approved: bool
    violations: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    adjusted_size: float | None = None


class PolicyAuditRecord(BaseModel):
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    event: str
    proposal: TradeProposal | None = None
    account_state: AccountState | None = None
    decision: PolicyDecision | None = None
    config: RiskPolicyConfig | None = None
    message: str | None = None
