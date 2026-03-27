---
phase: 3.0
title: Go Live (Real Binance)
status: pending
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
