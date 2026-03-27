"""Typed client models for the Hummingbot API responses used in EDGE-AGENT."""

from __future__ import annotations

from pydantic import AliasChoices, BaseModel, ConfigDict, Field


class MarketPrice(BaseModel):
    connector_name: str
    trading_pair: str
    price: float
    timestamp: float


class FundingRateInfo(BaseModel):
    trading_pair: str
    funding_rate: float
    next_funding_time: float
    mark_price: float
    index_price: float


class OrderBookLevel(BaseModel):
    price: float
    amount: float


class OrderBookSnapshot(BaseModel):
    trading_pair: str
    bids: list[OrderBookLevel]
    asks: list[OrderBookLevel]
    timestamp: float


class Candle(BaseModel):
    timestamp: float
    open: float
    high: float
    low: float
    close: float
    volume: float
    quote_asset_volume: float
    n_trades: float
    taker_buy_base_volume: float
    taker_buy_quote_volume: float


class Ticker24h(BaseModel):
    connector_name: str
    trading_pair: str
    open_price: float
    last_price: float
    high_price: float
    low_price: float
    base_volume: float
    quote_volume: float
    price_change: float
    price_change_percent: float


class Balance(BaseModel):
    account_name: str
    connector_name: str
    token: str
    units: float
    available_units: float
    price: float
    value: float


class Pagination(BaseModel):
    limit: int
    has_more: bool
    next_cursor: str | None = None
    total_count: int | None = None


class OpenPosition(BaseModel):
    model_config = ConfigDict(extra="ignore")

    trading_pair: str
    position_side: str | None = Field(
        default=None,
        validation_alias=AliasChoices("position_side", "side"),
    )
    unrealized_pnl: float
    entry_price: float
    amount: float
    leverage: int | float | None = None
    account_name: str | None = None
    connector_name: str | None = None


class PositionsResponse(BaseModel):
    data: list[OpenPosition] = Field(default_factory=list)
    pagination: Pagination
