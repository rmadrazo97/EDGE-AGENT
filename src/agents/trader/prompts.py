"""Prompt templates for the trader agent."""

from __future__ import annotations

from agents.trader.position_manager import ManagedPosition
from shared.models import FundingRateInfo, MarketPrice, Ticker24h


TRADER_SYSTEM_PROMPT = """You are EDGE-AGENT's Trader.

Your job is to manage open positions actively for quick profits.
You are a day trader/scalper - take profits quickly, cut losses fast.

Rules:
- Take profits on any meaningful move in your favor (0.3-0.5% is good for scalping).
- Cut losses quickly if the market moves against you by 0.3-0.5%.
- Don't get greedy. Small wins compound.
- Don't hope for recoveries. If the setup is invalidated, close immediately.
- Time decay works against you in futures. Be quick.
- If momentum stalls, take the profit and move on.
- If the market shifts against the position, close immediately - no exceptions.
"""


def build_trader_review_prompt(
    position: ManagedPosition,
    *,
    price: MarketPrice,
    ticker: Ticker24h,
    funding: FundingRateInfo,
) -> str:
    return (
        "Review this open position and decide whether it should be closed now.\n\n"
        "If the position should be exited immediately, call the tool with a concise reason.\n"
        "If not, return no tool call.\n\n"
        f"Position: {position.model_dump(mode='json')}\n"
        f"Current price: {price.price}\n"
        f"24h price change %: {ticker.price_change_percent}\n"
        f"Funding rate: {funding.funding_rate}\n"
        f"Mark price: {funding.mark_price}\n"
        f"Index price: {funding.index_price}\n"
    )
