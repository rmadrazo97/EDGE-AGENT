"""Persistent approval state and callback handling for Telegram reviews."""

from __future__ import annotations

import json
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable, Literal
from uuid import uuid4

from pydantic import BaseModel, Field
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from agents.analyst.signals import TradeSignal
from policy.models import PolicyAuditRecord, PolicyDecision, TradeProposal


ApprovalStatus = Literal["pending", "approved", "rejected", "timed_out"]


class ApprovalRequest(BaseModel):
    request_id: str = Field(default_factory=lambda: uuid4().hex)
    status: ApprovalStatus = "pending"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime
    signal: TradeSignal
    proposal: TradeProposal
    policy_decision: PolicyDecision
    telegram_message_id: int | None = None
    resolved_by_user_id: int | None = None
    review_note: str | None = None


class ApprovalResolution(BaseModel):
    request_id: str
    status: ApprovalStatus
    approved: bool


class ApprovalStoreData(BaseModel):
    requests: dict[str, ApprovalRequest] = Field(default_factory=dict)


class ApprovalStore:
    def __init__(
        self,
        path: str | Path = "runtime/reporter/approvals.json",
        *,
        audit_log_path: str | Path = "runtime/audit/policy.jsonl",
        sleep_fn: Callable[[float], None] = time.sleep,
    ) -> None:
        self.path = Path(path)
        self.audit_log_path = Path(audit_log_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.audit_log_path.parent.mkdir(parents=True, exist_ok=True)
        self.sleep_fn = sleep_fn
        self.data = self._load()

    def _load(self) -> ApprovalStoreData:
        if not self.path.exists():
            return ApprovalStoreData()
        return ApprovalStoreData.model_validate_json(self.path.read_text())

    def save(self) -> None:
        self.path.write_text(self.data.model_dump_json(indent=2), encoding="utf-8")

    def _append_audit(self, request: ApprovalRequest, *, event: str, message: str) -> None:
        record = PolicyAuditRecord(
            event=event,
            proposal=request.proposal,
            decision=request.policy_decision,
            message=message,
        )
        with self.audit_log_path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(record.model_dump(mode="json"), default=str) + "\n")

    def create(
        self,
        signal: TradeSignal,
        proposal: TradeProposal,
        decision: PolicyDecision,
        *,
        timeout_seconds: int,
    ) -> ApprovalRequest:
        request = ApprovalRequest(
            signal=signal,
            proposal=proposal,
            policy_decision=decision,
            expires_at=datetime.now(timezone.utc) + timedelta(seconds=timeout_seconds),
        )
        self.data.requests[request.request_id] = request
        self.save()
        self._append_audit(
            request,
            event="trade_approval_requested",
            message=f"Operator approval requested for {proposal.pair}; expires at {request.expires_at.isoformat()}",
        )
        return request

    def get(self, request_id: str) -> ApprovalRequest | None:
        request = self.data.requests.get(request_id)
        if request is None:
            return None
        if request.status == "pending" and request.expires_at <= datetime.now(timezone.utc):
            request.status = "timed_out"
            self.save()
            self._append_audit(
                request,
                event="trade_approval_timed_out",
                message=f"Approval request {request.request_id} timed out.",
            )
        return request

    def attach_message(self, request_id: str, message_id: int | None) -> ApprovalRequest:
        request = self.data.requests[request_id]
        request.telegram_message_id = message_id
        self.save()
        return request

    def pending(self) -> list[ApprovalRequest]:
        self.expire_pending()
        return [request for request in self.data.requests.values() if request.status == "pending"]

    def expire_pending(self) -> list[ApprovalRequest]:
        expired: list[ApprovalRequest] = []
        now = datetime.now(timezone.utc)
        for request in self.data.requests.values():
            if request.status == "pending" and request.expires_at <= now:
                request.status = "timed_out"
                expired.append(request)
                self._append_audit(
                    request,
                    event="trade_approval_timed_out",
                    message=f"Approval request {request.request_id} timed out.",
                )
        if expired:
            self.save()
        return expired

    def resolve(
        self,
        request_id: str,
        *,
        approved: bool,
        user_id: int,
        note: str | None = None,
    ) -> ApprovalRequest:
        request = self.get(request_id)
        if request is None:
            raise KeyError(request_id)
        if request.status != "pending":
            return request

        request.status = "approved" if approved else "rejected"
        request.resolved_by_user_id = user_id
        request.review_note = note
        self.save()
        self._append_audit(
            request,
            event="trade_approval_resolved",
            message=(
                f"Approval request {request.request_id} {request.status} by operator {user_id}."
            ),
        )
        return request

    def wait_for_resolution(
        self,
        request_id: str,
        *,
        poll_interval_seconds: float = 1.0,
    ) -> ApprovalResolution:
        while True:
            request = self.get(request_id)
            if request is None:
                raise KeyError(request_id)
            if request.status != "pending":
                return ApprovalResolution(
                    request_id=request.request_id,
                    status=request.status,
                    approved=request.status == "approved",
                )
            self.sleep_fn(poll_interval_seconds)

    @staticmethod
    def approval_markup(request_id: str) -> InlineKeyboardMarkup:
        return InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("Approve", callback_data=f"approval:approve:{request_id}"),
                    InlineKeyboardButton("Reject", callback_data=f"approval:reject:{request_id}"),
                ]
            ]
        )

    def handle_callback(
        self,
        callback_data: str,
        *,
        user_id: int | None,
        authorized_user_id: int | None,
    ) -> tuple[bool, str, ApprovalResolution | None]:
        if authorized_user_id is None or user_id != authorized_user_id:
            return False, "unauthorized", None

        try:
            prefix, action, request_id = callback_data.split(":", 2)
        except ValueError:
            return False, "invalid", None
        if prefix != "approval" or action not in {"approve", "reject"}:
            return False, "invalid", None

        request = self.get(request_id)
        if request is None:
            return False, "not_found", None
        if request.status != "pending":
            return False, request.status, ApprovalResolution(
                request_id=request.request_id,
                status=request.status,
                approved=request.status == "approved",
            )

        resolved = self.resolve(request_id, approved=action == "approve", user_id=user_id)
        resolution = ApprovalResolution(
            request_id=resolved.request_id,
            status=resolved.status,
            approved=resolved.status == "approved",
        )
        return True, resolved.status, resolution
