"""Telegram notification sender for alerts, reports, and approval requests."""

from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path

from telegram import Bot, Message
from telegram.constants import ParseMode

from agents.analyst.signals import ShortSignal
from agents.reporter.approvals import ApprovalResolution, ApprovalStore
from agents.reporter.formatters import (
    format_approval_request,
    format_close_alert,
    format_daily_loss_halt,
    format_periodic_report,
    format_stop_loss_alert,
    format_trade_alert,
)
from policy.models import PolicyDecision, TradeProposal
from shared.config import ClientSettings


LOGGER = logging.getLogger("agents.reporter.notifier")


class TelegramNotifier:
    def __init__(
        self,
        settings: ClientSettings | None = None,
        *,
        approval_store: ApprovalStore | None = None,
        bot: Bot | None = None,
        audit_log_path: str | Path = "runtime/audit/telegram.jsonl",
    ) -> None:
        self.settings = settings or ClientSettings.from_env()
        self.approval_store = approval_store or ApprovalStore()
        self.audit_log_path = Path(audit_log_path)
        self.audit_log_path.parent.mkdir(parents=True, exist_ok=True)
        self.bot = bot or (
            Bot(token=self.settings.telegram_bot_token)
            if self.settings.telegram_bot_token
            else None
        )

    @property
    def configured(self) -> bool:
        return self.bot is not None and self.settings.telegram_operator_chat_id is not None

    def _append_audit(self, event: str, **payload: object) -> None:
        record = {
            "event": event,
            "payload": payload,
        }
        with self.audit_log_path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(record, default=str) + "\n")

    def _send(self, text: str, *, reply_markup: object | None = None) -> Message | None:
        if not self.configured:
            LOGGER.warning("Telegram notifier is not configured; skipping message send.")
            return None
        try:
            message = asyncio.run(
                self.bot.send_message(
                    chat_id=self.settings.telegram_operator_chat_id,
                    text=text,
                    parse_mode=ParseMode.HTML,
                    reply_markup=reply_markup,
                )
            )
        except Exception as exc:
            LOGGER.warning("Telegram send failed: %s", exc)
            return None
        self._append_audit("notification_sent", text=text)
        return message

    def send_trade_alert(
        self,
        *,
        pair: str,
        side: str,
        size: float,
        entry_price: float,
        leverage: float,
        reasoning: str,
    ) -> None:
        self._send(
            format_trade_alert(
                pair=pair,
                side=side,
                size=size,
                entry_price=entry_price,
                leverage=leverage,
                reasoning=reasoning,
            )
        )

    def send_close_alert(
        self,
        *,
        pair: str,
        realized_pnl: float,
        duration_seconds: float | int | None,
        reason: str,
    ) -> None:
        self._send(
            format_close_alert(
                pair=pair,
                realized_pnl=realized_pnl,
                duration_seconds=duration_seconds,
                reason=reason,
            )
        )

    def send_stop_loss_alert(self, *, pair: str, realized_pnl: float) -> None:
        self._send(format_stop_loss_alert(pair=pair, realized_pnl=realized_pnl))

    def send_daily_loss_halt(self, *, current_daily_pnl: float, loss_limit_pct: float) -> None:
        self._send(
            format_daily_loss_halt(
                current_daily_pnl=current_daily_pnl,
                loss_limit_pct=loss_limit_pct,
            )
        )

    def send_periodic_report(self, text: str) -> None:
        self._send(text)

    def request_approval(
        self,
        signal: ShortSignal,
        proposal: TradeProposal,
        decision: PolicyDecision,
    ) -> ApprovalResolution:
        request = self.approval_store.create(
            signal,
            proposal,
            decision,
            timeout_seconds=self.settings.approval_timeout_seconds,
        )
        message = self._send(
            format_approval_request(request),
            reply_markup=ApprovalStore.approval_markup(request.request_id),
        )
        if message is not None:
            self.approval_store.attach_message(request.request_id, message.message_id)
        return self.approval_store.wait_for_resolution(request.request_id)
