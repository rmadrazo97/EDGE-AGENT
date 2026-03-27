---
phase: 4.0
title: Altcoin Pair Expansion
status: pending
depends_on: phase-3.2
---

# PRD: Altcoin Pair Expansion

## Goal
Expand from BTC/ETH to altcoin perpetuals for higher volatility opportunities and better margin potential.

## Requirements

### Pair selection criteria
The analyst agent should evaluate altcoin pairs based on:
- 24h volume (minimum threshold to avoid illiquid pairs)
- Spread (maximum acceptable spread)
- Funding rate (higher = more favorable for shorts)
- Historical volatility (higher = more opportunity but more risk)
- Correlation with BTC (lower correlation = better diversification)

### New agent capability: Opportunity Seeker
Either extend the Market Analyst or create a lightweight scanner that:
- Periodically scans top 20-30 altcoin perps on Binance
- Ranks by short opportunity score
- Suggests pairs to add to the active watchlist
- Analyst then does deep analysis on suggested pairs

### Risk adjustments for altcoins
- Altcoin positions: max 5% single position (half of BTC/ETH limit)
- Total altcoin exposure: max 15% of equity
- Wider stop loss allowed: up to 5% (altcoins are more volatile)
- Lower max leverage for altcoins: 2x

### Configuration
- `configs/risk/altcoins.yml` — altcoin-specific risk overrides
- Allowed pairs list updated dynamically based on scanner results
- Operator approval via Telegram to add new pair to active list

## Acceptance criteria
- [ ] Scanner identifies top altcoin opportunities
- [ ] Altcoin-specific risk rules enforced
- [ ] At least 3 altcoin pairs actively traded
- [ ] No altcoin position exceeds 5% of equity
- [ ] Operator approves new pairs via Telegram

## Out of scope
- DEX / on-chain pairs
- Spot trading
- Cross-exchange arbitrage
