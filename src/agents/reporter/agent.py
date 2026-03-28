"""Reporter agent loop for Telegram notifications, approvals, and reports.

Runs in send-only mode to avoid Telegram polling conflicts with OpenClaw.
Scheduled reports are driven by APScheduler directly (no python-telegram-bot polling).
"""

from __future__ import annotations

import argparse
import json
import logging
import signal
import time
from contextlib import ExitStack
from datetime import date, datetime, time as wall_clock_time, timezone
from pathlib import Path

from apscheduler.schedulers.background import BackgroundScheduler

from agents.reporter.approvals import ApprovalStore
from agents.reporter.formatters import format_daily_report, format_periodic_report
from agents.reporter.notifier import TelegramNotifier
from agents.trader.position_manager import PositionManager
from clients.portfolio import PortfolioClient
from clients.trading import TradingClient
from shared.config import ClientSettings


LOGGER = logging.getLogger("agents.reporter")


class ReporterAgent:
    def __init__(
        self,
        settings: ClientSettings | None = None,
        *,
        approval_store: ApprovalStore | None = None,
        notifier: TelegramNotifier | None = None,
        position_manager: PositionManager | None = None,
    ) -> None:
        self.settings = settings or ClientSettings.from_env()
        self.approval_store = approval_store or ApprovalStore()
        self.notifier = notifier or TelegramNotifier(
            settings=self.settings,
            approval_store=self.approval_store,
        )
        self.position_manager = position_manager or PositionManager()

    def _trade_open_count(self, target_date: date) -> int:
        count = 0
        trader_dir = Path("runtime/trader")
        for path in trader_dir.glob("*.jsonl"):
            for line in path.read_text(encoding="utf-8").splitlines():
                if not line:
                    continue
                try:
                    payload = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if payload.get("event") != "trade_opened":
                    continue
                raw_timestamp = payload.get("timestamp")
                if not raw_timestamp:
                    continue
                timestamp = datetime.fromisoformat(raw_timestamp.replace("Z", "+00:00"))
                if timestamp.date() == target_date:
                    count += 1
        return count

    def _signal_count(self, target_date: date) -> int:
        count = 0
        analyst_dir = Path("runtime/analyst")
        for path in analyst_dir.glob("*.jsonl"):
            for line in path.read_text(encoding="utf-8").splitlines():
                if not line:
                    continue
                try:
                    payload = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if payload.get("status") != "signal_generated":
                    continue
                raw_timestamp = payload.get("timestamp")
                if not raw_timestamp:
                    continue
                timestamp = datetime.fromisoformat(raw_timestamp.replace("Z", "+00:00"))
                if timestamp.date() == target_date:
                    count += 1
        return count

    def _snapshot(self) -> tuple[list, list]:
        with ExitStack() as stack:
            trading = stack.enter_context(TradingClient(settings=self.settings))
            portfolio = stack.enter_context(PortfolioClient(settings=self.settings))
            balances = portfolio.get_balances()
            positions = trading.get_positions()
            self.position_manager.sync_live_positions(positions)
        return balances, positions

    def build_periodic_report_text(self) -> str:
        balances, positions = self._snapshot()
        return format_periodic_report(
            balances=balances,
            positions=positions,
            managed_positions=self.position_manager.state.open_positions,
        )

    def build_daily_report_text(self, *, report_date: date | None = None) -> str:
        target_date = report_date or datetime.now(timezone.utc).date()
        balances, positions = self._snapshot()
        del balances
        closed_trades = [
            trade
            for trade in self.position_manager.state.closed_trades
            if trade.closed_at.date() == target_date
        ]
        realized_pnl = sum(trade.realized_pnl for trade in closed_trades)
        unrealized_pnl = sum(position.unrealized_pnl for position in positions)
        return format_daily_report(
            report_date=target_date,
            closed_trades=closed_trades,
            realized_pnl=realized_pnl,
            unrealized_pnl=unrealized_pnl,
            signal_count=self._signal_count(target_date),
            executed_count=self._trade_open_count(target_date),
        )

    def run(self) -> int:
        if not self.notifier.configured:
            LOGGER.warning("Reporter agent is not configured; TELEGRAM_BOT_TOKEN or TELEGRAM_OPERATOR_CHAT_ID missing.")
            return 0

        scheduler = BackgroundScheduler()
        scheduler.add_job(
            self._send_periodic_report,
            "interval",
            seconds=self.settings.report_interval_hours * 3600,
            next_run_time=datetime.now(timezone.utc),
            id="periodic-report",
        )
        scheduler.add_job(
            self._send_daily_report,
            "cron",
            hour=self.settings.daily_report_hour_utc,
            minute=0,
            timezone=timezone.utc,
            id="daily-report",
        )
        scheduler.start()

        LOGGER.info("Reporter running in send-only mode (no Telegram polling).")
        stop = False

        def _handle_signal(signum: int, frame: object) -> None:
            nonlocal stop
            stop = True

        signal.signal(signal.SIGTERM, _handle_signal)
        signal.signal(signal.SIGINT, _handle_signal)

        try:
            while not stop:
                time.sleep(10)
        except KeyboardInterrupt:
            pass
        finally:
            scheduler.shutdown(wait=False)
            LOGGER.info("Reporter stopped.")
        return 0

    def _send_periodic_report(self) -> None:
        try:
            self.notifier.send_periodic_report(self.build_periodic_report_text())
        except Exception:
            LOGGER.exception("Failed to send periodic report")

    def _send_daily_report(self) -> None:
        try:
            self.notifier.send_periodic_report(self.build_daily_report_text())
        except Exception:
            LOGGER.exception("Failed to send daily report")


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the Telegram reporter agent.")
    return parser


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    build_arg_parser().parse_args()
    return ReporterAgent().run()


if __name__ == "__main__":
    raise SystemExit(main())
