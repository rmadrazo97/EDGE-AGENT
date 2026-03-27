"""Unit tests for the trading client and pipeline safety checks."""

from __future__ import annotations

from decimal import Decimal

import httpx
import pytest

from clients.trading import TradingClient
from shared.config import ClientSettings


def test_open_short_sets_leverage_then_places_market_sell() -> None:
    calls: list[tuple[str, str]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append((request.method, request.url.path))
        if request.url.path.endswith("/leverage"):
            return httpx.Response(200, json={"status": "success", "message": "ok"})
        if request.url.path == "/trading/orders":
            return httpx.Response(
                201,
                json={
                    "order_id": "order-1",
                    "account_name": "master_account",
                    "connector_name": "binance_perpetual_testnet",
                    "trading_pair": "BTC-USDT",
                    "trade_type": "SELL",
                    "amount": "0.002",
                    "order_type": "MARKET",
                    "price": None,
                    "status": "submitted",
                },
            )
        raise AssertionError(request.url.path)

    client = httpx.Client(
        transport=httpx.MockTransport(handler),
        base_url="http://testserver",
    )
    trading = TradingClient(settings=ClientSettings(), http_client=client)
    submission = trading.open_short("BTC-USDT", Decimal("0.002"), 2)

    assert submission.trade_type == "SELL"
    assert calls == [
        ("POST", "/trading/master_account/binance_perpetual_testnet/leverage"),
        ("POST", "/trading/orders"),
    ]


def test_open_long_sets_leverage_then_places_market_buy() -> None:
    calls: list[tuple[str, str]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append((request.method, request.url.path))
        if request.url.path.endswith("/leverage"):
            return httpx.Response(200, json={"status": "success", "message": "ok"})
        if request.url.path == "/trading/orders":
            return httpx.Response(
                201,
                json={
                    "order_id": "order-2",
                    "account_name": "master_account",
                    "connector_name": "binance_perpetual_testnet",
                    "trading_pair": "BTC-USDT",
                    "trade_type": "BUY",
                    "amount": "0.002",
                    "order_type": "MARKET",
                    "price": None,
                    "status": "submitted",
                },
            )
        raise AssertionError(request.url.path)

    client = httpx.Client(
        transport=httpx.MockTransport(handler),
        base_url="http://testserver",
    )
    trading = TradingClient(settings=ClientSettings(), http_client=client)
    submission = trading.open_long("BTC-USDT", Decimal("0.002"), 2)

    assert submission.trade_type == "BUY"
    assert calls == [
        ("POST", "/trading/master_account/binance_perpetual_testnet/leverage"),
        ("POST", "/trading/orders"),
    ]


def test_set_stop_loss_returns_managed_stop_record() -> None:
    trading = TradingClient(
        settings=ClientSettings(),
        http_client=httpx.Client(transport=httpx.MockTransport(lambda _: httpx.Response(200)), base_url="http://testserver"),
    )

    stop_loss = trading.set_stop_loss("BTC-USDT", 70000.0, side="short")

    assert stop_loss.mode == "managed"
    assert stop_loss.status == "armed"
    assert stop_loss.trigger_above is True


def test_set_stop_loss_for_long_triggers_below() -> None:
    trading = TradingClient(
        settings=ClientSettings(),
        http_client=httpx.Client(transport=httpx.MockTransport(lambda _: httpx.Response(200)), base_url="http://testserver"),
    )

    stop_loss = trading.set_stop_loss("BTC-USDT", 64000.0, side="long")

    assert stop_loss.side == "SELL"
    assert stop_loss.trigger_above is False


def test_trading_client_refuses_non_testnet_connector() -> None:
    settings = ClientSettings(market_data_connector="binance_perpetual")
    trading = TradingClient(
        settings=settings,
        http_client=httpx.Client(transport=httpx.MockTransport(lambda _: httpx.Response(200)), base_url="http://testserver"),
    )

    with pytest.raises(ValueError, match="non-testnet connector"):
        trading.open_short("BTC-USDT", Decimal("0.002"), 2)


def test_close_position_submits_market_close() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/trading/positions":
            return httpx.Response(
                200,
                json={
                    "data": [
                        {
                            "trading_pair": "BTC-USDT",
                            "side": "BOTH",
                            "unrealized_pnl": 0.0,
                            "entry_price": 67000.0,
                            "amount": -0.002,
                            "leverage": 2,
                        }
                    ],
                    "pagination": {"limit": 100, "has_more": False, "next_cursor": None, "total_count": 1},
                },
            )
        if request.url.path == "/trading/orders":
            return httpx.Response(
                201,
                json={
                    "order_id": "close-1",
                    "account_name": "master_account",
                    "connector_name": "binance_perpetual_testnet",
                    "trading_pair": "BTC-USDT",
                    "trade_type": "BUY",
                    "amount": "0.002",
                    "order_type": "MARKET",
                    "price": None,
                    "status": "submitted",
                },
            )
        raise AssertionError(request.url.path)

    trading = TradingClient(
        settings=ClientSettings(),
        http_client=httpx.Client(transport=httpx.MockTransport(handler), base_url="http://testserver"),
    )
    submission = trading.close_position("BTC-USDT")

    assert submission.trade_type == "BUY"
