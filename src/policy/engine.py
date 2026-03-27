"""Reloadable risk policy engine with audit logging."""

from __future__ import annotations

import json
from pathlib import Path

import yaml

from policy.models import AccountState, PolicyAuditRecord, PolicyDecision, RiskPolicyConfig, TradeProposal
from policy.rules import (
    daily_loss_pct,
    position_notional,
    risk_cap_size,
    single_position_cap_size,
    stop_loss_distance_pct,
    total_exposure_cap_size,
    trade_risk_amount,
    warning_threshold,
)


class PolicyEngine:
    def __init__(
        self,
        config_path: str | Path = "configs/risk/policy.yml",
        audit_log_path: str | Path = "runtime/audit/policy.jsonl",
    ) -> None:
        self.config_path = Path(config_path)
        self.audit_log_path = Path(audit_log_path)
        self.audit_log_path.parent.mkdir(parents=True, exist_ok=True)
        self._config: RiskPolicyConfig | None = None
        self._config_mtime_ns: int | None = None

    @property
    def config(self) -> RiskPolicyConfig:
        return self._load_config_if_needed()

    def _read_config(self) -> RiskPolicyConfig:
        payload = yaml.safe_load(self.config_path.read_text()) or {}
        return RiskPolicyConfig.model_validate(payload)

    def _write_config(self, config: RiskPolicyConfig) -> None:
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        self.config_path.write_text(
            yaml.safe_dump(config.model_dump(), sort_keys=False),
            encoding="utf-8",
        )
        self._config = config
        self._config_mtime_ns = self.config_path.stat().st_mtime_ns

    def _append_audit(self, record: PolicyAuditRecord) -> None:
        with self.audit_log_path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(record.model_dump(mode="json"), default=str) + "\n")

    def _load_config_if_needed(self) -> RiskPolicyConfig:
        current_mtime_ns = self.config_path.stat().st_mtime_ns
        if self._config is not None and self._config_mtime_ns == current_mtime_ns:
            return self._config

        previous = self._config
        self._config = self._read_config()
        self._config_mtime_ns = current_mtime_ns

        if previous is not None and previous.model_dump() != self._config.model_dump():
            self._append_audit(
                PolicyAuditRecord(
                    event="config_reloaded",
                    config=self._config,
                    message="Risk policy configuration changed and was reloaded.",
                )
            )

        return self._config

    def update_config(self, **changes: object) -> RiskPolicyConfig:
        current = self._load_config_if_needed()
        updated = current.model_copy(update=changes)
        self._write_config(updated)
        self._append_audit(
            PolicyAuditRecord(
                event="config_updated",
                config=updated,
                message=f"Policy config updated with keys: {sorted(changes)}",
            )
        )
        return updated

    def evaluate(self, proposal: TradeProposal, account_state: AccountState) -> PolicyDecision:
        config = self._load_config_if_needed()
        violations: list[str] = []
        warnings: list[str] = []

        if proposal.side.lower() != "short":
            violations.append("only short trades are allowed")
        if not config.trading_enabled:
            violations.append("trading is disabled by policy kill switch")
        if proposal.pair not in config.allowed_pairs:
            violations.append(f"pair {proposal.pair} is not allowed")
        if proposal.leverage > config.max_leverage:
            violations.append(
                f"leverage {proposal.leverage} exceeds max leverage {config.max_leverage}"
            )
        if config.require_stop_loss and proposal.stop_loss_price is None:
            violations.append("stop loss is required")

        stop_distance = stop_loss_distance_pct(proposal)
        if stop_distance is not None and stop_distance > config.max_stop_loss_pct:
            violations.append(
                f"stop loss distance {stop_distance:.4f} exceeds max {config.max_stop_loss_pct:.4f}"
            )

        current_daily_loss = daily_loss_pct(config, account_state)
        if current_daily_loss >= config.max_daily_loss_pct:
            violations.append(
                f"daily loss limit exceeded: {current_daily_loss:.4f} >= {config.max_daily_loss_pct:.4f}"
            )
        elif current_daily_loss >= warning_threshold(config.max_daily_loss_pct):
            warnings.append("daily loss is approaching the configured limit")

        size_caps = [
            cap
            for cap in (
                risk_cap_size(config, proposal, account_state),
                single_position_cap_size(config, proposal, account_state),
                total_exposure_cap_size(config, proposal, account_state),
            )
            if cap is not None
        ]
        approved_size = min([proposal.size, *size_caps]) if size_caps else proposal.size

        if approved_size <= 0:
            violations.append("no exposure capacity remains for this trade")
        elif approved_size < proposal.size:
            warnings.append("position size reduced to comply with policy limits")

        adjusted_notional = position_notional(proposal, size=approved_size) if approved_size > 0 else 0.0
        max_single_notional = account_state.total_equity * config.max_single_position_pct
        max_total_exposure = account_state.total_equity * config.max_total_exposure_pct
        if adjusted_notional >= warning_threshold(max_single_notional):
            warnings.append("single-position exposure is approaching the configured limit")
        if account_state.current_total_exposure + adjusted_notional >= warning_threshold(max_total_exposure):
            warnings.append("total exposure is approaching the configured limit")

        adjusted_risk = trade_risk_amount(proposal, size=approved_size)
        max_risk_amount = account_state.total_equity * config.max_risk_per_trade_pct
        if adjusted_risk is not None and adjusted_risk >= warning_threshold(max_risk_amount):
            warnings.append("per-trade risk is approaching the configured limit")

        decision = PolicyDecision(
            approved=not violations,
            violations=violations,
            warnings=warnings,
            adjusted_size=approved_size if approved_size < proposal.size else None,
        )
        self._append_audit(
            PolicyAuditRecord(
                event="trade_evaluated",
                proposal=proposal,
                account_state=account_state,
                decision=decision,
                config=config,
            )
        )
        return decision
