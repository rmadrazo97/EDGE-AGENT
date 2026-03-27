"""Reporter agent loop for Telegram notifications, approvals, and reports."""

from __future__ import annotations

import argparse
import json
import logging
from contextlib import ExitStack
from datetime import date, datetime, time as wall_clock_time, timezone
from pathlib import Path

from telegram import Update
from telegram.ext import Application, ApplicationBuilder, CallbackContext, CallbackQueryHandler

from agents.reporter.approvals import ApprovalStore
from agents.reporter.formatters import format_daily_report, format_periodic_report
from agents.reporter.notifier import TelegramNotifier
from agents.trader.position_manager import PositionManager
from clients.market_data import MarketDataClient
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

    async def send_periodic_report_job(self, context: CallbackContext) -> None:
        del context
        self.notifier.send_periodic_report(self.build_periodic_report_text())

    async def send_daily_report_job(self, context: CallbackContext) -> None:
        del context
        self.notifier.send_periodic_report(self.build_daily_report_text())

    async def handle_approval_callback(self, update: Update, context: CallbackContext) -> None:
        del context
        query = update.callback_query
        if query is None:
            return
        handled, reason, resolution = self.approval_store.handle_callback(
            query.data or "",
            user_id=update.effective_user.id if update.effective_user else None,
            authorized_user_id=self.settings.telegram_operator_chat_id,
        )
        if not handled:
            if reason == "unauthorized":
                await query.answer("Unauthorized.", show_alert=True)
            elif reason == "not_found":
                await query.answer("Approval request not found.", show_alert=True)
            elif reason == "timed_out":
                await query.answer("Approval request timed out.", show_alert=True)
            else:
                await query.answer("Approval request is no longer pending.", show_alert=True)
            return

        await query.answer("Recorded.")
        await query.edit_message_reply_markup(reply_markup=None)
        await query.edit_message_text(
            f"{query.message.text_html}\n\nStatus: <code>{resolution.status}</code>",
            parse_mode="HTML",
        )

    def build_application(self) -> Application | None:
        if not self.notifier.configured:
            LOGGER.warning("Reporter agent is not configured; TELEGRAM_BOT_TOKEN or TELEGRAM_OPERATOR_CHAT_ID missing.")
            return None

        application = ApplicationBuilder().token(self.settings.telegram_bot_token).build()
        application.add_handler(CallbackQueryHandler(self.handle_approval_callback, pattern=r"^approval:"))
        if application.job_queue is None:
            raise RuntimeError("python-telegram-bot JobQueue is unavailable. Install APScheduler.")

        application.job_queue.run_repeating(
            self.send_periodic_report_job,
            interval=self.settings.report_interval_hours * 3600,
            first=60,
            name="periodic-report",
        )
        application.job_queue.run_daily(
            self.send_daily_report_job,
            time=wall_clock_time(hour=self.settings.daily_report_hour_utc, tzinfo=timezone.utc),
            name="daily-report",
        )
        return application

    def run(self) -> int:
        application = self.build_application()
        if application is None:
            return 0
        application.run_polling(allowed_updates=["callback_query"])
        return 0


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
