---
phase: 1.3
title: Binance Testnet Connection
status: completed
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
- [x] Binance testnet account connected through Hummingbot API
- [x] Market data returns valid data for BTC-USDT and ETH-USDT
- [x] Client wrappers return typed Pydantic models
- [x] All clients have basic error handling (connection errors, API errors)
- [x] No real exchange credentials in the codebase

## Implementation notes
- Added typed client configuration and response models in `src/shared/config.py` and `src/shared/models.py`.
- Added a reusable authenticated API base client with connection and API error handling in `src/clients/base.py`.
- Added `src/clients/accounts.py` to create the Hummingbot account if needed and register `binance_perpetual_testnet` credentials from local environment variables only.
- Added `src/clients/market_data.py` with typed wrappers for price, funding rate, order book, candles, and a derived 24h ticker summary built from candle data because the live Hummingbot API does not expose a dedicated 24h ticker endpoint.
- Added `src/clients/portfolio.py` with typed balance and position helpers against `/portfolio/state` and `/trading/positions`.
- Fixed the Hummingbot runtime credential path so connector credentials persist under `runtime/hummingbot-api/bots/credentials/`, which matches the upstream API file-system helper.

## Verification
- `python3 -m pytest tests/unit/test_api_clients.py tests/unit/test_package_layout.py`
- `python3 -m pytest tests/integration/test_api_connectivity.py tests/unit/test_api_clients.py -q`
- Connected `binance_perpetual_testnet` to `master_account` through Hummingbot API using local `.env` credentials
- Verified `/accounts/master_account/credentials` includes `binance_perpetual_testnet`
- Verified balances on `master_account/binance_perpetual_testnet` returned BTC, USDT, and USDC testnet balances
- Verified market data responses for BTC-USDT and ETH-USDT prices and funding info
- Verified BTC-USDT order book and candle data through the typed client wrappers

## Out of scope
- Order placement (Phase 1.4)
- Real Binance account
- Altcoin pairs
