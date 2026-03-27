---
phase: 1.4
title: First Trade Pipeline (Testnet)
status: completed
depends_on: phase-1.3
---

# PRD: First Trade Pipeline (Testnet)

## Goal
Prove the full trade lifecycle works end-to-end on Binance testnet: open a short position, monitor it, close it. Uses a hardcoded signal (not AI) to validate the plumbing.

## Requirements

### Trading client (`src/clients/trading.py`)
- `open_short(pair, size, leverage)` → opens short position
- `close_position(pair)` → closes position
- `set_stop_loss(pair, price)` → sets stop loss order
- `get_open_orders(pair)` → lists open orders
- `cancel_order(pair, order_id)` → cancels order

### Simple test controller (`src/strategies/controllers/test_short.py`)
A hardcoded controller that:
1. Opens a small short on BTC-USDT testnet
2. Sets a 3% stop loss
3. Waits 60 seconds
4. Closes the position
5. Logs entry price, exit price, P&L

This is NOT a real strategy — it's a pipeline validation tool.

### Makefile target
- `make test-trade` — runs the test controller on testnet

## Acceptance criteria
- [x] Short position opens successfully on testnet
- [x] Stop loss order is placed
- [x] Position closes after timeout
- [x] P&L is calculated and logged correctly
- [x] Trading client methods return typed Pydantic models
- [x] Full trade lifecycle logged with timestamps

## Implementation notes
- Added `src/clients/trading.py` with typed wrappers for opening shorts, closing positions, setting leverage, listing open orders, canceling orders, and arming a managed stop loss.
- Added `src/strategies/controllers/test_short.py` as a hardcoded pipeline validator that logs lifecycle events to `runtime/test-trade/*.jsonl`.
- Added `make test-trade` to run the controller locally on testnet only.
- Added package wiring for `src/strategies/` and unit coverage in `tests/unit/test_trading_client.py`.
- The current Hummingbot API only exposes `LIMIT`, `MARKET`, and `LIMIT_MAKER` order types, so `set_stop_loss()` is implemented as a managed local stop-loss trigger rather than a native exchange stop-order API call.
- Normalized Hummingbot to `ONEWAY` mode in the controller because the connector was reporting `HEDGE` while the Binance demo account was actually one-way, and order submission only succeeded after aligning the connector state.
- Added stale-position cleanup at controller startup so repeated `make test-trade` runs are deterministic after an interrupted test.
- Updated the shared position model to accept both `position_side` and `side`, because Hummingbot returns `side: "BOTH"` for one-way positions.

## Verification completed
- `python3 -m pytest tests/unit/test_trading_client.py tests/unit/test_api_clients.py tests/unit/test_package_layout.py`
- `python3 -m pytest tests/integration/test_api_connectivity.py -q`
- `make smoke`
- `make test-trade`
- Verified successful end-to-end lifecycle in `runtime/test-trade/20260327T135755Z.jsonl`: stale position cleanup, short open, managed stop-loss armed, timed close, and final P&L logged

## Risk controls (even on testnet)
- Hardcoded to testnet only — refuses to run if real credentials detected
- Maximum position size capped in test controller

## Out of scope
- AI signal generation
- Risk policy layer (Phase 2.2)
- Multiple pairs
