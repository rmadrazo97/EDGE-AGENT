"""Persistent trader state and position bookkeeping."""

from __future__ import annotations

import json
from datetime import date, datetime, timezone
from pathlib import Path

from pydantic import BaseModel, Field

from agents.analyst.signals import ShortSignal
from policy.models import AccountState
from shared.models import Balance, OpenPosition


class ManagedPosition(BaseModel):
    pair: str
    size: float
    entry_price: float
    stop_loss_price: float
    leverage: float
    opened_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    order_id: str
    signal_confidence: float
    reasoning: str


class ClosedTrade(BaseModel):
    pair: str
    size: float
    entry_price: float
    exit_price: float
    leverage: float
    stop_loss_price: float
    opened_at: datetime
    closed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    reason: str
    realized_pnl: float


class TraderState(BaseModel):
    open_positions: dict[str, ManagedPosition] = Field(default_factory=dict)
    closed_trades: list[ClosedTrade] = Field(default_factory=list)


class PositionManager:
    def __init__(self, state_path: str | Path = "runtime/trader/state.json") -> None:
        self.state_path = Path(state_path)
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self.state = self._load_state()

    def _load_state(self) -> TraderState:
        if not self.state_path.exists():
            return TraderState()
        return TraderState.model_validate_json(self.state_path.read_text())

    def save(self) -> None:
        self.state_path.write_text(self.state.model_dump_json(indent=2), encoding="utf-8")

    def get_open_position(self, pair: str) -> ManagedPosition | None:
        return self.state.open_positions.get(pair)

    def record_open(
        self,
        *,
        signal: ShortSignal,
        size: float,
        leverage: float,
        order_id: str,
    ) -> ManagedPosition:
        position = ManagedPosition(
            pair=signal.pair,
            size=size,
            entry_price=signal.entry_price,
            stop_loss_price=signal.stop_loss_price,
            leverage=leverage,
            order_id=order_id,
            signal_confidence=signal.confidence,
            reasoning=signal.reasoning,
        )
        self.state.open_positions[signal.pair] = position
        self.save()
        return position

    def record_close(self, pair: str, *, exit_price: float, reason: str) -> ClosedTrade:
        position = self.state.open_positions.pop(pair)
        realized_pnl = (position.entry_price - exit_price) * position.size
        trade = ClosedTrade(
            pair=pair,
            size=position.size,
            entry_price=position.entry_price,
            exit_price=exit_price,
            leverage=position.leverage,
            stop_loss_price=position.stop_loss_price,
            opened_at=position.opened_at,
            reason=reason,
            realized_pnl=realized_pnl,
        )
        self.state.closed_trades.append(trade)
        self.save()
        return trade

    def sync_live_positions(self, live_positions: list[OpenPosition]) -> None:
        live_pairs = {position.trading_pair for position in live_positions}
        missing_pairs = [pair for pair in self.state.open_positions if pair not in live_pairs]
        for pair in missing_pairs:
            self.state.open_positions.pop(pair, None)
        if missing_pairs:
            self.save()

    def daily_realized_pnl(self, as_of: date | None = None) -> float:
        target_date = as_of or datetime.now(timezone.utc).date()
        return sum(
            trade.realized_pnl
            for trade in self.state.closed_trades
            if trade.closed_at.date() == target_date
        )

    def build_account_state(
        self,
        *,
        balances: list[Balance],
        live_positions: list[OpenPosition],
        current_prices: dict[str, float],
    ) -> AccountState:
        total_equity = sum(balance.value for balance in balances)
        available_margin = sum(balance.available_units * balance.price for balance in balances)
        current_total_exposure = sum(
            abs(position.amount) * current_prices.get(position.trading_pair, position.entry_price)
            for position in live_positions
        )
        return AccountState(
            total_equity=total_equity,
            available_margin=available_margin,
            daily_realized_pnl=self.daily_realized_pnl(),
            current_total_exposure=current_total_exposure,
            open_pairs=[position.trading_pair for position in live_positions],
        )
