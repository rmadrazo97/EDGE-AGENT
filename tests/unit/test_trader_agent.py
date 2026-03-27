"""Unit coverage for the trader agent and position manager."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

from agents.analyst.signals import ShortSignal
from agents.trader.agent import TraderAgent
from agents.trader.position_manager import PositionManager
from clients.trading import ManagedStopLoss, TradeSubmission
from policy.engine import PolicyEngine
from shared.config import ClientSettings
from shared.models import Balance, FundingRateInfo, MarketPrice, OpenPosition, Ticker24h
from shared.moonshot import MoonshotChoice, MoonshotCompletion, MoonshotMessage, MoonshotToolCall, MoonshotToolCallFunction


class StubTradingClient:
    def __init__(self) -> None:
        self.open_calls: list[tuple[str, Decimal, int]] = []
        self.close_calls: list[str] = []
        self.position_mode_calls: list[str] = []
        self.positions: list[OpenPosition] = []

    def set_position_mode(self, mode: str) -> object:
        self.position_mode_calls.append(mode)
        return {"position_mode": mode}

    def open_short(self, pair: str, size: Decimal, leverage: int) -> TradeSubmission:
        self.open_calls.append((pair, size, leverage))
        self.positions = [
            OpenPosition(
                trading_pair=pair,
                position_side="BOTH",
                unrealized_pnl=0.0,
                entry_price=50000.0,
                amount=-float(size),
            )
        ]
        return TradeSubmission(
            order_id="order-1",
            account_name="master_account",
            connector_name="binance_perpetual_testnet",
            trading_pair=pair,
            trade_type="SELL",
            amount=size,
            order_type="MARKET",
            status="submitted",
        )

    def set_stop_loss(self, pair: str, price: float) -> ManagedStopLoss:
        return ManagedStopLoss(
            trading_pair=pair,
            stop_price=price,
            side="BUY",
            trigger_above=True,
            status="armed",
            created_at=datetime.now(timezone.utc),
            note="managed",
        )

    def get_positions(self, pair: str | None = None) -> list[OpenPosition]:
        if pair is None:
            return self.positions
        return [position for position in self.positions if position.trading_pair == pair]

    def close_position(self, pair: str) -> TradeSubmission:
        self.close_calls.append(pair)
        self.positions = []
        return TradeSubmission(
            order_id="close-1",
            account_name="master_account",
            connector_name="binance_perpetual_testnet",
            trading_pair=pair,
            trade_type="BUY",
            amount=Decimal("0.002"),
            order_type="MARKET",
            status="submitted",
        )


class StubPortfolioClient:
    def get_balances(self) -> list[Balance]:
        return [
            Balance(
                account_name="master_account",
                connector_name="binance_perpetual_testnet",
                token="USDT",
                units=5000.0,
                available_units=5000.0,
                price=1.0,
                value=5000.0,
            )
        ]


class StubMarketDataClient:
    def get_price(self, pair: str) -> MarketPrice:
        return MarketPrice(
            connector_name="binance_perpetual_testnet",
            trading_pair=pair,
            price=50000.0 if pair == "BTC-USDT" else 2000.0,
            timestamp=1.0,
        )

    def get_ticker_24h(self, pair: str) -> Ticker24h:
        return Ticker24h(
            connector_name="binance_perpetual_testnet",
            trading_pair=pair,
            open_price=51000.0,
            last_price=50000.0,
            high_price=51500.0,
            low_price=49500.0,
            base_volume=1000.0,
            quote_volume=50000000.0,
            price_change=-1000.0,
            price_change_percent=-1.96,
        )

    def get_funding_rate(self, pair: str) -> FundingRateInfo:
        return FundingRateInfo(
            trading_pair=pair,
            funding_rate=0.0002,
            next_funding_time=1.0,
            mark_price=50010.0,
            index_price=50005.0,
        )


class StubMoonshotClient:
    def __init__(self, completion: MoonshotCompletion) -> None:
        self.completion = completion

    def chat_completion(self, **_: object) -> MoonshotCompletion:
        return self.completion


def make_close_completion(pair: str) -> MoonshotCompletion:
    return MoonshotCompletion(
        choices=[
            MoonshotChoice(
                index=0,
                message=MoonshotMessage(
                    role="assistant",
                    tool_calls=[
                        MoonshotToolCall(
                            id="tool-1",
                            type="function",
                            function=MoonshotToolCallFunction(
                                name="close_position",
                                arguments=f'{{"pair":"{pair}","reason":"momentum turned against the short"}}',
                            ),
                        )
                    ],
                ),
                finish_reason="tool_calls",
            )
        ]
    )


def make_no_tool_completion() -> MoonshotCompletion:
    return MoonshotCompletion(
        choices=[
            MoonshotChoice(
                index=0,
                message=MoonshotMessage(role="assistant", content="hold", tool_calls=[]),
                finish_reason="stop",
            )
        ]
    )


def write_policy_config(path: Path) -> None:
    path.write_text(
        "\n".join(
            [
                "trading_enabled: true",
                "max_risk_per_trade_pct: 0.02",
                "max_daily_loss_pct: 0.05",
                "max_total_exposure_pct: 0.30",
                "max_single_position_pct: 0.10",
                "max_leverage: 3",
                "require_stop_loss: true",
                "max_stop_loss_pct: 0.03",
                "allowed_pairs:",
                "  - BTC-USDT",
                "  - ETH-USDT",
            ]
        )
    )


def sample_signal() -> ShortSignal:
    return ShortSignal(
        pair="BTC-USDT",
        confidence=0.85,
        entry_price=50000.0,
        stop_loss_price=51000.0,
        reasoning="valid short",
        data_snapshot={"pair": "BTC-USDT"},
    )


def make_trader(tmp_path: Path, *, moonshot_completion: MoonshotCompletion | None = None) -> tuple[TraderAgent, StubTradingClient]:
    config_path = tmp_path / "policy.yml"
    audit_path = tmp_path / "policy.jsonl"
    state_path = tmp_path / "state.json"
    write_policy_config(config_path)
    trading = StubTradingClient()
    trader = TraderAgent(
        settings=ClientSettings(),
        policy_engine=PolicyEngine(config_path=config_path, audit_log_path=audit_path),
        position_manager=PositionManager(state_path=state_path),
        trading_client=trading,
        portfolio_client=StubPortfolioClient(),
        market_data_client=StubMarketDataClient(),
        moonshot_client=StubMoonshotClient(moonshot_completion or make_no_tool_completion()),
    )
    return trader, trading


def test_position_manager_persists_and_restores_state(tmp_path: Path) -> None:
    manager = PositionManager(state_path=tmp_path / "state.json")
    signal = sample_signal()

    manager.record_open(signal=signal, size=0.002, leverage=2.0, order_id="open-1")
    manager.record_close("BTC-USDT", exit_price=49500.0, reason="tp")

    restored = PositionManager(state_path=tmp_path / "state.json")

    assert restored.get_open_position("BTC-USDT") is None
    assert len(restored.state.closed_trades) == 1
    assert restored.daily_realized_pnl() == 1.0


def test_trader_processes_policy_approved_signal(tmp_path: Path) -> None:
    trader, trading = make_trader(tmp_path)

    decisions = trader.run_once([sample_signal()])

    assert decisions[0].approved is True
    assert trading.position_mode_calls == ["ONEWAY"]
    assert trading.open_calls
    assert trader.position_manager.get_open_position("BTC-USDT") is not None


def test_trader_blocks_policy_rejected_signal(tmp_path: Path) -> None:
    trader, trading = make_trader(tmp_path)
    rejected_signal = sample_signal().model_copy(update={"pair": "SOL-USDT"})

    decisions = trader.run_once([rejected_signal])

    assert decisions[0].approved is False
    assert trading.open_calls == []


def test_trader_reviews_positions_and_closes_when_model_calls_tool(tmp_path: Path) -> None:
    trader, trading = make_trader(tmp_path, moonshot_completion=make_close_completion("BTC-USDT"))
    trader.position_manager.record_open(signal=sample_signal(), size=0.002, leverage=2.0, order_id="open-1")
    trading.positions = [
        OpenPosition(
            trading_pair="BTC-USDT",
            position_side="BOTH",
            unrealized_pnl=-5.0,
            entry_price=50000.0,
            amount=-0.002,
        )
    ]

    trader.review_positions(
        trading=trading,
        market=StubMarketDataClient(),
        moonshot=StubMoonshotClient(make_close_completion("BTC-USDT")),
    )

    assert trading.close_calls == ["BTC-USDT"]
    assert trader.position_manager.get_open_position("BTC-USDT") is None
