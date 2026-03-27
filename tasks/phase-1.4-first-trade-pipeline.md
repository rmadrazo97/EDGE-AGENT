---
phase: 1.4
title: First Trade Pipeline (Testnet)
status: pending
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
- [ ] Short position opens successfully on testnet
- [ ] Stop loss order is placed
- [ ] Position closes after timeout
- [ ] P&L is calculated and logged correctly
- [ ] Trading client methods return typed Pydantic models
- [ ] Full trade lifecycle logged with timestamps

## Risk controls (even on testnet)
- Hardcoded to testnet only — refuses to run if real credentials detected
- Maximum position size capped in test controller

## Out of scope
- AI signal generation
- Risk policy layer (Phase 2.2)
- Multiple pairs
