"""Unit coverage for the portfolio advisor agent."""

from __future__ import annotations

import json

from agents.advisor.agent import PortfolioAdvisorAgent
from agents.advisor.models import PortfolioAdvisory
from agents.reporter.formatters import format_advisory
from shared.config import ClientSettings
from shared.models import Balance, FundingRateInfo, MarketPrice, OpenPosition, Ticker24h
from shared.moonshot import (
    MoonshotChoice,
    MoonshotCompletion,
    MoonshotMessage,
    MoonshotToolCall,
    MoonshotToolCallFunction,
)


class StubPortfolioClient:
    def __init__(
        self,
        positions: list[OpenPosition] | None = None,
        balances: list[Balance] | None = None,
    ) -> None:
        self._positions = positions or []
        self._balances = balances or [
            Balance(
                account_name="master_account",
                connector_name="binance_perpetual_testnet",
                token="USDT",
                units=10000.0,
                available_units=8000.0,
                price=1.0,
                value=10000.0,
            )
        ]

    def get_positions(self) -> list[OpenPosition]:
        return self._positions

    def get_balances(self) -> list[Balance]:
        return self._balances


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


class StubMoonshotClient:
    def __init__(self, advisory_args: dict | None = None, no_tool_call: bool = False) -> None:
        self._advisory_args = advisory_args or {
            "portfolio_health": "healthy",
            "recommendations": ["Maintain current exposure levels", "Continue monitoring BTC correlation"],
            "reasoning": "Portfolio is well-balanced with moderate exposure and positive recent performance.",
            "suggested_actions": ["Review stop distances on ETH position", "Consider reducing leverage if volatility increases"],
        }
        self._no_tool_call = no_tool_call

    def chat_completion(self, **kwargs) -> MoonshotCompletion:
        if self._no_tool_call:
            return MoonshotCompletion(
                choices=[
                    MoonshotChoice(
                        index=0,
                        message=MoonshotMessage(role="assistant", content="No advisory needed at this time."),
                        finish_reason="stop",
                    )
                ]
            )
        return MoonshotCompletion(
            choices=[
                MoonshotChoice(
                    index=0,
                    message=MoonshotMessage(
                        role="assistant",
                        tool_calls=[
                            MoonshotToolCall(
                                id="call_1",
                                type="function",
                                function=MoonshotToolCallFunction(
                                    name="emit_advisory",
                                    arguments=json.dumps(self._advisory_args),
                                ),
                            )
                        ],
                    ),
                    finish_reason="tool_calls",
                )
            ]
        )

    @staticmethod
    def parse_tool_arguments(tool_call):
        return json.loads(tool_call.function.arguments)

    def __enter__(self):
        return self

    def __exit__(self, *_):
        pass


class StubPositionManager:
    class _State:
        closed_trades = []

    def __init__(self):
        self.state = self._State()

    def daily_realized_pnl(self, as_of=None):
        return 0.0


class StubNotifier:
    def __init__(self):
        self.advisories_sent: list[PortfolioAdvisory] = []

    def send_advisory(self, advisory: PortfolioAdvisory) -> None:
        self.advisories_sent.append(advisory)


def _make_settings(**overrides) -> ClientSettings:
    defaults = dict(
        moonshot_api_key="test-key",
        analyst_pairs=["BTC-USDT"],
    )
    defaults.update(overrides)
    return ClientSettings(**defaults)


def test_advisor_generates_advisory(tmp_path):
    notifier = StubNotifier()
    agent = PortfolioAdvisorAgent(
        settings=_make_settings(),
        position_manager=StubPositionManager(),
        portfolio_client=StubPortfolioClient(),
        market_data_client=StubMarketDataClient(),
        moonshot_client=StubMoonshotClient(),
        notifier=notifier,
    )
    agent.runtime_dir = tmp_path
    agent.log_path = tmp_path / "test.jsonl"

    advisory = agent.run_once()

    assert advisory is not None
    assert advisory.portfolio_health == "healthy"
    assert len(advisory.recommendations) == 2
    assert len(advisory.suggested_actions) == 2
    assert len(notifier.advisories_sent) == 1


def test_advisor_handles_no_tool_call(tmp_path):
    notifier = StubNotifier()
    agent = PortfolioAdvisorAgent(
        settings=_make_settings(),
        position_manager=StubPositionManager(),
        portfolio_client=StubPortfolioClient(),
        market_data_client=StubMarketDataClient(),
        moonshot_client=StubMoonshotClient(no_tool_call=True),
        notifier=notifier,
    )
    agent.runtime_dir = tmp_path
    agent.log_path = tmp_path / "test.jsonl"

    advisory = agent.run_once()

    assert advisory is None
    assert len(notifier.advisories_sent) == 0


def test_advisor_with_caution_health(tmp_path):
    notifier = StubNotifier()
    agent = PortfolioAdvisorAgent(
        settings=_make_settings(),
        position_manager=StubPositionManager(),
        portfolio_client=StubPortfolioClient(),
        market_data_client=StubMarketDataClient(),
        moonshot_client=StubMoonshotClient(advisory_args={
            "portfolio_health": "caution",
            "recommendations": ["Reduce BTC exposure"],
            "reasoning": "High concentration risk in BTC.",
            "suggested_actions": ["Close 50% of BTC position"],
        }),
        notifier=notifier,
    )
    agent.runtime_dir = tmp_path
    agent.log_path = tmp_path / "test.jsonl"

    advisory = agent.run_once()

    assert advisory is not None
    assert advisory.portfolio_health == "caution"
    assert "Reduce BTC exposure" in advisory.recommendations


def test_format_advisory():
    advisory = PortfolioAdvisory(
        portfolio_health="healthy",
        recommendations=["Keep current exposure"],
        reasoning="All metrics are within normal range.",
        suggested_actions=["No action needed"],
    )
    text = format_advisory(advisory)
    assert "Portfolio Advisory" in text
    assert "healthy" in text
    assert "Keep current exposure" in text


def test_summarize_positions_empty():
    result = PortfolioAdvisorAgent._summarize_positions([])
    assert "No open positions" in result


def test_summarize_positions_with_data():
    positions = [
        OpenPosition(
            trading_pair="BTC-USDT",
            position_side="short",
            unrealized_pnl=-50.0,
            entry_price=65000.0,
            amount=-0.01,
            leverage=2,
        )
    ]
    result = PortfolioAdvisorAgent._summarize_positions(positions)
    assert "BTC-USDT" in result
    assert "65000" in result
