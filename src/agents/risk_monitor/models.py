"""Typed models for risk monitoring alerts."""

from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, Field


class RiskAlert(BaseModel):
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    severity: str  # "info", "warning", "critical"
    alert_type: str
    pair: str | None = None
    message: str
    current_value: float
    threshold: float
