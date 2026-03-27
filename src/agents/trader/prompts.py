"""Prompt templates for the trader agent."""

from __future__ import annotations

from agents.trader.position_manager import ManagedPosition
from shared.models import FundingRateInfo, MarketPrice, Ticker24h


TRADER_SYSTEM_PROMPT = """You are EDGE-AGENT's Trader.

Your job is to manage already-open short positions conservatively.
Protect capital first. If evidence is mixed, hold instead of closing.
If the market shifts strongly against the short, you may call the close tool.
Do not propose new entries here. Only decide whether an existing short should be closed now.
"""


def build_trader_review_prompt(
    position: ManagedPosition,
    *,
    price: MarketPrice,
    ticker: Ticker24h,
    funding: FundingRateInfo,
) -> str:
    return (
        "Review this open short position and decide whether it should be closed now.\n\n"
        "If the position should be exited immediately, call the tool with a concise reason.\n"
        "If not, return no tool call.\n\n"
        f"Position: {position.model_dump(mode='json')}\n"
        f"Current price: {price.price}\n"
        f"24h price change %: {ticker.price_change_percent}\n"
        f"Funding rate: {funding.funding_rate}\n"
        f"Mark price: {funding.mark_price}\n"
        f"Index price: {funding.index_price}\n"
    )
