"""Continuous rule-based risk surveillance agent."""

from __future__ import annotations

import argparse
import json
import logging
import time
from contextlib import ExitStack
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from agents.reporter.notifier import TelegramNotifier
from agents.risk_monitor.models import RiskAlert
from agents.trader.position_manager import ManagedPosition, PositionManager
from clients.market_data import MarketDataClient
from clients.portfolio import PortfolioClient
from shared.config import ClientSettings
from shared.math import calculate_realized_volatility
from shared.models import Candle, OpenPosition


LOGGER = logging.getLogger("agents.risk_monitor")


class RiskMonitorAgent:
    def __init__(
        self,
        settings: ClientSettings | None = None,
        *,
        position_manager: PositionManager | None = None,
        portfolio_client: PortfolioClient | None = None,
        market_data_client: MarketDataClient | None = None,
        notifier: TelegramNotifier | None = None,
        sleep_fn: Callable[[float], None] = time.sleep,
    ) -> None:
        self.settings = settings or ClientSettings.from_env()
        self.position_manager = position_manager or PositionManager()
        self.portfolio_client = portfolio_client
        self.market_data_client = market_data_client
        self.notifier = notifier
        self.sleep_fn = sleep_fn
        self.runtime_dir = Path("runtime/risk-monitor")
        self.runtime_dir.mkdir(parents=True, exist_ok=True)
        self.log_path = self.runtime_dir / f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.jsonl"
        self._baseline_volatility: dict[str, float] = {}

    def _record(self, event: str, **details: object) -> None:
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": event,
            "details": details,
        }
        with self.log_path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(payload, default=str) + "\n")
        LOGGER.info("%s %s", event, details)

    _calculate_realized_volatility = staticmethod(calculate_realized_volatility)

    def check_position_stop_proximity(
        self,
        position: OpenPosition,
        managed: ManagedPosition,
        current_price: float,
    ) -> RiskAlert | None:
        stop_distance = abs(managed.entry_price - managed.stop_loss_price)
        if stop_distance <= 0:
            return None

        if managed.side == "long":
            unrealized_loss_distance = max(0.0, managed.entry_price - current_price)
        else:
            unrealized_loss_distance = max(0.0, current_price - managed.entry_price)

        loss_ratio = unrealized_loss_distance / stop_distance
        if loss_ratio >= 0.8:
            return RiskAlert(
                severity="warning" if loss_ratio < 0.95 else "critical",
                alert_type="stop_proximity",
                pair=position.trading_pair,
                message=(
                    f"{position.trading_pair} unrealized loss at {loss_ratio * 100:.0f}% of stop distance. "
                    f"Entry={managed.entry_price:.2f} Current={current_price:.2f} Stop={managed.stop_loss_price:.2f}"
                ),
                current_value=loss_ratio,
                threshold=0.8,
            )
        return None

    def check_total_exposure(
        self,
        positions: list[OpenPosition],
        total_equity: float,
        max_exposure_pct: float,
    ) -> RiskAlert | None:
        if total_equity <= 0:
            return None
        total_exposure = sum(abs(p.amount) * p.entry_price for p in positions)
        exposure_ratio = total_exposure / total_equity
        limit_usage = exposure_ratio / max_exposure_pct if max_exposure_pct > 0 else 0.0
        if limit_usage >= 0.8:
            return RiskAlert(
                severity="warning" if limit_usage < 1.0 else "critical",
                alert_type="exposure_limit",
                pair=None,
                message=(
                    f"Total exposure at {limit_usage * 100:.0f}% of limit. "
                    f"Exposure={total_exposure:.2f} Equity={total_equity:.2f} Limit={max_exposure_pct * 100:.0f}%"
                ),
                current_value=limit_usage,
                threshold=0.8,
            )
        return None

    def check_daily_loss(
        self,
        daily_pnl: float,
        total_equity: float,
        max_daily_loss_pct: float,
    ) -> RiskAlert | None:
        if total_equity <= 0 or daily_pnl >= 0:
            return None
        loss_pct = abs(daily_pnl) / total_equity
        limit_usage = loss_pct / max_daily_loss_pct if max_daily_loss_pct > 0 else 0.0
        if limit_usage >= 0.8:
            return RiskAlert(
                severity="warning" if limit_usage < 1.0 else "critical",
                alert_type="daily_loss_limit",
                pair=None,
                message=(
                    f"Daily loss at {limit_usage * 100:.0f}% of limit. "
                    f"PnL={daily_pnl:.2f} Equity={total_equity:.2f} Limit={max_daily_loss_pct * 100:.0f}%"
                ),
                current_value=limit_usage,
                threshold=0.8,
            )
        return None

    def check_funding_rate(
        self,
        pair: str,
        funding_rate: float,
        position_side: str | None,
    ) -> RiskAlert | None:
        if position_side is None:
            return None
        # Negative funding means shorts pay longs (bad for shorts)
        # Positive funding means longs pay shorts (bad for longs)
        bad_for_position = False
        if position_side in ("short", "SHORT") and funding_rate < 0:
            bad_for_position = True
        elif position_side in ("long", "LONG") and funding_rate > 0:
            bad_for_position = True

        if bad_for_position and abs(funding_rate) > 0.0001:
            return RiskAlert(
                severity="info",
                alert_type="adverse_funding",
                pair=pair,
                message=(
                    f"{pair} funding rate {funding_rate:.6f} is adverse for {position_side} position. "
                    f"This costs the position on each funding interval."
                ),
                current_value=abs(funding_rate),
                threshold=0.0001,
            )
        return None

    def check_volatility(
        self,
        pair: str,
        current_volatility: float,
    ) -> RiskAlert | None:
        baseline = self._baseline_volatility.get(pair)
        if baseline is None or baseline <= 0:
            # Store current as baseline for future comparison
            self._baseline_volatility[pair] = current_volatility
            return None

        ratio = current_volatility / baseline if baseline > 0 else 0.0
        # Update baseline with exponential moving average
        self._baseline_volatility[pair] = baseline * 0.9 + current_volatility * 0.1

        if ratio > 2.0:
            return RiskAlert(
                severity="warning",
                alert_type="unusual_volatility",
                pair=pair,
                message=(
                    f"{pair} volatility is {ratio:.1f}x normal. "
                    f"Current={current_volatility:.4f}% Baseline={baseline:.4f}%"
                ),
                current_value=ratio,
                threshold=2.0,
            )
        return None

    def run_once(self) -> list[RiskAlert]:
        alerts: list[RiskAlert] = []

        with ExitStack() as stack:
            portfolio = self.portfolio_client or stack.enter_context(PortfolioClient(settings=self.settings))
            market = self.market_data_client or stack.enter_context(MarketDataClient(settings=self.settings))

            positions = portfolio.get_positions()
            if not positions:
                self._record("check_completed", alerts_count=0, reason="no_open_positions")
                return alerts

            balances = portfolio.get_balances()
            total_equity = sum(b.value for b in balances)
            daily_pnl = self.position_manager.daily_realized_pnl()

            # Check total exposure
            exposure_alert = self.check_total_exposure(positions, total_equity, max_exposure_pct=0.30)
            if exposure_alert:
                alerts.append(exposure_alert)

            # Check daily loss
            loss_alert = self.check_daily_loss(daily_pnl, total_equity, max_daily_loss_pct=0.05)
            if loss_alert:
                alerts.append(loss_alert)

            # Per-position checks
            for position in positions:
                pair = position.trading_pair
                managed = self.position_manager.get_open_position(pair)

                try:
                    price = market.get_price(pair)
                    current_price = price.price
                except Exception as exc:
                    self._record("price_fetch_failed", pair=pair, error=str(exc))
                    continue

                # Stop proximity
                if managed is not None:
                    stop_alert = self.check_position_stop_proximity(position, managed, current_price)
                    if stop_alert:
                        alerts.append(stop_alert)

                # Funding rate
                try:
                    funding = market.get_funding_rate(pair)
                    side = managed.side if managed else position.position_side
                    funding_alert = self.check_funding_rate(pair, funding.funding_rate, side)
                    if funding_alert:
                        alerts.append(funding_alert)
                except Exception as exc:
                    self._record("funding_fetch_failed", pair=pair, error=str(exc))

                # Volatility
                try:
                    candles = market.get_klines(pair, interval="1h", limit=12)
                    volatility = self._calculate_realized_volatility(candles)
                    vol_alert = self.check_volatility(pair, volatility)
                    if vol_alert:
                        alerts.append(vol_alert)
                except Exception as exc:
                    self._record("volatility_fetch_failed", pair=pair, error=str(exc))

        # Log and notify
        self._record("check_completed", alerts_count=len(alerts))
        for alert in alerts:
            self._record(
                "alert_raised",
                severity=alert.severity,
                alert_type=alert.alert_type,
                pair=alert.pair,
                message=alert.message,
            )
            if self.notifier is not None:
                self.notifier.send_risk_alert(alert)

        # Check for convergence of critical signals
        critical_count = sum(1 for a in alerts if a.severity == "critical")
        if critical_count >= 2:
            self._record("emergency_convergence", critical_alerts=critical_count)
            if self.notifier is not None:
                self.notifier._send(
                    f"EMERGENCY: {critical_count} critical risk signals detected simultaneously. "
                    "Consider immediate position reduction."
                )

        return alerts

    def run_forever(self) -> None:
        interval_seconds = self.settings.risk_monitor_interval_seconds
        while True:
            cycle_started_at = time.monotonic()
            self.run_once()
            elapsed = time.monotonic() - cycle_started_at
            sleep_seconds = max(0.0, interval_seconds - elapsed)
            self.sleep_fn(sleep_seconds)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the EDGE-AGENT risk monitor.")
    parser.add_argument("--once", action="store_true", help="Run a single risk check and exit.")
    return parser


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    args = build_arg_parser().parse_args()
    agent = RiskMonitorAgent()
    if args.once:
        agent.run_once()
        return 0

    agent.run_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
