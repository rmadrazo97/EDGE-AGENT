"""Altcoin opportunity scanner — identifies high-potential perpetual pairs on Binance.

This scanner is **read-only**: it ranks altcoin pairs by opportunity score but
does not modify the trading configuration.  Adding a pair to `allowed_pairs`
still requires operator action.
"""

from __future__ import annotations

import argparse
import logging
import math
from contextlib import ExitStack
from pathlib import Path
from typing import Protocol

import yaml
from pydantic import BaseModel

from agents.scanner.models import AltcoinRiskConfig, PairOpportunity
from clients.base import HummingbotAPIConnectionError, HummingbotAPIError
from clients.market_data import MarketDataClient
from shared.config import ClientSettings
from shared.models import FundingRateInfo, OrderBookSnapshot, Ticker24h

LOGGER = logging.getLogger("agents.scanner")

# Pairs that are always excluded (majors already traded by the core agent).
_EXCLUDED_PAIRS = {"BTC-USDT", "ETH-USDT"}

# Default candidate altcoin pairs to scan when the Hummingbot API does not
# expose a dynamic pair-listing endpoint.
_DEFAULT_CANDIDATE_PAIRS: list[str] = [
    "SOL-USDT",
    "DOGE-USDT",
    "XRP-USDT",
    "ADA-USDT",
    "AVAX-USDT",
    "LINK-USDT",
    "DOT-USDT",
    "MATIC-USDT",
    "NEAR-USDT",
    "ARB-USDT",
    "OP-USDT",
    "APT-USDT",
    "SUI-USDT",
    "FIL-USDT",
    "ATOM-USDT",
    "LTC-USDT",
    "UNI-USDT",
    "INJ-USDT",
    "TIA-USDT",
    "FET-USDT",
    "PEPE-USDT",
    "WIF-USDT",
    "RENDER-USDT",
    "SEI-USDT",
    "RUNE-USDT",
]

# ── Scoring weights ──────────────────────────────────────────────────────
# The opportunity score is a simple weighted sum (0–100 scale).
_WEIGHT_VOLUME = 0.25
_WEIGHT_FUNDING = 0.25
_WEIGHT_VOLATILITY = 0.30
_WEIGHT_SPREAD = 0.20


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def load_altcoin_risk_config(path: Path | None = None) -> AltcoinRiskConfig:
    """Load altcoin risk overrides from the YAML config file."""
    if path is None:
        path = _repo_root() / "configs" / "risk" / "altcoins.yml"
    if not path.exists():
        return AltcoinRiskConfig()
    with path.open() as fh:
        raw = yaml.safe_load(fh) or {}
    return AltcoinRiskConfig.model_validate(raw)


# ── Market data protocol (for dependency injection / testing) ────────────

class MarketDataProvider(Protocol):
    """Minimal interface the scanner needs from a market data source."""

    def get_ticker_24h(self, pair: str) -> Ticker24h: ...
    def get_funding_rate(self, pair: str) -> FundingRateInfo: ...
    def get_order_book(self, pair: str, depth: int = 10) -> OrderBookSnapshot: ...


# ── Scoring helpers ──────────────────────────────────────────────────────

def _score_volume(quote_volume: float) -> float:
    """Score in [0, 100] — higher volume is better, log-scaled."""
    if quote_volume <= 0:
        return 0.0
    return min(100.0, math.log10(quote_volume) * 10)


def _score_funding(funding_rate: float) -> float:
    """Score in [0, 100] — extreme funding rates signal opportunity."""
    return min(100.0, abs(funding_rate) * 10_000)


def _score_volatility(price_change_pct: float) -> float:
    """Score in [0, 100] — large absolute price moves signal opportunity."""
    return min(100.0, abs(price_change_pct) * 10)


def _score_spread(best_bid: float, best_ask: float) -> tuple[float, float]:
    """Return (spread_pct, score) — tighter spread is better."""
    if best_bid <= 0 or best_ask <= 0:
        return 0.0, 0.0
    mid = (best_bid + best_ask) / 2
    spread_pct = (best_ask - best_bid) / mid * 100
    # A 0% spread => 100 score; 1% spread => 0 score (linear).
    score = max(0.0, 100.0 - spread_pct * 100)
    return spread_pct, score


def compute_opportunity_score(
    *,
    volume_score: float,
    funding_score: float,
    volatility_score: float,
    spread_score: float,
) -> float:
    """Weighted composite score (0–100)."""
    return (
        _WEIGHT_VOLUME * volume_score
        + _WEIGHT_FUNDING * funding_score
        + _WEIGHT_VOLATILITY * volatility_score
        + _WEIGHT_SPREAD * spread_score
    )


def _build_reason(
    funding_rate: float,
    price_change_pct: float,
    spread_pct: float,
) -> str:
    parts: list[str] = []
    if abs(funding_rate) >= 0.0003:
        direction = "positive" if funding_rate > 0 else "negative"
        parts.append(f"extreme {direction} funding ({funding_rate:+.4f})")
    if abs(price_change_pct) >= 3.0:
        direction = "up" if price_change_pct > 0 else "down"
        parts.append(f"high volatility ({price_change_pct:+.1f}% {direction})")
    if spread_pct <= 0.05:
        parts.append("tight spread")
    return "; ".join(parts) if parts else "moderate opportunity metrics"


# ── Scanner agent ────────────────────────────────────────────────────────

class AltcoinScannerAgent:
    """Scans altcoin perpetual pairs and ranks them by opportunity score.

    The scanner is intentionally **read-only** — it produces a ranked list of
    ``PairOpportunity`` objects but never modifies the live trading config.
    """

    def __init__(
        self,
        settings: ClientSettings | None = None,
        *,
        market_data_client: MarketDataProvider | None = None,
        risk_config: AltcoinRiskConfig | None = None,
        candidate_pairs: list[str] | None = None,
    ) -> None:
        self.settings = settings or ClientSettings.from_env()
        self._market_data_client = market_data_client
        self.risk_config = risk_config or load_altcoin_risk_config()
        self.candidate_pairs = [
            p for p in (candidate_pairs or _DEFAULT_CANDIDATE_PAIRS)
            if p not in _EXCLUDED_PAIRS
        ]

    def _evaluate_pair(
        self,
        pair: str,
        market: MarketDataProvider,
    ) -> PairOpportunity | None:
        """Collect data for *pair* and compute its opportunity score."""
        try:
            ticker = market.get_ticker_24h(pair)
            funding = market.get_funding_rate(pair)
            book = market.get_order_book(pair, depth=5)
        except (HummingbotAPIError, HummingbotAPIConnectionError, ValueError) as exc:
            LOGGER.warning("Skipping %s — data fetch failed: %s", pair, exc)
            return None

        quote_volume = ticker.quote_volume

        # Apply volume filter.
        if quote_volume < self.risk_config.min_24h_volume_usd:
            LOGGER.debug("Skipping %s — 24h volume $%.0f below threshold", pair, quote_volume)
            return None

        best_bid = book.bids[0].price if book.bids else 0.0
        best_ask = book.asks[0].price if book.asks else 0.0

        vol_score = _score_volume(quote_volume)
        fund_score = _score_funding(funding.funding_rate)
        volat_score = _score_volatility(ticker.price_change_percent)
        spread_pct, spr_score = _score_spread(best_bid, best_ask)

        score = compute_opportunity_score(
            volume_score=vol_score,
            funding_score=fund_score,
            volatility_score=volat_score,
            spread_score=spr_score,
        )

        reason = _build_reason(funding.funding_rate, ticker.price_change_percent, spread_pct)

        return PairOpportunity(
            pair=pair,
            volume_24h=quote_volume,
            funding_rate=funding.funding_rate,
            price_change_24h_pct=ticker.price_change_percent,
            estimated_spread=spread_pct,
            opportunity_score=round(score, 2),
            reason=reason,
        )

    def scan(self, top_n: int = 10) -> list[PairOpportunity]:
        """Evaluate all candidate pairs and return the top *top_n* by score."""
        with ExitStack() as stack:
            market: MarketDataProvider
            if self._market_data_client is not None:
                market = self._market_data_client
            else:
                client = MarketDataClient(settings=self.settings)
                stack.enter_context(client)
                market = client

            opportunities: list[PairOpportunity] = []
            for pair in self.candidate_pairs:
                result = self._evaluate_pair(pair, market)
                if result is not None:
                    opportunities.append(result)

        # Sort by score descending; break ties by volume descending.
        opportunities.sort(key=lambda o: (-o.opportunity_score, -o.volume_24h))
        return opportunities[:top_n]


# ── CLI entry-point ──────────────────────────────────────────────────────

def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Scan altcoin perpetual pairs for opportunities.")
    parser.add_argument(
        "--top",
        type=int,
        default=10,
        help="Number of top opportunities to display (default: 10).",
    )
    return parser


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    args = build_arg_parser().parse_args()
    agent = AltcoinScannerAgent()
    results = agent.scan(top_n=args.top)

    if not results:
        LOGGER.info("No altcoin opportunities found above thresholds.")
        return 0

    print(f"\n{'Rank':<5} {'Pair':<14} {'Score':>6} {'Volume 24h':>16} {'Funding':>10} {'Chg%':>8} {'Spread%':>9}  Reason")
    print("-" * 100)
    for rank, opp in enumerate(results, 1):
        print(
            f"{rank:<5} {opp.pair:<14} {opp.opportunity_score:>6.1f} "
            f"{opp.volume_24h:>16,.0f} {opp.funding_rate:>+10.4f} "
            f"{opp.price_change_24h_pct:>+8.2f} {opp.estimated_spread:>8.4f}%  "
            f"{opp.reason}"
        )
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
