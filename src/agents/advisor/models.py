"""Typed models for portfolio advisory outputs."""

from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, Field


class PortfolioAdvisory(BaseModel):
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    portfolio_health: str  # "healthy", "caution", "warning"
    recommendations: list[str]
    reasoning: str
    suggested_actions: list[str]  # specific actionable items
