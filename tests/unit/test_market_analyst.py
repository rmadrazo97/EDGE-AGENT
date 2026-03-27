"""Unit coverage for the market analyst agent."""

from __future__ import annotations

from collections import deque

from agents.analyst.agent import MarketAnalystAgent
from shared.config import ClientSettings
from shared.models import Candle, FundingRateInfo, MarketPrice, OpenPosition, OrderBookLevel, OrderBookSnapshot, Ticker24h
from shared.moonshot import MoonshotAPIError, MoonshotChoice, MoonshotCompletion, MoonshotMessage, MoonshotToolCall, MoonshotToolCallFunction


class StubMarketDataClient:
    def get_price(self, pair: str) -> MarketPrice:
        return MarketPrice(
            connector_name="binance_perpetual_testnet",
            trading_pair=pair,
            price=65000.0,
            timestamp=1.0,
        )

    def get_ticker_24h(self, pair: str) -> Ticker24h:
        return Ticker24h(
            connector_name="binance_perpetual_testnet",
            trading_pair=pair,
            open_price=66000.0,
            last_price=65000.0,
            high_price=66500.0,
            low_price=64500.0,
            base_volume=1200.0,
            quote_volume=78000000.0,
            price_change=-1000.0,
            price_change_percent=-1.515,
        )

    def get_funding_rate(self, pair: str) -> FundingRateInfo:
        return FundingRateInfo(
            trading_pair=pair,
            funding_rate=0.0004,
            next_funding_time=1.0,
            mark_price=65010.0,
            index_price=65005.0,
        )

    def get_order_book(self, pair: str, depth: int = 10) -> OrderBookSnapshot:
        return OrderBookSnapshot(
            trading_pair=pair,
            bids=[OrderBookLevel(price=64990.0, amount=4.0)],
            asks=[OrderBookLevel(price=65010.0, amount=9.0)],
            timestamp=1.0,
        )

    def get_klines(self, pair: str, interval: str = "1m", limit: int = 100) -> list[Candle]:
        candles: list[Candle] = []
        for index in range(limit):
            base = 66000.0 - (index * 20.0)
            candles.append(
                Candle(
                    timestamp=float(index),
                    open=base,
                    high=base + 50.0,
                    low=base - 75.0,
                    close=base - 25.0,
                    volume=100.0 + index,
                    quote_asset_volume=6500000.0 + index,
                    n_trades=50.0 + index,
                    taker_buy_base_volume=40.0 + index,
                    taker_buy_quote_volume=2600000.0 + index,
                )
            )
        return candles


class StubPortfolioClient:
    def __init__(self, positions: list[OpenPosition] | None = None) -> None:
        self._positions = positions or []

    def get_positions(self) -> list[OpenPosition]:
        return self._positions


class StubMoonshotClient:
    def __init__(self, responses: list[MoonshotCompletion | Exception]) -> None:
        self._responses = deque(responses)

    def chat_completion(self, **_: object) -> MoonshotCompletion:
        response = self._responses.popleft()
        if isinstance(response, Exception):
            raise response
        return response


def make_completion(tool_arguments: str | None) -> MoonshotCompletion:
    tool_calls = []
    if tool_arguments is not None:
        tool_calls.append(
            MoonshotToolCall(
                id="call-1",
                type="function",
                function=MoonshotToolCallFunction(
                    name="emit_short_signal",
                    arguments=tool_arguments,
                ),
            )
        )

    return MoonshotCompletion(
        id="cmpl-1",
        choices=[
            MoonshotChoice(
                index=0,
                message=MoonshotMessage(
                    role="assistant",
                    content=None,
                    tool_calls=tool_calls,
                ),
                finish_reason="tool_calls" if tool_calls else "stop",
            )
        ],
    )


def make_settings() -> ClientSettings:
    return ClientSettings(
        analyst_pairs=["BTC-USDT"],
        analyst_confidence_threshold=0.7,
        analyst_max_retries=3,
        analyst_retry_backoff_seconds=0.5,
    )


def test_analyst_generates_signal_when_model_output_passes_filters() -> None:
    agent = MarketAnalystAgent(
        settings=make_settings(),
        market_data_client=StubMarketDataClient(),
        portfolio_client=StubPortfolioClient(),
        moonshot_client=StubMoonshotClient(
            [
                make_completion(
                    '{"pair":"BTC-USDT","confidence":0.82,"entry_price":64980.0,"stop_loss_price":66300.0,"reasoning":"Funding is positive, price is weak, and asks outweigh bids."}'
                )
            ]
        ),
    )

    signals = agent.run_once()

    assert len(signals) == 1
    assert signals[0].pair == "BTC-USDT"
    assert signals[0].confidence == 0.82


def test_analyst_filters_low_confidence_signal() -> None:
    agent = MarketAnalystAgent(
        settings=make_settings(),
        market_data_client=StubMarketDataClient(),
        portfolio_client=StubPortfolioClient(),
        moonshot_client=StubMoonshotClient(
            [
                make_completion(
                    '{"pair":"BTC-USDT","confidence":0.55,"entry_price":64980.0,"stop_loss_price":66300.0,"reasoning":"Weak setup."}'
                )
            ]
        ),
    )

    signals = agent.run_once()

    assert signals == []


def test_analyst_filters_signal_when_position_already_open() -> None:
    agent = MarketAnalystAgent(
        settings=make_settings(),
        market_data_client=StubMarketDataClient(),
        portfolio_client=StubPortfolioClient(
            positions=[
                OpenPosition(
                    trading_pair="BTC-USDT",
                    position_side="BOTH",
                    unrealized_pnl=0.0,
                    entry_price=65000.0,
                    amount=-0.001,
                )
            ]
        ),
        moonshot_client=StubMoonshotClient(
            [
                make_completion(
                    '{"pair":"BTC-USDT","confidence":0.85,"entry_price":64980.0,"stop_loss_price":66300.0,"reasoning":"Would otherwise be valid."}'
                )
            ]
        ),
    )

    signals = agent.run_once()

    assert signals == []


def test_analyst_retries_after_transient_moonshot_error() -> None:
    sleep_calls: list[float] = []
    agent = MarketAnalystAgent(
        settings=make_settings(),
        market_data_client=StubMarketDataClient(),
        portfolio_client=StubPortfolioClient(),
        moonshot_client=StubMoonshotClient(
            [
                MoonshotAPIError("temporary upstream failure"),
                make_completion(
                    '{"pair":"BTC-USDT","confidence":0.8,"entry_price":64980.0,"stop_loss_price":66300.0,"reasoning":"Recovered on retry."}'
                ),
            ]
        ),
        sleep_fn=sleep_calls.append,
    )

    signals = agent.run_once()

    assert len(signals) == 1
    assert sleep_calls == [0.5]


def test_analyst_returns_no_signal_when_model_declines_tool_call() -> None:
    agent = MarketAnalystAgent(
        settings=make_settings(),
        market_data_client=StubMarketDataClient(),
        portfolio_client=StubPortfolioClient(),
        moonshot_client=StubMoonshotClient([make_completion(None)]),
    )

    signals = agent.run_once()

    assert signals == []
