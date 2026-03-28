---
phase: 4.0
title: Altcoin Pair Expansion
status: completed
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
- [x] Scanner identifies top altcoin opportunities
- [x] Altcoin-specific risk rules enforced
- [x] Altcoin risk config created (`configs/risk/altcoins.yml`)
- [ ] At least 3 altcoin pairs actively traded
- [ ] No altcoin position exceeds 5% of equity
- [ ] Operator approves new pairs via Telegram

## Out of scope
- DEX / on-chain pairs
- Spot trading
- Cross-exchange arbitrage

## Implementation notes (Phase 4.0 scanner)

### Files created
- `src/agents/scanner/__init__.py` — package marker
- `src/agents/scanner/models.py` — `PairOpportunity` and `AltcoinRiskConfig` Pydantic models
- `src/agents/scanner/agent.py` — `AltcoinScannerAgent` with CLI (`python3 -m agents.scanner.agent --top N`)
- `configs/risk/altcoins.yml` — altcoin-specific risk overrides (position size, exposure, leverage, volume floor)
- `tests/unit/test_scanner.py` — unit tests covering scoring, volume filter, ranking order, error handling

### Design decisions
- **Read-only scanner**: the agent suggests pairs but never modifies `allowed_pairs`. Adding a pair still requires operator action (manual or via OpenClaw/Telegram).
- **Weighted-sum scoring**: composite of volume (0.25), funding rate extremity (0.25), volatility (0.30), and spread tightness (0.20). No ML — intentionally simple and transparent.
- **Injectable dependencies**: `MarketDataProvider` protocol allows test stubs; `AltcoinRiskConfig` is loaded from YAML but can be overridden in constructor.
- **Graceful error handling**: per-pair API failures are logged and skipped; the scan continues with remaining pairs.
- **25 default candidate pairs**: top Binance perpetuals by market cap; BTC-USDT and ETH-USDT are always excluded.
- **Makefile target**: `make scan-altcoins` runs the scanner with `--top 10`.
