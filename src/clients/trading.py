"""Trading client wrappers for the Hummingbot API."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from clients.base import HummingbotAPIClient
from shared.models import OpenPosition, Pagination


class TradeSubmission(BaseModel):
    order_id: str
    account_name: str
    connector_name: str
    trading_pair: str
    trade_type: str
    amount: Decimal
    order_type: str
    price: Decimal | None = None
    status: str


class ManagedStopLoss(BaseModel):
    trading_pair: str
    stop_price: float
    side: str
    trigger_above: bool
    status: str
    mode: str = "managed"
    created_at: datetime
    note: str


class ActiveOrder(BaseModel):
    model_config = ConfigDict(extra="allow")

    client_order_id: str | None = None
    order_id: str | None = None
    trading_pair: str | None = None
    connector_name: str | None = None
    account_name: str | None = None
    order_type: str | None = None
    trade_type: str | None = None
    amount: float | None = None
    price: float | None = None
    status: str | None = None


class ActiveOrdersResponse(BaseModel):
    data: list[ActiveOrder]
    pagination: Pagination


class CancelOrderResult(BaseModel):
    message: str


class LeverageResult(BaseModel):
    status: str
    message: str


class PositionModeResult(BaseModel):
    status: str | None = None
    message: str | None = None
    position_mode: str | None = None
    connector: str | None = None
    account: str | None = None


class TradingClient(HummingbotAPIClient):
    max_test_position_size: Decimal = Decimal("0.005")

    def _ensure_testnet_only(self) -> None:
        connector_name = self.settings.market_data_connector
        if connector_name != "binance_perpetual_testnet":
            raise ValueError(
                f"Refusing to trade on non-testnet connector: {connector_name}"
            )

    def set_leverage(self, pair: str, leverage: int) -> LeverageResult:
        self._ensure_testnet_only()
        payload = self._request_json(
            "POST",
            f"/trading/{self.settings.account_name}/{self.settings.market_data_connector}/leverage",
            json={"trading_pair": pair, "leverage": leverage},
        )
        return LeverageResult.model_validate(payload)

    def get_position_mode(self) -> PositionModeResult:
        self._ensure_testnet_only()
        payload = self._request_json(
            "GET",
            f"/trading/{self.settings.account_name}/{self.settings.market_data_connector}/position-mode",
        )
        return PositionModeResult.model_validate(payload)

    def set_position_mode(self, position_mode: str = "HEDGE") -> PositionModeResult:
        self._ensure_testnet_only()
        payload = self._request_json(
            "POST",
            f"/trading/{self.settings.account_name}/{self.settings.market_data_connector}/position-mode",
            json={"position_mode": position_mode},
        )
        return PositionModeResult.model_validate(payload)

    def _open_position(self, pair: str, size: Decimal, leverage: int, *, trade_type: str) -> TradeSubmission:
        self._ensure_testnet_only()
        if size > self.max_test_position_size:
            raise ValueError(
                f"Refusing size {size}: exceeds test cap of {self.max_test_position_size}"
            )

        self.set_leverage(pair, leverage)
        payload = self._request_json(
            "POST",
            "/trading/orders",
            json={
                "account_name": self.settings.account_name,
                "connector_name": self.settings.market_data_connector,
                "trading_pair": pair,
                "trade_type": trade_type,
                "amount": str(size),
                "order_type": "MARKET",
                "position_action": "OPEN",
            },
            expected_statuses=(200, 201),
        )
        return TradeSubmission.model_validate(payload)

    def open_short(self, pair: str, size: Decimal, leverage: int) -> TradeSubmission:
        return self._open_position(pair, size, leverage, trade_type="SELL")

    def open_long(self, pair: str, size: Decimal, leverage: int) -> TradeSubmission:
        return self._open_position(pair, size, leverage, trade_type="BUY")

    def set_stop_loss(self, pair: str, price: float, *, side: str = "short") -> ManagedStopLoss:
        self._ensure_testnet_only()
        is_short = side.lower() == "short"
        return ManagedStopLoss(
            trading_pair=pair,
            stop_price=price,
            side="BUY" if is_short else "SELL",
            trigger_above=is_short,
            status="armed",
            created_at=datetime.now(timezone.utc),
            note=(
                "Managed stop loss armed locally. The current Hummingbot API only exposes "
                "LIMIT, MARKET, and LIMIT_MAKER orders, so this pipeline monitors price and "
                "submits a market close if the trigger is hit."
            ),
        )

    def get_open_orders(self, pair: str) -> list[ActiveOrder]:
        self._ensure_testnet_only()
        payload = self._request_json(
            "POST",
            "/trading/orders/active",
            json={
                "account_names": [self.settings.account_name],
                "connector_names": [self.settings.market_data_connector],
                "trading_pairs": [pair],
            },
        )
        typed = ActiveOrdersResponse(
            data=[ActiveOrder.model_validate(order) for order in payload["data"]],
            pagination=Pagination.model_validate(payload["pagination"]),
        )
        return typed.data

    def get_positions(self, pair: str | None = None) -> list[OpenPosition]:
        self._ensure_testnet_only()
        payload = self._request_json(
            "POST",
            "/trading/positions",
            json={
                "account_names": [self.settings.account_name],
                "connector_names": [self.settings.market_data_connector],
            },
        )
        positions = [OpenPosition.model_validate(position) for position in payload["data"]]
        if pair is not None:
            positions = [position for position in positions if position.trading_pair == pair]
        return positions

    def close_position(self, pair: str) -> TradeSubmission:
        self._ensure_testnet_only()
        positions = self.get_positions(pair)
        if not positions:
            raise ValueError(f"No open position found for {pair}")

        position = positions[0]
        close_amount = abs(Decimal(str(position.amount)))
        is_short = Decimal(str(position.amount)) < 0
        payload = self._request_json(
            "POST",
            "/trading/orders",
            json={
                "account_name": self.settings.account_name,
                "connector_name": self.settings.market_data_connector,
                "trading_pair": pair,
                "trade_type": "BUY" if is_short else "SELL",
                "amount": str(close_amount),
                "order_type": "MARKET",
                "position_action": "CLOSE",
            },
            expected_statuses=(200, 201),
        )
        return TradeSubmission.model_validate(payload)

    def cancel_order(self, pair: str, order_id: str) -> CancelOrderResult:
        self._ensure_testnet_only()
        payload = self._request_json(
            "POST",
            f"/trading/{self.settings.account_name}/{self.settings.market_data_connector}/orders/{order_id}/cancel",
            params={"trading_pair": pair},
        )
        return CancelOrderResult.model_validate(payload)
