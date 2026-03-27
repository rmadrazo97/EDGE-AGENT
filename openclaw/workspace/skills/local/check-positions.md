# Skill: Check Positions

## Description

Read current trading state and open positions, then format a summary for the operator.

## When to use

- Operator asks "Show positions", "What's my status?", "Any open trades?"
- Part of daily summary generation

## Steps

1. Read trader state from `runtime/state/trader.json`
2. Query live positions via Hummingbot MCP `get_positions` endpoint
3. For each open position, include:
   - Pair and direction (long/short)
   - Entry price and current price
   - Position size (notional and as % of equity)
   - Unrealized P&L (absolute and percentage)
   - Stop loss price
   - Time in position
4. Include account summary:
   - Total equity
   - Available margin
   - Total exposure (% of equity)
   - Daily realized P&L
5. Format as a concise Telegram-friendly message

## Output format

```
Portfolio Status
Equity: $X,XXX.XX | Margin: $X,XXX.XX
Daily P&L: +$XX.XX (+X.XX%)
Exposure: XX% of equity

Open Positions:
BTC-USDT LONG | Entry: $XX,XXX | Size: $XXX (X%)
  P&L: +$XX.XX (+X.XX%) | Stop: $XX,XXX

No other open positions.
```

## Error handling

- If Hummingbot MCP is unreachable, report the error and show cached state from `trader.json`
- If no positions are open, say "No open positions"
