"""Unit coverage for the risk monitor agent."""

from __future__ import annotations

from agents.reporter.formatters import format_risk_alert
from agents.risk_monitor.agent import RiskMonitorAgent
from agents.risk_monitor.models import RiskAlert
from agents.trader.position_manager import ManagedPosition
from shared.config import ClientSettings
from shared.models import Balance, Candle, FundingRateInfo, MarketPrice, OpenPosition, Ticker24h


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
    def __init__(self, prices: dict[str, float] | None = None, funding_rates: dict[str, float] | None = None):
        self._prices = prices or {"BTC-USDT": 65000.0, "ETH-USDT": 3400.0}
        self._funding_rates = funding_rates or {"BTC-USDT": 0.0004, "ETH-USDT": 0.0002}

    def get_price(self, pair: str) -> MarketPrice:
        return MarketPrice(
            connector_name="binance_perpetual_testnet",
            trading_pair=pair,
            price=self._prices.get(pair, 65000.0),
            timestamp=1.0,
        )

    def get_ticker_24h(self, pair: str) -> Ticker24h:
        return Ticker24h(
            connector_name="binance_perpetual_testnet",
            trading_pair=pair,
            open_price=66000.0,
            last_price=self._prices.get(pair, 65000.0),
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
            funding_rate=self._funding_rates.get(pair, 0.0004),
            next_funding_time=1.0,
            mark_price=self._prices.get(pair, 65000.0) + 10.0,
            index_price=self._prices.get(pair, 65000.0) + 5.0,
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


class StubPositionManager:
    def __init__(self, positions: dict[str, ManagedPosition] | None = None):
        self._positions = positions or {}

    def daily_realized_pnl(self, as_of=None):
        return 0.0

    def get_open_position(self, pair: str) -> ManagedPosition | None:
        return self._positions.get(pair)


class StubNotifier:
    def __init__(self):
        self.alerts_sent: list[RiskAlert] = []
        self.messages_sent: list[str] = []

    def send_risk_alert(self, alert: RiskAlert) -> None:
        self.alerts_sent.append(alert)

    def _send(self, text: str, **kwargs) -> None:
        self.messages_sent.append(text)


def _make_settings(**overrides) -> ClientSettings:
    defaults = dict(
        moonshot_api_key="test-key",
        analyst_pairs=["BTC-USDT"],
    )
    defaults.update(overrides)
    return ClientSettings(**defaults)


# --- Stop proximity tests ---

def _make_agent(**overrides):
    defaults = dict(settings=_make_settings(), position_manager=StubPositionManager())
    defaults.update(overrides)
    return RiskMonitorAgent(**defaults)


def test_stop_proximity_triggers_warning():
    agent = _make_agent()
    position = OpenPosition(
        trading_pair="BTC-USDT",
        position_side="short",
        unrealized_pnl=-400.0,
        entry_price=65000.0,
        amount=-0.01,
    )
    managed = ManagedPosition(
        pair="BTC-USDT",
        side="short",
        size=0.01,
        entry_price=65000.0,
        stop_loss_price=66000.0,
        leverage=2.0,
        order_id="test-order",
        signal_confidence=0.8,
        reasoning="test",
    )
    # Price at 65900 means 900/1000 = 90% of stop distance used
    alert = agent.check_position_stop_proximity(position, managed, current_price=65900.0)
    assert alert is not None
    assert alert.severity == "warning"
    assert alert.alert_type == "stop_proximity"


def test_stop_proximity_no_alert_when_safe():
    agent = _make_agent()
    position = OpenPosition(
        trading_pair="BTC-USDT",
        position_side="short",
        unrealized_pnl=-100.0,
        entry_price=65000.0,
        amount=-0.01,
    )
    managed = ManagedPosition(
        pair="BTC-USDT",
        side="short",
        size=0.01,
        entry_price=65000.0,
        stop_loss_price=66000.0,
        leverage=2.0,
        order_id="test-order",
        signal_confidence=0.8,
        reasoning="test",
    )
    # Price at 65300 means 300/1000 = 30% -- safe
    alert = agent.check_position_stop_proximity(position, managed, current_price=65300.0)
    assert alert is None


def test_stop_proximity_long_position():
    agent = _make_agent()
    position = OpenPosition(
        trading_pair="ETH-USDT",
        position_side="long",
        unrealized_pnl=-80.0,
        entry_price=3500.0,
        amount=1.0,
    )
    managed = ManagedPosition(
        pair="ETH-USDT",
        side="long",
        size=1.0,
        entry_price=3500.0,
        stop_loss_price=3400.0,
        leverage=2.0,
        order_id="test-order",
        signal_confidence=0.8,
        reasoning="test",
    )
    # Price at 3415 means loss of 85/100 = 85% of stop distance
    alert = agent.check_position_stop_proximity(position, managed, current_price=3415.0)
    assert alert is not None
    assert alert.alert_type == "stop_proximity"


# --- Exposure tests ---

def test_exposure_limit_triggers():
    agent = _make_agent()
    positions = [
        OpenPosition(
            trading_pair="BTC-USDT",
            position_side="short",
            unrealized_pnl=0.0,
            entry_price=65000.0,
            amount=-0.04,  # 0.04 * 65000 = 2600 exposure
        )
    ]
    # 2600 / 10000 = 26%, limit is 30%, usage = 26/30 = 86.7%
    alert = agent.check_total_exposure(positions, total_equity=10000.0, max_exposure_pct=0.30)
    assert alert is not None
    assert alert.alert_type == "exposure_limit"


def test_exposure_limit_safe():
    agent = _make_agent()
    positions = [
        OpenPosition(
            trading_pair="BTC-USDT",
            position_side="short",
            unrealized_pnl=0.0,
            entry_price=65000.0,
            amount=-0.01,  # 0.01 * 65000 = 650 exposure
        )
    ]
    # 650 / 10000 = 6.5%, limit is 30%, usage = 6.5/30 = 21.7%
    alert = agent.check_total_exposure(positions, total_equity=10000.0, max_exposure_pct=0.30)
    assert alert is None


# --- Daily loss tests ---

def test_daily_loss_triggers():
    agent = _make_agent()
    # Loss of 450 on 10000 equity = 4.5%, limit 5%, usage = 90%
    alert = agent.check_daily_loss(daily_pnl=-450.0, total_equity=10000.0, max_daily_loss_pct=0.05)
    assert alert is not None
    assert alert.alert_type == "daily_loss_limit"


def test_daily_loss_safe():
    agent = _make_agent()
    # Loss of 100 on 10000 equity = 1%, limit 5%, usage = 20%
    alert = agent.check_daily_loss(daily_pnl=-100.0, total_equity=10000.0, max_daily_loss_pct=0.05)
    assert alert is None


def test_daily_loss_no_alert_when_positive():
    agent = _make_agent()
    alert = agent.check_daily_loss(daily_pnl=200.0, total_equity=10000.0, max_daily_loss_pct=0.05)
    assert alert is None


# --- Funding rate tests ---

def test_funding_rate_adverse_for_short():
    agent = _make_agent()
    # Negative funding is bad for shorts
    alert = agent.check_funding_rate("BTC-USDT", funding_rate=-0.0005, position_side="short")
    assert alert is not None
    assert alert.alert_type == "adverse_funding"


def test_funding_rate_adverse_for_long():
    agent = _make_agent()
    # Positive funding is bad for longs
    alert = agent.check_funding_rate("BTC-USDT", funding_rate=0.0005, position_side="long")
    assert alert is not None
    assert alert.alert_type == "adverse_funding"


def test_funding_rate_favorable():
    agent = _make_agent()
    # Positive funding is good for shorts
    alert = agent.check_funding_rate("BTC-USDT", funding_rate=0.0005, position_side="short")
    assert alert is None


def test_funding_rate_no_position():
    agent = _make_agent()
    alert = agent.check_funding_rate("BTC-USDT", funding_rate=-0.001, position_side=None)
    assert alert is None


# --- Volatility tests ---

def test_volatility_first_check_sets_baseline():
    agent = _make_agent()
    alert = agent.check_volatility("BTC-USDT", current_volatility=1.5)
    assert alert is None
    assert "BTC-USDT" in agent._baseline_volatility


def test_volatility_triggers_on_spike():
    agent = _make_agent()
    agent._baseline_volatility["BTC-USDT"] = 1.0
    alert = agent.check_volatility("BTC-USDT", current_volatility=2.5)
    assert alert is not None
    assert alert.alert_type == "unusual_volatility"
    assert alert.current_value > 2.0


def test_volatility_no_alert_normal():
    agent = _make_agent()
    agent._baseline_volatility["BTC-USDT"] = 1.0
    alert = agent.check_volatility("BTC-USDT", current_volatility=1.2)
    assert alert is None


# --- Integration: run_once ---

def test_run_once_no_positions(tmp_path):
    agent = RiskMonitorAgent(
        settings=_make_settings(),
        position_manager=StubPositionManager(),
        portfolio_client=StubPortfolioClient(positions=[]),
        market_data_client=StubMarketDataClient(),
    )
    agent.runtime_dir = tmp_path
    agent.log_path = tmp_path / "test.jsonl"

    alerts = agent.run_once()
    assert alerts == []


def test_run_once_with_alerts(tmp_path):
    managed = ManagedPosition(
        pair="BTC-USDT",
        side="short",
        size=0.01,
        entry_price=65000.0,
        stop_loss_price=66000.0,
        leverage=2.0,
        order_id="test-order",
        signal_confidence=0.8,
        reasoning="test",
    )
    notifier = StubNotifier()
    agent = RiskMonitorAgent(
        settings=_make_settings(),
        position_manager=StubPositionManager(positions={"BTC-USDT": managed}),
        portfolio_client=StubPortfolioClient(
            positions=[
                OpenPosition(
                    trading_pair="BTC-USDT",
                    position_side="short",
                    unrealized_pnl=-800.0,
                    entry_price=65000.0,
                    amount=-0.01,
                )
            ]
        ),
        # Price at 65900 triggers stop proximity alert
        market_data_client=StubMarketDataClient(prices={"BTC-USDT": 65900.0}),
        notifier=notifier,
    )
    agent.runtime_dir = tmp_path
    agent.log_path = tmp_path / "test.jsonl"

    alerts = agent.run_once()
    assert len(alerts) >= 1
    stop_alerts = [a for a in alerts if a.alert_type == "stop_proximity"]
    assert len(stop_alerts) == 1
    assert len(notifier.alerts_sent) >= 1


# --- Formatter tests ---

def test_format_risk_alert_warning():
    alert = RiskAlert(
        severity="warning",
        alert_type="stop_proximity",
        pair="BTC-USDT",
        message="BTC-USDT approaching stop loss",
        current_value=0.9,
        threshold=0.8,
    )
    text = format_risk_alert(alert)
    assert "WARNING" in text
    assert "stop_proximity" in text
    assert "BTC-USDT" in text


def test_format_risk_alert_critical():
    alert = RiskAlert(
        severity="critical",
        alert_type="daily_loss_limit",
        pair=None,
        message="Daily loss at 95% of limit",
        current_value=0.95,
        threshold=0.8,
    )
    text = format_risk_alert(alert)
    assert "CRITICAL" in text
    assert "daily_loss_limit" in text
