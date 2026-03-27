---
phase: 3.0
title: Go Live (Real Binance)
status: prepared
depends_on: phase-2.4
---

# PRD: Go Live on Real Binance

## Goal
Switch from testnet to real Binance Futures with tiny positions. Validate everything works with real money before scaling up.

## Requirements

### Credential switch
- Configure real Binance Futures API credentials
- Credentials stored in `.env` only, never in code
- Verify connection via portfolio/balances endpoint

### Conservative start parameters
Override defaults for initial live period:
- Max risk per trade: **1%** (halved from default)
- Max total exposure: **15%** (halved from default)
- Max single position: **5%** (halved from default)
- Allowed pairs: BTC-USDT only (ETH-USDT added after 1 week)
- Analysis interval: 30 minutes (slowed from 15)

### Go-live checklist
- [ ] Real credentials configured and tested
- [ ] Conservative risk parameters loaded
- [ ] Telegram bot connected and responding
- [ ] Kill switch tested (open tiny position, use `/kill`)
- [ ] Manual trade via API confirmed working
- [ ] Audit logging active
- [ ] Operator has verified: I'm ready to risk real money

### First week protocol
- Monitor every trade via Telegram
- Review daily reports manually
- Keep `/pause` ready
- After 1 week: review all trades, evaluate signal quality
- Decision point: continue / adjust parameters / pause and rethink

## Acceptance criteria
- [ ] First real trade executes correctly
- [ ] Stop loss fires on real exchange
- [ ] P&L tracking matches Binance account
- [ ] No unexpected behavior vs testnet
- [ ] Audit log captures every action

## Out of scope
- Full risk parameter restoration (do that after 1 week of clean operation)
- Altcoin pairs
- VPS migration

---

## Implementation Notes

Prepared on 2026-03-27. The following artifacts were created:

### Configuration
- **`configs/risk/policy-live-conservative.yml`** -- Conservative risk policy with halved limits (1% per-trade risk, 15% max exposure, 5% max single position, 2x leverage, BTC-USDT only). Copy this to `configs/risk/policy.yml` at go-live time.

### Runbooks
- **`docs/runbooks/go-live.md`** -- Full go-live checklist: credential setup, testnet guard removal (`_ensure_testnet_only` and `max_test_position_size` in `src/clients/trading.py`), risk parameter switch, pre-flight verification, first-week monitoring protocol, and parameter relaxation decision points.
- **`docs/runbooks/disable-trading.md`** -- Four methods to halt trading (Telegram `/kill`, edit policy YAML, close via API, close on Binance directly), plus verification and resume procedures.
- **`docs/runbooks/rollback.md`** -- Step-by-step revert from live to testnet: stop agents, close positions, restore `.env` credentials, restore default `policy.yml`, restore testnet guards, verify connectivity.

### Architecture Decision Records
- **`docs/decisions/0001-compose-not-fork.md`** -- Why we compose around upstream Hummingbot images rather than forking.
- **`docs/decisions/0002-risk-gateway.md`** -- Why a deterministic policy layer sits between AI agents and the trading API.
- **`docs/decisions/0003-generalist-day-trading.md`** -- Why we generalized from short-only to direction-agnostic day trading.

### Key finding: code changes required before go-live
The `TradingClient` in `src/clients/trading.py` has two testnet-only guards that must be addressed:
1. `_ensure_testnet_only()` (line 78) -- raises an error for non-testnet connectors
2. `max_test_position_size = Decimal("0.005")` (line 76) -- caps position size for testing

These are intentionally left in place until the operator is ready to execute the go-live runbook.
