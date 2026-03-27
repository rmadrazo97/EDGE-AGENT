"""Typed signal and market snapshot models for the analyst agent."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from shared.models import Candle, OpenPosition


class MarketSnapshot(BaseModel):
    pair: str
    current_price: float
    price_change_24h_pct: float
    funding_rate: float
    mark_price: float
    index_price: float
    volume_24h: float
    quote_volume_24h: float
    realized_volatility_24h_pct: float
    order_book_imbalance: float
    total_bid_depth: float
    total_ask_depth: float
    hourly_candles: list[Candle]
    four_hour_candles: list[Candle]
    open_position: OpenPosition | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ProposedTradeSignal(BaseModel):
    pair: str
    side: str
    confidence: float
    entry_price: float
    stop_loss_price: float
    reasoning: str

    @model_validator(mode="after")
    def validate_signal(self) -> "ProposedTradeSignal":
        if self.side not in {"long", "short"}:
            raise ValueError("side must be one of: long, short")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0.0 and 1.0")
        if self.entry_price <= 0:
            raise ValueError("entry_price must be positive")
        if self.side == "short" and self.stop_loss_price <= self.entry_price:
            raise ValueError("stop_loss_price must be above entry_price for a short")
        if self.side == "long" and self.stop_loss_price >= self.entry_price:
            raise ValueError("stop_loss_price must be below entry_price for a long")
        stop_distance_pct = abs((self.stop_loss_price - self.entry_price) / self.entry_price) * 100
        if stop_distance_pct > 3.0:
            raise ValueError("stop_loss_price must be within 3% of entry_price")
        return self


class TradeSignal(ProposedTradeSignal):
    data_snapshot: dict[str, Any]
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class AnalystCycleRecord(BaseModel):
    model_config = ConfigDict(extra="allow")

    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    status: str
    pair: str | None = None
    signal: TradeSignal | None = None
    reason: str | None = None
    error: str | None = None
    data_snapshot: dict[str, Any] | None = None
