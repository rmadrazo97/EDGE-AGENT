"""Unit coverage for the thin Hummingbot API wrappers."""

from __future__ import annotations

import httpx
import pytest

from clients.accounts import AccountsClient
from clients.base import HummingbotAPIError
from clients.market_data import MarketDataClient
from clients.portfolio import PortfolioClient
from shared.config import ClientSettings


def test_market_data_client_parses_price_response() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert request.url.path == "/market-data/prices"
        return httpx.Response(
            200,
            json={
                "connector": "binance_perpetual_testnet",
                "prices": {"BTC-USDT": 67812.0},
                "timestamp": 1774605186.5,
            },
        )

    client = httpx.Client(
        transport=httpx.MockTransport(handler),
        base_url="http://testserver",
    )

    market_data = MarketDataClient(
        settings=ClientSettings(),
        http_client=client,
    )
    price = market_data.get_price("BTC-USDT")

    assert price.trading_pair == "BTC-USDT"
    assert price.price == 67812.0


def test_portfolio_client_flattens_balances() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/portfolio/state"
        return httpx.Response(
            200,
            json={
                "master_account": {
                    "binance_perpetual_testnet": [
                        {
                            "token": "USDT",
                            "units": 1000.0,
                            "available_units": 900.0,
                            "price": 1.0,
                            "value": 1000.0,
                        }
                    ]
                }
            },
        )

    client = httpx.Client(
        transport=httpx.MockTransport(handler),
        base_url="http://testserver",
    )

    portfolio = PortfolioClient(settings=ClientSettings(), http_client=client)
    balances = portfolio.get_balances()

    assert len(balances) == 1
    assert balances[0].connector_name == "binance_perpetual_testnet"
    assert balances[0].token == "USDT"


def test_portfolio_client_parses_oneway_positions() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/trading/positions"
        return httpx.Response(
            200,
            json={
                "data": [
                    {
                        "account_name": "master_account",
                        "connector_name": "binance_perpetual_testnet",
                        "trading_pair": "BTC-USDT",
                        "side": "BOTH",
                        "amount": -0.002,
                        "entry_price": 66143.0,
                        "unrealized_pnl": 0.15,
                        "leverage": 2.0,
                    }
                ],
                "pagination": {"limit": 100, "has_more": False, "next_cursor": None, "total_count": 1},
            },
        )

    client = httpx.Client(
        transport=httpx.MockTransport(handler),
        base_url="http://testserver",
    )

    portfolio = PortfolioClient(settings=ClientSettings(), http_client=client)
    positions = portfolio.get_positions()

    assert len(positions) == 1
    assert positions[0].position_side == "BOTH"
    assert positions[0].amount == -0.002


def test_client_raises_api_error_for_unsuccessful_response() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(400, json={"detail": "bad request"})

    client = httpx.Client(
        transport=httpx.MockTransport(handler),
        base_url="http://testserver",
    )

    market_data = MarketDataClient(settings=ClientSettings(), http_client=client)

    with pytest.raises(HummingbotAPIError) as exc_info:
        market_data.get_order_book("BTC-USDT")

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "bad request"


def test_accounts_client_requires_testnet_credentials() -> None:
    settings = ClientSettings(
        binance_testnet_api_key=None,
        binance_testnet_api_secret=None,
    )
    accounts = AccountsClient(settings=settings, http_client=httpx.Client(transport=httpx.MockTransport(lambda _: httpx.Response(200, json=[])), base_url="http://testserver"))

    with pytest.raises(ValueError, match="Missing Binance testnet credentials"):
        accounts.connect_binance_testnet()
