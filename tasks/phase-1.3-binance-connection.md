---
phase: 1.3
title: Binance Testnet Connection
status: pending
depends_on: phase-1.2
---

# PRD: Binance Testnet Connection

## Goal
Connect Hummingbot API to Binance Futures testnet and verify we can read market data and account state. No real money at this stage.

## Requirements

### Exchange account setup
- Configure Binance Futures testnet credentials via Hummingbot API accounts endpoint
- Store credentials only in `.env` files (gitignored)

### Verify via API
- List connected accounts → Binance testnet appears
- Query portfolio/balances → returns testnet balance
- Query market data for BTC-USDT perp → returns price, volume, funding rate
- Query market data for ETH-USDT perp → returns price, volume, funding rate
- Query order book for BTC-USDT → returns bids/asks

### Client wrapper (`src/clients/market_data.py`)
Thin Python wrapper around the market data endpoints we'll actually use:
- `get_price(pair)` → current price
- `get_funding_rate(pair)` → current funding rate
- `get_order_book(pair, depth)` → order book snapshot
- `get_klines(pair, interval, limit)` → candlestick data
- `get_ticker_24h(pair)` → 24h volume, high, low, change

### Client wrapper (`src/clients/portfolio.py`)
- `get_balances()` → account balances
- `get_positions()` → open positions

## Acceptance criteria
- [ ] Binance testnet account connected through Hummingbot API
- [ ] Market data returns valid data for BTC-USDT and ETH-USDT
- [ ] Client wrappers return typed Pydantic models
- [ ] All clients have basic error handling (connection errors, API errors)
- [ ] No real exchange credentials in the codebase

## Out of scope
- Order placement (Phase 1.4)
- Real Binance account
- Altcoin pairs
