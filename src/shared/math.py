"""Shared mathematical helpers used across agents."""

from __future__ import annotations

import math

from shared.models import Candle


def calculate_realized_volatility(candles: list[Candle]) -> float:
    """Return annualised-style realized volatility as a percentage.

    Computes the population standard deviation of simple returns then
    scales by 100 so the result reads as a percentage.
    """
    if len(candles) < 2:
        return 0.0

    returns: list[float] = []
    for previous, current in zip(candles, candles[1:]):
        if previous.close <= 0:
            continue
        returns.append((current.close - previous.close) / previous.close)

    if len(returns) < 2:
        return 0.0

    mean_return = sum(returns) / len(returns)
    variance = sum((value - mean_return) ** 2 for value in returns) / len(returns)
    return math.sqrt(variance) * 100
