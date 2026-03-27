"""Unit coverage for Telegram approval persistence."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from agents.analyst.signals import ShortSignal
from agents.reporter.approvals import ApprovalStore
from policy.models import PolicyDecision, TradeProposal


def sample_signal() -> ShortSignal:
    return ShortSignal(
        pair="BTC-USDT",
        confidence=0.82,
        entry_price=65000.0,
        stop_loss_price=66500.0,
        reasoning="test signal",
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
        signal_confidence=0.82,
        reasoning="test signal",
    )


def sample_decision() -> PolicyDecision:
    return PolicyDecision(
        approved=True,
        warnings=["position size reduced to comply with policy limits"],
        adjusted_size=0.0015,
    )


def test_approval_store_persists_round_trip(tmp_path: Path) -> None:
    store_path = tmp_path / "approvals.json"
    store = ApprovalStore(path=store_path)

    created = store.create(sample_signal(), sample_proposal(), sample_decision())
    store.approve(created.request_id, note="approved")
    store.set_size_override(created.request_id, 0.001)
    store.mark_executed(created.request_id)

    restored = ApprovalStore(path=store_path)
    request = restored.get(created.request_id)

    assert request is not None
    assert request.status == "approved"
    assert request.size_override == 0.001
    assert request.executed is True


def test_approval_store_expires_pending_requests(tmp_path: Path) -> None:
    store = ApprovalStore(path=tmp_path / "approvals.json")
    created = store.create(sample_signal(), sample_proposal(), sample_decision())
    store.data.requests[created.request_id].expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
    store.save()

    expired = store.expire_pending()

    assert [request.request_id for request in expired] == [created.request_id]
    assert store.get(created.request_id).status == "expired"
