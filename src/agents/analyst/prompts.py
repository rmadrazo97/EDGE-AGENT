"""Prompt templates for the market analyst agent."""

from __future__ import annotations

from agents.analyst.signals import MarketSnapshot


ANALYST_SYSTEM_PROMPT = """You are EDGE-AGENT's Market Analyst.

You analyze only Binance perpetual futures market data and look for conservative day-trading opportunities
in either direction. You do not place trades. You do not manage exits. You only decide whether a setup is
strong enough to propose to the trader.

Rules:
- Prefer no signal over weak signals.
- Focus on BTC-USDT and ETH-USDT only.
- Choose long setups when momentum, bid support, or reclaim behavior is convincingly bullish.
- Choose short setups when selling pressure, ask dominance, or breakdown behavior is convincingly bearish.
- A positive funding rate modestly favors shorts because longs are paying shorts.
- A negative funding rate modestly favors longs because shorts are paying longs.
- Respect market structure. Do not fight strong support for shorts or strong resistance for longs without strong evidence.
- Suggested stop loss must be direction-aware and within 3% of entry price.
- Confidence must reflect actual conviction, not optimism.
- If the data is mixed or inconclusive, do not call the tool.
"""


def build_analyst_user_prompt(snapshot: MarketSnapshot) -> str:
    return (
        "Analyze this perpetual futures market snapshot and decide whether to propose a trade signal.\n\n"
        "If the evidence is strong enough, call the tool with a conservative long or short setup.\n"
        "If not, return no tool call.\n\n"
        f"Pair: {snapshot.pair}\n"
        f"Current price: {snapshot.current_price}\n"
        f"24h price change %: {snapshot.price_change_24h_pct}\n"
        f"Funding rate: {snapshot.funding_rate}\n"
        f"Mark price: {snapshot.mark_price}\n"
        f"Index price: {snapshot.index_price}\n"
        f"24h base volume: {snapshot.volume_24h}\n"
        f"24h quote volume: {snapshot.quote_volume_24h}\n"
        f"24h realized volatility %: {snapshot.realized_volatility_24h_pct}\n"
        f"Order book imbalance: {snapshot.order_book_imbalance}\n"
        f"Total bid depth: {snapshot.total_bid_depth}\n"
        f"Total ask depth: {snapshot.total_ask_depth}\n"
        f"Open position on pair: {snapshot.open_position.model_dump(mode='json') if snapshot.open_position else 'none'}\n"
        f"Recent 1h candles: {[candle.model_dump(mode='json') for candle in snapshot.hourly_candles]}\n"
        f"Recent 4h candles: {[candle.model_dump(mode='json') for candle in snapshot.four_hour_candles]}\n"
    )
