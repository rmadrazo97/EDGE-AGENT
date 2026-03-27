"""Unit coverage for the risk policy engine."""

from __future__ import annotations

import json
from pathlib import Path

from policy.engine import PolicyEngine
from policy.models import AccountState, TradeProposal
from policy.rules import (
    daily_loss_pct,
    position_notional,
    risk_cap_size,
    single_position_cap_size,
    stop_loss_distance_pct,
    total_exposure_cap_size,
    trade_risk_amount,
)


def write_policy_config(path: Path, *, trading_enabled: bool = True) -> None:
    path.write_text(
        "\n".join(
            [
                f"trading_enabled: {'true' if trading_enabled else 'false'}",
                "max_risk_per_trade_pct: 0.02",
                "max_daily_loss_pct: 0.05",
                "max_total_exposure_pct: 0.30",
                "max_single_position_pct: 0.10",
                "max_leverage: 3",
                "require_stop_loss: true",
                "max_stop_loss_pct: 0.03",
                "allowed_sides:",
                "  - long",
                "  - short",
                "allowed_pairs:",
                "  - BTC-USDT",
                "  - ETH-USDT",
            ]
        )
    )


def sample_proposal(**overrides: object) -> TradeProposal:
    payload = {
        "pair": "BTC-USDT",
        "side": "short",
        "size": 0.02,
        "leverage": 2.0,
        "entry_price": 50000.0,
        "stop_loss_price": 51000.0,
        "signal_confidence": 0.8,
        "reasoning": "test signal",
    }
    payload.update(overrides)
    return TradeProposal.model_validate(payload)


def sample_account_state(**overrides: object) -> AccountState:
    payload = {
        "total_equity": 10000.0,
        "available_margin": 5000.0,
        "daily_realized_pnl": 0.0,
        "current_total_exposure": 0.0,
        "open_pairs": [],
    }
    payload.update(overrides)
    return AccountState.model_validate(payload)


def test_rule_helpers_compute_expected_values(tmp_path: Path) -> None:
    config_path = tmp_path / "policy.yml"
    audit_path = tmp_path / "policy.jsonl"
    write_policy_config(config_path)
    engine = PolicyEngine(config_path=config_path, audit_log_path=audit_path)
    proposal = sample_proposal()
    state = sample_account_state()

    assert stop_loss_distance_pct(proposal) == 0.02
    assert position_notional(proposal) == 1000.0
    assert trade_risk_amount(proposal) == 20.0
    assert risk_cap_size(engine.config, proposal, state) == 0.2
    assert single_position_cap_size(engine.config, proposal, state) == 0.02
    assert total_exposure_cap_size(engine.config, proposal, state) == 0.06
    assert daily_loss_pct(engine.config, state) == 0.0


def test_policy_engine_approves_valid_trade(tmp_path: Path) -> None:
    config_path = tmp_path / "policy.yml"
    audit_path = tmp_path / "policy.jsonl"
    write_policy_config(config_path)
    engine = PolicyEngine(config_path=config_path, audit_log_path=audit_path)

    decision = engine.evaluate(sample_proposal(), sample_account_state())

    assert decision.approved is True
    assert decision.violations == []
    assert decision.adjusted_size is None


def test_policy_engine_rejects_when_kill_switch_is_disabled(tmp_path: Path) -> None:
    config_path = tmp_path / "policy.yml"
    audit_path = tmp_path / "policy.jsonl"
    write_policy_config(config_path, trading_enabled=False)
    engine = PolicyEngine(config_path=config_path, audit_log_path=audit_path)

    decision = engine.evaluate(sample_proposal(), sample_account_state())

    assert decision.approved is False
    assert "trading is disabled by policy kill switch" in decision.violations


def test_policy_engine_rejects_pair_leverage_stop_and_side_violations(tmp_path: Path) -> None:
    config_path = tmp_path / "policy.yml"
    audit_path = tmp_path / "policy.jsonl"
    write_policy_config(config_path)
    engine = PolicyEngine(config_path=config_path, audit_log_path=audit_path)

    decision = engine.evaluate(
        sample_proposal(
            pair="SOL-USDT",
            side="flat",
            leverage=5.0,
            stop_loss_price=None,
        ),
        sample_account_state(),
    )

    assert decision.approved is False
    assert "side flat is not allowed; allowed sides: long, short" in decision.violations
    assert "pair SOL-USDT is not allowed" in decision.violations
    assert "leverage 5.0 exceeds max leverage 3.0" in decision.violations
    assert "stop loss is required" in decision.violations


def test_policy_engine_rejects_stop_loss_distance_and_daily_loss_limit(tmp_path: Path) -> None:
    config_path = tmp_path / "policy.yml"
    audit_path = tmp_path / "policy.jsonl"
    write_policy_config(config_path)
    engine = PolicyEngine(config_path=config_path, audit_log_path=audit_path)

    decision = engine.evaluate(
        sample_proposal(stop_loss_price=52000.0),
        sample_account_state(daily_realized_pnl=-600.0),
    )

    assert decision.approved is False
    assert "stop loss distance 0.0400 exceeds max 0.0300" in decision.violations
    assert "daily loss limit exceeded: 0.0600 >= 0.0500" in decision.violations


def test_policy_engine_rejects_long_stop_loss_on_wrong_side(tmp_path: Path) -> None:
    config_path = tmp_path / "policy.yml"
    audit_path = tmp_path / "policy.jsonl"
    write_policy_config(config_path)
    engine = PolicyEngine(config_path=config_path, audit_log_path=audit_path)

    decision = engine.evaluate(
        sample_proposal(side="long", stop_loss_price=50500.0),
        sample_account_state(),
    )

    assert decision.approved is False
    assert "stop loss must be below entry price for long trades" in decision.violations


def test_policy_engine_adjusts_size_and_emits_warnings(tmp_path: Path) -> None:
    config_path = tmp_path / "policy.yml"
    audit_path = tmp_path / "policy.jsonl"
    write_policy_config(config_path)
    engine = PolicyEngine(config_path=config_path, audit_log_path=audit_path)

    decision = engine.evaluate(
        sample_proposal(size=0.05),
        sample_account_state(current_total_exposure=2500.0, daily_realized_pnl=-450.0),
    )

    assert decision.approved is True
    assert decision.adjusted_size == 0.01
    assert "position size reduced to comply with policy limits" in decision.warnings
    assert "daily loss is approaching the configured limit" in decision.warnings
    assert "total exposure is approaching the configured limit" in decision.warnings


def test_policy_engine_warns_when_single_position_exposure_is_high(tmp_path: Path) -> None:
    config_path = tmp_path / "policy.yml"
    audit_path = tmp_path / "policy.jsonl"
    write_policy_config(config_path)
    engine = PolicyEngine(config_path=config_path, audit_log_path=audit_path)

    decision = engine.evaluate(
        sample_proposal(size=0.018),
        sample_account_state(),
    )

    assert decision.approved is True
    assert "single-position exposure is approaching the configured limit" in decision.warnings


def test_policy_engine_rejects_when_no_total_exposure_capacity_remains(tmp_path: Path) -> None:
    config_path = tmp_path / "policy.yml"
    audit_path = tmp_path / "policy.jsonl"
    write_policy_config(config_path)
    engine = PolicyEngine(config_path=config_path, audit_log_path=audit_path)

    decision = engine.evaluate(
        sample_proposal(),
        sample_account_state(current_total_exposure=3000.0),
    )

    assert decision.approved is False
    assert "no exposure capacity remains for this trade" in decision.violations


def test_policy_engine_logs_config_reload_and_evaluations(tmp_path: Path) -> None:
    config_path = tmp_path / "policy.yml"
    audit_path = tmp_path / "policy.jsonl"
    write_policy_config(config_path)
    engine = PolicyEngine(config_path=config_path, audit_log_path=audit_path)

    engine.evaluate(sample_proposal(), sample_account_state())
    updated = config_path.read_text().replace("max_leverage: 3", "max_leverage: 2")
    config_path.write_text(updated)
    engine.evaluate(sample_proposal(leverage=2.5), sample_account_state())

    records = [json.loads(line) for line in audit_path.read_text().splitlines()]

    assert records[0]["event"] == "trade_evaluated"
    assert records[1]["event"] == "config_reloaded"
    assert records[2]["event"] == "trade_evaluated"
    assert records[2]["decision"]["approved"] is False
