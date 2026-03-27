"""Unit coverage for Telegram notifier formatting and approvals."""

from __future__ import annotations

from datetime import date, datetime, timezone
from pathlib import Path

from agents.analyst.signals import ShortSignal
from agents.reporter.approvals import ApprovalResolution, ApprovalStore
from agents.reporter.formatters import (
    format_approval_request,
    format_close_alert,
    format_daily_loss_halt,
    format_daily_report,
    format_periodic_report,
    format_stop_loss_alert,
    format_trade_alert,
)
from agents.reporter.notifier import TelegramNotifier
from agents.trader.position_manager import ClosedTrade, ManagedPosition
from policy.models import PolicyDecision, TradeProposal
from shared.config import ClientSettings
from shared.models import Balance, OpenPosition


class FakeTelegramMessage:
    def __init__(self, message_id: int) -> None:
        self.message_id = message_id


class FakeBot:
    def __init__(self) -> None:
        self.messages: list[dict[str, object]] = []

    async def send_message(self, **kwargs: object) -> FakeTelegramMessage:
        self.messages.append(kwargs)
        return FakeTelegramMessage(message_id=len(self.messages))


def sample_signal() -> ShortSignal:
    return ShortSignal(
        pair="BTC-USDT",
        confidence=0.84,
        entry_price=65000.0,
        stop_loss_price=66500.0,
        reasoning="Funding positive and structure weak.",
        data_snapshot={"pair": "BTC-USDT"},
    )


def sample_proposal() -> TradeProposal:
    return TradeProposal(
        pair="BTC-USDT",
        side="short",
        size=0.002,
        leverage=2.0,
        entry_price=65000.0,
        stop_loss_price=66500.0,
        signal_confidence=0.84,
        reasoning="Funding positive and structure weak.",
    )


def sample_decision() -> PolicyDecision:
    return PolicyDecision(
        approved=False,
        violations=["pair BTC-USDT requires operator review"],
        warnings=[],
    )


def sample_balances() -> list[Balance]:
    return [
        Balance(
            account_name="master_account",
            connector_name="binance_perpetual_testnet",
            token="USDT",
            units=1500.0,
            available_units=1300.0,
            price=1.0,
            value=1500.0,
        )
    ]


def sample_positions() -> list[OpenPosition]:
    return [
        OpenPosition(
            trading_pair="BTC-USDT",
            position_side="BOTH",
            unrealized_pnl=12.5,
            entry_price=65000.0,
            amount=-0.002,
        )
    ]


def sample_managed_positions() -> dict[str, ManagedPosition]:
    return {
        "BTC-USDT": ManagedPosition(
            pair="BTC-USDT",
            size=0.002,
            entry_price=65000.0,
            stop_loss_price=66500.0,
            leverage=2.0,
            order_id="order-1",
            signal_confidence=0.84,
            reasoning="Funding positive and structure weak.",
        )
    }


def sample_closed_trade() -> ClosedTrade:
    opened_at = datetime(2026, 3, 27, 10, 0, tzinfo=timezone.utc)
    return ClosedTrade(
        pair="BTC-USDT",
        size=0.002,
        entry_price=65000.0,
        exit_price=64600.0,
        leverage=2.0,
        stop_loss_price=66500.0,
        opened_at=opened_at,
        closed_at=datetime(2026, 3, 27, 10, 45, tzinfo=timezone.utc),
        reason="momentum faded",
        realized_pnl=0.8,
    )


def test_formatter_outputs_cover_all_alert_types(tmp_path: Path) -> None:
    decision = sample_decision()
    store = ApprovalStore(
        path=tmp_path / "approvals.json",
        audit_log_path=tmp_path / "policy.jsonl",
    )
    request = store.create(sample_signal(), sample_proposal(), decision, timeout_seconds=300)

    trade_text = format_trade_alert(
        pair="BTC-USDT",
        side="short",
        size=0.002,
        entry_price=65000.0,
        leverage=2.0,
        reasoning="Funding positive and structure weak.",
    )
    close_text = format_close_alert(
        pair="BTC-USDT",
        realized_pnl=0.8,
        duration_seconds=2700,
        reason="momentum faded",
    )
    stop_text = format_stop_loss_alert(pair="BTC-USDT", realized_pnl=-12.0)
    halt_text = format_daily_loss_halt(current_daily_pnl=-52.0, loss_limit_pct=0.05)
    periodic_text = format_periodic_report(
        balances=sample_balances(),
        positions=sample_positions(),
        managed_positions=sample_managed_positions(),
    )
    daily_text = format_daily_report(
        report_date=date(2026, 3, 27),
        closed_trades=[sample_closed_trade()],
        realized_pnl=0.8,
        unrealized_pnl=12.5,
        signal_count=3,
        executed_count=1,
    )
    approval_text = format_approval_request(request)

    assert "Trade opened" in trade_text
    assert "🔴" in format_close_alert(pair="BTC-USDT", realized_pnl=-1.0, duration_seconds=60, reason="stop")
    assert "Stop loss triggered" in stop_text
    assert "Daily loss limit hit" in halt_text
    assert "Periodic report" in periodic_text
    assert "Daily report" in daily_text
    assert "Approval requested" in approval_text
    assert "<code>" in trade_text
    assert "<code>" in close_text


def test_approval_timeout_behavior(tmp_path: Path) -> None:
    store = ApprovalStore(
        path=tmp_path / "approvals.json",
        audit_log_path=tmp_path / "policy.jsonl",
        sleep_fn=lambda _: None,
    )
    request = store.create(sample_signal(), sample_proposal(), sample_decision(), timeout_seconds=0)

    resolution = store.wait_for_resolution(request.request_id)

    assert resolution == ApprovalResolution(
        request_id=request.request_id,
        status="timed_out",
        approved=False,
    )


def test_unauthorized_callback_is_rejected(tmp_path: Path) -> None:
    store = ApprovalStore(
        path=tmp_path / "approvals.json",
        audit_log_path=tmp_path / "policy.jsonl",
    )
    request = store.create(sample_signal(), sample_proposal(), sample_decision(), timeout_seconds=300)

    handled, reason, resolution = store.handle_callback(
        f"approval:approve:{request.request_id}",
        user_id=999,
        authorized_user_id=123,
    )

    assert handled is False
    assert reason == "unauthorized"
    assert resolution is None
    assert store.get(request.request_id).status == "pending"


def test_notifier_sends_trade_alert_with_stub_bot(tmp_path: Path) -> None:
    settings = ClientSettings(
        telegram_bot_token="123456:token",
        telegram_operator_chat_id=12345,
    )
    store = ApprovalStore(
        path=tmp_path / "approvals.json",
        audit_log_path=tmp_path / "policy.jsonl",
    )
    fake_bot = FakeBot()
    notifier = TelegramNotifier(
        settings=settings,
        approval_store=store,
        bot=fake_bot,
        audit_log_path=tmp_path / "telegram.jsonl",
    )

    notifier.send_trade_alert(
        pair="BTC-USDT",
        side="short",
        size=0.002,
        entry_price=65000.0,
        leverage=2.0,
        reasoning="Funding positive and structure weak.",
    )

    assert len(fake_bot.messages) == 1
    assert fake_bot.messages[0]["chat_id"] == 12345
    assert "Trade opened" in fake_bot.messages[0]["text"]
