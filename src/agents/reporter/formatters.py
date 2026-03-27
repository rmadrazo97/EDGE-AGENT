"""Formatting helpers for Telegram notifications and reports."""

from __future__ import annotations

from datetime import date, datetime, timezone
from html import escape

from agents.reporter.approvals import ApprovalRequest
from agents.trader.position_manager import ClosedTrade, ManagedPosition
from shared.models import Balance, OpenPosition


def _code(value: object) -> str:
    return f"<code>{escape(str(value))}</code>"


def _minutes(seconds: float | int | None) -> str:
    if not seconds:
        return "n/a"
    return f"{max(int(round(float(seconds) / 60.0)), 0)}m"


def format_trade_alert(
    *,
    pair: str,
    side: str,
    size: float,
    entry_price: float,
    leverage: float,
    reasoning: str,
) -> str:
    return "\n".join(
        [
            "Trade opened",
            f"- pair {_code(pair)} {escape(side.upper())}",
            f"- size {_code(f'{size:.6f}')} lev {_code(leverage)}",
            f"- entry {_code(f'{entry_price:.2f}')}",
            f"- thesis {_code(reasoning)}",
        ]
    )


def format_close_alert(
    *,
    pair: str,
    realized_pnl: float,
    duration_seconds: float | int | None,
    reason: str,
) -> str:
    icon = "🟢" if realized_pnl >= 0 else "🔴"
    return "\n".join(
        [
            f"{icon} Position closed",
            f"- pair {_code(pair)}",
            f"- pnl {_code(f'{realized_pnl:.2f}')}",
            f"- duration {_code(_minutes(duration_seconds))}",
            f"- reason {_code(reason)}",
        ]
    )


def format_stop_loss_alert(*, pair: str, realized_pnl: float) -> str:
    return "\n".join(
        [
            "⚠️ Stop loss triggered",
            f"- pair {_code(pair)}",
            f"- realized pnl {_code(f'{realized_pnl:.2f}')}",
        ]
    )


def format_daily_loss_halt(*, current_daily_pnl: float, loss_limit_pct: float) -> str:
    return "\n".join(
        [
            "⚠️ Daily loss limit hit",
            f"- realized today {_code(f'{current_daily_pnl:.2f}')}",
            f"- limit {_code(f'{loss_limit_pct * 100:.1f}%')}",
            "- new entries are blocked by policy",
        ]
    )


def format_periodic_report(
    *,
    balances: list[Balance],
    positions: list[OpenPosition],
    managed_positions: dict[str, ManagedPosition],
) -> str:
    if not positions:
        equity = sum(balance.value for balance in balances)
        return "\n".join(
            [
                "Periodic report",
                f"- equity {_code(f'{equity:.2f}')}",
                "- open positions none",
            ]
        )

    lines = ["Periodic report"]
    total_unrealized = sum(position.unrealized_pnl for position in positions)
    lines.append(f"- unrealized pnl {_code(f'{total_unrealized:.2f}')}")
    for position in positions:
        managed = managed_positions.get(position.trading_pair)
        stop_label = f"{managed.stop_loss_price:.2f}" if managed else "n/a"
        lines.append(
            f"- {escape(position.trading_pair)} {_code(f'{position.amount:.6f}')} "
            f"entry {_code(f'{position.entry_price:.2f}')} "
            f"upnl {_code(f'{position.unrealized_pnl:.2f}')} "
            f"stop {_code(stop_label)}"
        )
    return "\n".join(lines)


def format_daily_report(
    *,
    report_date: date,
    closed_trades: list[ClosedTrade],
    realized_pnl: float,
    unrealized_pnl: float,
    signal_count: int,
    executed_count: int,
) -> str:
    wins = sum(1 for trade in closed_trades if trade.realized_pnl > 0)
    win_rate = (wins / len(closed_trades) * 100.0) if closed_trades else 0.0
    return "\n".join(
        [
            f"Daily report {_code(report_date.isoformat())}",
            f"- trades closed {_code(len(closed_trades))}",
            f"- realized {_code(f'{realized_pnl:.2f}')}",
            f"- unrealized {_code(f'{unrealized_pnl:.2f}')}",
            f"- win rate {_code(f'{win_rate:.1f}%')}",
            f"- signals/executed {_code(f'{signal_count}/{executed_count}')}",
        ]
    )


def format_approval_request(request: ApprovalRequest) -> str:
    remaining_seconds = (request.expires_at - datetime.now(timezone.utc)).total_seconds()
    status_line = request.status if request.status != "pending" else _minutes(remaining_seconds)
    decision_summary = ", ".join(request.policy_decision.violations or request.policy_decision.warnings) or "manual review"
    return "\n".join(
        [
            "⚠️ Approval requested",
            f"- pair {_code(request.proposal.pair)}",
            f"- size {_code(f'{request.proposal.size:.6f}')} lev {_code(request.proposal.leverage)}",
            f"- confidence {_code(f'{request.signal.confidence:.2f}')}",
            f"- reason {_code(decision_summary)}",
            f"- expires/status {_code(status_line)}",
        ]
    )
