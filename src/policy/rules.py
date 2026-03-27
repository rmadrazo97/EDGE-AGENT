"""Pure rule helpers for the EDGE-AGENT risk policy engine."""

from __future__ import annotations

from policy.models import AccountState, RiskPolicyConfig, TradeProposal


def stop_loss_distance_pct(proposal: TradeProposal) -> float | None:
    if proposal.stop_loss_price is None or proposal.entry_price <= 0:
        return None
    return abs(proposal.stop_loss_price - proposal.entry_price) / proposal.entry_price


def position_notional(proposal: TradeProposal, *, size: float | None = None) -> float:
    target_size = proposal.size if size is None else size
    return target_size * proposal.entry_price


def trade_risk_amount(proposal: TradeProposal, *, size: float | None = None) -> float | None:
    if proposal.stop_loss_price is None:
        return None
    target_size = proposal.size if size is None else size
    return abs(proposal.stop_loss_price - proposal.entry_price) * target_size


def risk_cap_size(config: RiskPolicyConfig, proposal: TradeProposal, state: AccountState) -> float | None:
    risk_amount = trade_risk_amount(proposal, size=1.0)
    if risk_amount is None or risk_amount <= 0 or state.total_equity <= 0:
        return None
    return (state.total_equity * config.max_risk_per_trade_pct) / risk_amount


def single_position_cap_size(config: RiskPolicyConfig, proposal: TradeProposal, state: AccountState) -> float | None:
    if proposal.entry_price <= 0 or state.total_equity <= 0:
        return None
    max_notional = state.total_equity * config.max_single_position_pct
    return max_notional / proposal.entry_price


def total_exposure_cap_size(config: RiskPolicyConfig, proposal: TradeProposal, state: AccountState) -> float | None:
    if proposal.entry_price <= 0 or state.total_equity <= 0:
        return None
    max_exposure = state.total_equity * config.max_total_exposure_pct
    remaining_exposure = max_exposure - state.current_total_exposure
    if remaining_exposure <= 0:
        return 0.0
    return remaining_exposure / proposal.entry_price


def daily_loss_pct(config: RiskPolicyConfig, state: AccountState) -> float:
    if state.total_equity <= 0:
        return 1.0
    realized_loss = abs(min(state.daily_realized_pnl, 0.0))
    return realized_loss / state.total_equity


def warning_threshold(limit: float) -> float:
    return limit * 0.8
