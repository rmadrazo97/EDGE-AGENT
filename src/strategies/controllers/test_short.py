"""Hardcoded short pipeline to validate testnet trading plumbing."""

from __future__ import annotations

import json
import logging
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

from clients.base import HummingbotAPIError
from clients.market_data import MarketDataClient
from clients.trading import ManagedStopLoss, TradingClient


LOGGER = logging.getLogger("strategies.controllers.test_short")


@dataclass
class TradeLifecycleEvent:
    timestamp: str
    stage: str
    details: dict


class TestShortController:
    pair = "BTC-USDT"
    size = Decimal("0.002")
    leverage = 2
    wait_seconds = 60
    poll_interval_seconds = 2
    max_position_wait_seconds = 20

    def __init__(self) -> None:
        self.runtime_dir = Path("runtime/test-trade")
        self.runtime_dir.mkdir(parents=True, exist_ok=True)
        self.log_path = self.runtime_dir / f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.jsonl"

    def _record(self, stage: str, **details: object) -> None:
        event = TradeLifecycleEvent(
            timestamp=datetime.now(timezone.utc).isoformat(),
            stage=stage,
            details=dict(details),
        )
        with self.log_path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(asdict(event), default=str) + "\n")
        LOGGER.info("%s %s", stage, details)

    def _wait_for_position(self, trading: TradingClient) -> object:
        deadline = time.monotonic() + self.max_position_wait_seconds
        while time.monotonic() < deadline:
            positions = trading.get_positions(self.pair)
            if positions:
                return positions[0]
            time.sleep(self.poll_interval_seconds)
        raise TimeoutError(f"Position for {self.pair} did not appear within {self.max_position_wait_seconds}s")

    def _wait_for_flat(self, trading: TradingClient) -> None:
        deadline = time.monotonic() + self.max_position_wait_seconds
        while time.monotonic() < deadline:
            if not trading.get_positions(self.pair):
                return
            time.sleep(self.poll_interval_seconds)
        raise TimeoutError(f"Position for {self.pair} did not close within {self.max_position_wait_seconds}s")

    def _ensure_clean_state(self, trading: TradingClient) -> None:
        positions = trading.get_positions(self.pair)
        if not positions:
            return

        self._record(
            "preexisting_position_detected",
            count=len(positions),
            amount=positions[0].amount,
            entry_price=positions[0].entry_price,
        )
        close_submission = trading.close_position(self.pair)
        self._record("preexisting_position_close_submitted", **close_submission.model_dump(mode="json"))
        self._wait_for_flat(trading)
        self._record("preexisting_position_cleared", pair=self.pair)

    def run(self) -> int:
        with TradingClient() as trading, MarketDataClient() as market:
            self._record(
                "pipeline_started",
                pair=self.pair,
                size=str(self.size),
                leverage=self.leverage,
                wait_seconds=self.wait_seconds,
                log_path=str(self.log_path),
            )

            trading._ensure_testnet_only()
            mode_result = trading.get_position_mode()
            if mode_result.position_mode != "ONEWAY":
                self._record("position_mode_mismatch", reported_mode=mode_result.position_mode, target_mode="ONEWAY")
                mode_result = trading.set_position_mode("ONEWAY")
            self._record("position_mode", **mode_result.model_dump())
            self._ensure_clean_state(trading)

            open_submission = trading.open_short(self.pair, self.size, self.leverage)
            self._record("short_submitted", **open_submission.model_dump(mode="json"))

            position = self._wait_for_position(trading)
            entry_price = float(position.entry_price)
            stop_price = round(entry_price * 1.03, 2)
            self._record("position_opened", **position.model_dump())

            stop_loss = trading.set_stop_loss(self.pair, stop_price)
            self._record("stop_loss_armed", **stop_loss.model_dump(mode="json"))

            exit_reason = "timeout"
            end_time = time.monotonic() + self.wait_seconds
            while time.monotonic() < end_time:
                current_price = market.get_price(self.pair).price
                self._record("price_tick", current_price=current_price, stop_price=stop_loss.stop_price)
                if current_price >= stop_loss.stop_price:
                    exit_reason = "managed_stop_loss"
                    break
                time.sleep(self.poll_interval_seconds)

            pre_close_price = market.get_price(self.pair).price
            close_submission = trading.close_position(self.pair)
            self._record(
                "close_submitted",
                reason=exit_reason,
                market_price=pre_close_price,
                **close_submission.model_dump(mode="json"),
            )

            self._wait_for_flat(trading)
            exit_price = pre_close_price
            realized_pnl = (entry_price - exit_price) * float(self.size)
            self._record(
                "pipeline_completed",
                entry_price=entry_price,
                exit_price=exit_price,
                pnl_quote=realized_pnl,
                reason=exit_reason,
            )
        return 0


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    controller = TestShortController()
    try:
        return controller.run()
    except (HummingbotAPIError, TimeoutError, ValueError) as exc:
        controller._record("pipeline_failed", error_type=type(exc).__name__, error=str(exc))
        LOGGER.error("Test short pipeline failed: %s", exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
