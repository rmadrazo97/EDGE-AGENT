"""Typed models for the altcoin opportunity scanner."""

from __future__ import annotations

from pydantic import BaseModel, Field


class AltcoinRiskConfig(BaseModel):
    """Risk overrides loaded from configs/risk/altcoins.yml."""

    max_single_position_pct: float = Field(default=0.05)
    max_altcoin_exposure_pct: float = Field(default=0.15)
    max_stop_loss_pct: float = Field(default=0.05)
    max_leverage: int = Field(default=2)
    min_24h_volume_usd: float = Field(default=10_000_000)


class PairOpportunity(BaseModel):
    """A scored altcoin pair opportunity."""

    pair: str
    volume_24h: float
    funding_rate: float
    price_change_24h_pct: float
    estimated_spread: float = Field(default=0.0)
    opportunity_score: float
    reason: str
