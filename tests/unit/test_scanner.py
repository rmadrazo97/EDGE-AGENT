"""Unit tests for the altcoin opportunity scanner."""

from __future__ import annotations

from agents.scanner.agent import (
    AltcoinScannerAgent,
    _score_funding,
    _score_spread,
    _score_volatility,
    _score_volume,
    compute_opportunity_score,
)
from agents.scanner.models import AltcoinRiskConfig, PairOpportunity
from shared.config import ClientSettings
from shared.models import (
    FundingRateInfo,
    OrderBookLevel,
    OrderBookSnapshot,
    Ticker24h,
)


# ── Stub market data client ─────────────────────────────────────────────

class StubScannerMarketData:
    """Configurable stub that returns per-pair market data for testing."""

    def __init__(self, pair_data: dict[str, dict] | None = None) -> None:
        self._pair_data = pair_data or {}

    def _get(self, pair: str) -> dict:
        return self._pair_data.get(pair, {})

    def get_ticker_24h(self, pair: str) -> Ticker24h:
        data = self._get(pair)
        return Ticker24h(
            connector_name="binance_perpetual_testnet",
            trading_pair=pair,
            open_price=data.get("open_price", 100.0),
            last_price=data.get("last_price", 100.0),
            high_price=data.get("high_price", 105.0),
            low_price=data.get("low_price", 95.0),
            base_volume=data.get("base_volume", 1_000_000.0),
            quote_volume=data.get("quote_volume", 50_000_000.0),
            price_change=data.get("price_change", 0.0),
            price_change_percent=data.get("price_change_percent", 0.0),
        )

    def get_funding_rate(self, pair: str) -> FundingRateInfo:
        data = self._get(pair)
        return FundingRateInfo(
            trading_pair=pair,
            funding_rate=data.get("funding_rate", 0.0001),
            next_funding_time=1.0,
            mark_price=data.get("mark_price", 100.0),
            index_price=data.get("index_price", 100.0),
        )

    def get_order_book(self, pair: str, depth: int = 10) -> OrderBookSnapshot:
        data = self._get(pair)
        bid = data.get("best_bid", 99.95)
        ask = data.get("best_ask", 100.05)
        return OrderBookSnapshot(
            trading_pair=pair,
            bids=[OrderBookLevel(price=bid, amount=500.0)],
            asks=[OrderBookLevel(price=ask, amount=500.0)],
            timestamp=1.0,
        )


def _make_settings() -> ClientSettings:
    return ClientSettings(analyst_pairs=["BTC-USDT", "ETH-USDT"])


def _make_risk_config(**overrides: object) -> AltcoinRiskConfig:
    defaults = {
        "max_single_position_pct": 0.05,
        "max_altcoin_exposure_pct": 0.15,
        "max_stop_loss_pct": 0.05,
        "max_leverage": 2,
        "min_24h_volume_usd": 10_000_000,
    }
    defaults.update(overrides)
    return AltcoinRiskConfig(**defaults)


# ── Scoring unit tests ──────────────────────────────────────────────────

def test_score_volume_zero_returns_zero() -> None:
    assert _score_volume(0) == 0.0


def test_score_volume_positive() -> None:
    score = _score_volume(100_000_000)
    assert score > 0
    assert score <= 100


def test_score_funding_extreme() -> None:
    score = _score_funding(0.01)
    assert score == 100.0


def test_score_funding_mild() -> None:
    score = _score_funding(0.0001)
    assert 0 < score < 100


def test_score_volatility_high() -> None:
    score = _score_volatility(-12.0)
    assert score == 100.0


def test_score_volatility_low() -> None:
    score = _score_volatility(0.5)
    assert 0 < score < 100


def test_score_spread_tight() -> None:
    spread_pct, score = _score_spread(100.0, 100.01)
    assert spread_pct < 0.02
    assert score > 90


def test_score_spread_wide() -> None:
    spread_pct, score = _score_spread(100.0, 102.0)
    assert spread_pct > 1.0
    assert score == 0.0


def test_composite_score_weights_sum_correctly() -> None:
    score = compute_opportunity_score(
        volume_score=100,
        funding_score=100,
        volatility_score=100,
        spread_score=100,
    )
    assert score == 100.0


def test_composite_score_partial() -> None:
    score = compute_opportunity_score(
        volume_score=50,
        funding_score=0,
        volatility_score=0,
        spread_score=0,
    )
    assert score == 50 * 0.25


# ── Scanner agent tests ─────────────────────────────────────────────────

def test_scan_returns_opportunities_sorted_by_score() -> None:
    """The scanner should return opportunities sorted highest-score-first."""
    pair_data = {
        "SOL-USDT": {
            "quote_volume": 200_000_000,
            "funding_rate": 0.0005,
            "price_change_percent": 6.0,
            "best_bid": 150.0,
            "best_ask": 150.02,
        },
        "DOGE-USDT": {
            "quote_volume": 80_000_000,
            "funding_rate": 0.0001,
            "price_change_percent": 1.0,
            "best_bid": 0.15,
            "best_ask": 0.1502,
        },
        "XRP-USDT": {
            "quote_volume": 120_000_000,
            "funding_rate": 0.0008,
            "price_change_percent": -8.0,
            "best_bid": 0.60,
            "best_ask": 0.6002,
        },
    }
    agent = AltcoinScannerAgent(
        settings=_make_settings(),
        market_data_client=StubScannerMarketData(pair_data),
        risk_config=_make_risk_config(),
        candidate_pairs=["SOL-USDT", "DOGE-USDT", "XRP-USDT"],
    )

    results = agent.scan(top_n=10)

    assert len(results) == 3
    scores = [r.opportunity_score for r in results]
    assert scores == sorted(scores, reverse=True), "Results must be sorted by score descending"


def test_scan_filters_below_volume_threshold() -> None:
    """Pairs with quote volume below the threshold should be excluded."""
    pair_data = {
        "SOL-USDT": {"quote_volume": 200_000_000, "funding_rate": 0.0003, "price_change_percent": 4.0},
        "LOWVOL-USDT": {"quote_volume": 5_000_000, "funding_rate": 0.001, "price_change_percent": 10.0},
    }
    agent = AltcoinScannerAgent(
        settings=_make_settings(),
        market_data_client=StubScannerMarketData(pair_data),
        risk_config=_make_risk_config(min_24h_volume_usd=10_000_000),
        candidate_pairs=["SOL-USDT", "LOWVOL-USDT"],
    )

    results = agent.scan(top_n=10)

    pairs = [r.pair for r in results]
    assert "SOL-USDT" in pairs
    assert "LOWVOL-USDT" not in pairs


def test_scan_respects_top_n_limit() -> None:
    """The scanner should return at most top_n results."""
    pair_data = {
        f"PAIR{i}-USDT": {
            "quote_volume": 50_000_000 + i * 10_000_000,
            "funding_rate": 0.0002,
            "price_change_percent": 2.0 + i,
        }
        for i in range(5)
    }
    agent = AltcoinScannerAgent(
        settings=_make_settings(),
        market_data_client=StubScannerMarketData(pair_data),
        risk_config=_make_risk_config(),
        candidate_pairs=[f"PAIR{i}-USDT" for i in range(5)],
    )

    results = agent.scan(top_n=2)

    assert len(results) == 2


def test_scan_excludes_btc_and_eth() -> None:
    """BTC-USDT and ETH-USDT must always be excluded from altcoin scanning."""
    pair_data = {
        "BTC-USDT": {"quote_volume": 1_000_000_000, "funding_rate": 0.001, "price_change_percent": 5.0},
        "ETH-USDT": {"quote_volume": 500_000_000, "funding_rate": 0.001, "price_change_percent": 5.0},
        "SOL-USDT": {"quote_volume": 200_000_000, "funding_rate": 0.0003, "price_change_percent": 3.0},
    }
    agent = AltcoinScannerAgent(
        settings=_make_settings(),
        market_data_client=StubScannerMarketData(pair_data),
        risk_config=_make_risk_config(),
        candidate_pairs=["BTC-USDT", "ETH-USDT", "SOL-USDT"],
    )

    results = agent.scan(top_n=10)

    pairs = [r.pair for r in results]
    assert "BTC-USDT" not in pairs
    assert "ETH-USDT" not in pairs
    assert "SOL-USDT" in pairs


def test_scan_handles_api_error_gracefully() -> None:
    """If a pair fails to fetch, the scanner should skip it without crashing."""

    class FailingMarketData(StubScannerMarketData):
        def get_ticker_24h(self, pair: str) -> Ticker24h:
            if pair == "BAD-USDT":
                raise ValueError("API unreachable")
            return super().get_ticker_24h(pair)

    pair_data = {
        "SOL-USDT": {"quote_volume": 200_000_000, "funding_rate": 0.0003, "price_change_percent": 3.0},
    }
    agent = AltcoinScannerAgent(
        settings=_make_settings(),
        market_data_client=FailingMarketData(pair_data),
        risk_config=_make_risk_config(),
        candidate_pairs=["SOL-USDT", "BAD-USDT"],
    )

    results = agent.scan(top_n=10)

    assert len(results) == 1
    assert results[0].pair == "SOL-USDT"


def test_opportunity_model_fields() -> None:
    """Verify PairOpportunity model accepts all expected fields."""
    opp = PairOpportunity(
        pair="SOL-USDT",
        volume_24h=200_000_000,
        funding_rate=0.0005,
        price_change_24h_pct=6.0,
        estimated_spread=0.01,
        opportunity_score=72.5,
        reason="extreme positive funding (+0.0005); high volatility (+6.0% up)",
    )
    assert opp.pair == "SOL-USDT"
    assert opp.opportunity_score == 72.5
