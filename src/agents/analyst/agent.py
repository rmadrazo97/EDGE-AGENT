"""Market analyst loop backed by Moonshot structured outputs."""

from __future__ import annotations

import argparse
import json
import logging
import time
from contextlib import ExitStack
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from agents.analyst.prompts import ANALYST_SYSTEM_PROMPT, build_analyst_user_prompt
from agents.analyst.signals import AnalystCycleRecord, MarketSnapshot, ProposedTradeSignal, TradeSignal
from clients.base import HummingbotAPIConnectionError, HummingbotAPIError
from clients.market_data import MarketDataClient
from clients.portfolio import PortfolioClient
from shared.config import ClientSettings
from shared.math import calculate_realized_volatility
from shared.models import Candle, OpenPosition, OrderBookSnapshot
from shared.moonshot import MoonshotAPIError, MoonshotClient


LOGGER = logging.getLogger("agents.analyst")


class MarketAnalystAgent:
    signal_tool = {
        "type": "function",
        "function": {
            "name": "emit_trade_signal",
            "description": "Emit a conservative trade signal when the setup is strong enough.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pair": {"type": "string", "enum": ["BTC-USDT", "ETH-USDT"]},
                    "side": {"type": "string", "enum": ["long", "short"]},
                    "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
                    "entry_price": {"type": "number", "exclusiveMinimum": 0},
                    "stop_loss_price": {"type": "number", "exclusiveMinimum": 0},
                    "reasoning": {"type": "string"},
                },
                "required": ["pair", "side", "confidence", "entry_price", "stop_loss_price", "reasoning"],
            },
        },
    }

    def __init__(
        self,
        settings: ClientSettings | None = None,
        *,
        market_data_client: MarketDataClient | None = None,
        portfolio_client: PortfolioClient | None = None,
        moonshot_client: MoonshotClient | None = None,
        sleep_fn: Callable[[float], None] = time.sleep,
    ) -> None:
        self.settings = settings or ClientSettings.from_env()
        self.market_data_client = market_data_client
        self.portfolio_client = portfolio_client
        self.moonshot_client = moonshot_client
        self.sleep_fn = sleep_fn
        self.runtime_dir = Path("runtime/analyst")
        self.runtime_dir.mkdir(parents=True, exist_ok=True)
        self.log_path = self.runtime_dir / f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.jsonl"

    def _record(self, record: AnalystCycleRecord) -> None:
        with self.log_path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(record.model_dump(mode="json"), default=str) + "\n")
        LOGGER.info("%s %s", record.status, record.model_dump(exclude_none=True, mode="json"))

    @staticmethod
    def _calculate_order_book_imbalance(order_book: OrderBookSnapshot) -> tuple[float, float, float]:
        total_bid_depth = sum(level.amount for level in order_book.bids)
        total_ask_depth = sum(level.amount for level in order_book.asks)
        denominator = total_bid_depth + total_ask_depth
        imbalance = 0.0 if denominator == 0 else (total_bid_depth - total_ask_depth) / denominator
        return imbalance, total_bid_depth, total_ask_depth

    _calculate_realized_volatility = staticmethod(calculate_realized_volatility)

    def collect_market_snapshot(
        self,
        pair: str,
        *,
        market: MarketDataClient,
        portfolio: PortfolioClient,
    ) -> MarketSnapshot:
        price = market.get_price(pair)
        ticker = market.get_ticker_24h(pair)
        funding = market.get_funding_rate(pair)
        order_book = market.get_order_book(pair, depth=10)
        hourly_candles = market.get_klines(pair, interval="1h", limit=12)
        four_hour_candles = market.get_klines(pair, interval="4h", limit=12)
        positions = portfolio.get_positions()
        open_position = next((position for position in positions if position.trading_pair == pair), None)
        imbalance, total_bid_depth, total_ask_depth = self._calculate_order_book_imbalance(order_book)

        return MarketSnapshot(
            pair=pair,
            current_price=price.price,
            price_change_24h_pct=ticker.price_change_percent,
            funding_rate=funding.funding_rate,
            mark_price=funding.mark_price,
            index_price=funding.index_price,
            volume_24h=ticker.base_volume,
            quote_volume_24h=ticker.quote_volume,
            realized_volatility_24h_pct=self._calculate_realized_volatility(hourly_candles),
            order_book_imbalance=imbalance,
            total_bid_depth=total_bid_depth,
            total_ask_depth=total_ask_depth,
            hourly_candles=hourly_candles[-6:],
            four_hour_candles=four_hour_candles[-6:],
            open_position=open_position,
        )

    def request_signal(
        self,
        snapshot: MarketSnapshot,
        *,
        moonshot: MoonshotClient,
    ) -> ProposedTradeSignal | None:
        completion = moonshot.chat_completion(
            system_prompt=ANALYST_SYSTEM_PROMPT,
            user_prompt=build_analyst_user_prompt(snapshot),
            tools=[self.signal_tool],
        )
        if not completion.choices:
            raise MoonshotAPIError("Moonshot returned no choices.")

        message = completion.choices[0].message
        if not message.tool_calls:
            return None

        tool_call = message.tool_calls[0]
        if tool_call.function.name != "emit_trade_signal":
            raise MoonshotAPIError(f"Unexpected tool call: {tool_call.function.name}")

        return ProposedTradeSignal.model_validate(
            MoonshotClient.parse_tool_arguments(tool_call)
        )

    def _filter_signal(self, snapshot: MarketSnapshot, proposed: ProposedTradeSignal) -> tuple[TradeSignal | None, str | None]:
        if proposed.pair != snapshot.pair:
            return None, "model_returned_mismatched_pair"
        if proposed.side not in {"long", "short"}:
            return None, "model_returned_invalid_side"
        if proposed.confidence < self.settings.analyst_confidence_threshold:
            return None, "confidence_below_threshold"
        if snapshot.open_position is not None:
            return None, "conflicts_with_existing_open_position"

        entry_deviation_pct = abs(proposed.entry_price - snapshot.current_price) / snapshot.current_price
        if entry_deviation_pct > 0.02:
            return None, "entry_price_outside_reasonable_range"

        signal = TradeSignal(
            **proposed.model_dump(),
            data_snapshot=snapshot.model_dump(mode="json"),
        )
        return signal, None

    def analyze_pair(
        self,
        pair: str,
        *,
        market: MarketDataClient,
        portfolio: PortfolioClient,
        moonshot: MoonshotClient,
    ) -> TradeSignal | None:
        snapshot = self.collect_market_snapshot(pair, market=market, portfolio=portfolio)
        self._record(
            AnalystCycleRecord(
                status="analysis_started",
                pair=pair,
                data_snapshot=snapshot.model_dump(mode="json"),
            )
        )

        for attempt in range(1, self.settings.analyst_max_retries + 1):
            try:
                proposed_signal = self.request_signal(snapshot, moonshot=moonshot)
                if proposed_signal is None:
                    self._record(
                        AnalystCycleRecord(
                            status="no_signal",
                            pair=pair,
                            reason="model_declined_to_emit_signal",
                            data_snapshot=snapshot.model_dump(mode="json"),
                        )
                    )
                    return None

                signal, rejection_reason = self._filter_signal(snapshot, proposed_signal)
                if signal is None:
                    self._record(
                        AnalystCycleRecord(
                            status="signal_filtered",
                            pair=pair,
                            reason=rejection_reason,
                            data_snapshot=snapshot.model_dump(mode="json"),
                        )
                    )
                    return None

                self._record(
                    AnalystCycleRecord(
                        status="signal_generated",
                        pair=pair,
                        signal=signal,
                        data_snapshot=snapshot.model_dump(mode="json"),
                    )
                )
                return signal
            except (MoonshotAPIError, HummingbotAPIError, HummingbotAPIConnectionError, ValueError) as exc:
                if attempt >= self.settings.analyst_max_retries:
                    self._record(
                        AnalystCycleRecord(
                            status="analysis_failed",
                            pair=pair,
                            error=str(exc),
                            data_snapshot=snapshot.model_dump(mode="json"),
                        )
                    )
                    return None

                self._record(
                    AnalystCycleRecord(
                        status="analysis_retrying",
                        pair=pair,
                        reason=f"attempt {attempt} failed",
                        error=str(exc),
                        data_snapshot=snapshot.model_dump(mode="json"),
                    )
                )
                self.sleep_fn(self.settings.analyst_retry_backoff_seconds * attempt)
        return None

    def run_once(self) -> list[TradeSignal]:
        signals: list[TradeSignal] = []
        with ExitStack() as stack:
            market = self.market_data_client or stack.enter_context(MarketDataClient(settings=self.settings))
            portfolio = self.portfolio_client or stack.enter_context(PortfolioClient(settings=self.settings))
            moonshot = self.moonshot_client or stack.enter_context(MoonshotClient(settings=self.settings))

            for pair in self.settings.analyst_pairs:
                signal = self.analyze_pair(pair, market=market, portfolio=portfolio, moonshot=moonshot)
                if signal is not None:
                    signals.append(signal)

        return signals

    def run_forever(self) -> None:
        interval_seconds = self.settings.analyst_interval_minutes * 60
        while True:
            cycle_started_at = time.monotonic()
            self.run_once()
            elapsed = time.monotonic() - cycle_started_at
            sleep_seconds = max(0.0, interval_seconds - elapsed)
            self.sleep_fn(sleep_seconds)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the EDGE-AGENT market analyst.")
    parser.add_argument("--once", action="store_true", help="Run a single analysis cycle and exit.")
    return parser


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    args = build_arg_parser().parse_args()
    agent = MarketAnalystAgent()
    if args.once:
        agent.run_once()
        return 0

    agent.run_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
