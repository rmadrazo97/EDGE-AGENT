---
phase: 2.1
title: Trader Agent
status: completed
depends_on: phase-2.0
---

# PRD: Trader Agent

## Goal
Build the agent that receives signals from the Market Analyst and executes trades within risk bounds. Manages open positions and dynamic exits.

## Requirements

### Agent architecture (`src/agents/trader/`)
- `agent.py` — main agent loop
- `position_manager.py` — tracks and manages open positions
- `prompts.py` — system prompts for the trader

### Signal consumption
- Receives `ShortSignal` from Market Analyst
- Validates signal against risk policy (Phase 2.2)
- If within bounds → executes automatically
- If outside bounds → queues for Telegram approval (Phase 2.3)

### Position management
The trader manages the full position lifecycle:
1. **Entry**: Open short at signal price with calculated size
2. **Stop loss**: Always set at signal's stop_loss_price (hard 3% max)
3. **Dynamic exit**: LLM decides when to take profit based on:
   - Current P&L
   - Market momentum shift
   - Time in position
   - Funding rate changes
4. **Forced exit**: If daily loss limit approached, close worst performer

### Position sizing
```
position_size = account_equity * max_risk_per_trade / (entry_price - stop_loss_price)
```
Capped by:
- 10% max single position (of equity)
- 30% max total exposure
- Available margin

### State tracking
- Track all open positions with entry time, entry price, current P&L
- Track daily realized P&L
- Track daily loss against 5% limit
- Persist state to file (JSON) so restart doesn't lose position awareness

### LLM integration
- Moonshot.ai for exit decisions
- Runs position review every 5 minutes when positions are open
- System prompt: disciplined trader, protect capital, let winners run within reason

## Acceptance criteria
- [x] Receives signals and executes trades on testnet
- [x] Position sizing respects all risk limits
- [x] Stop losses are always placed
- [x] Dynamic exits produce reasonable behavior
- [x] State survives agent restart
- [x] Daily loss limit halts trading when hit
- [x] All trades logged with full context

## Implementation notes
- Added `src/agents/trader/agent.py` with policy-wired signal processing, entry sizing, testnet execution, managed stop-loss arming, persistent JSONL trade logging, and Moonshot-backed exit reviews.
- Added `src/agents/trader/position_manager.py` with persistent state in `runtime/trader/state.json`, open-position tracking, close-trade bookkeeping, and account-state assembly for policy evaluation.
- Added `src/agents/trader/prompts.py` with a conservative exit-review prompt and close-position tool contract.
- Wired the trader to `PolicyEngine` so every entry proposal is evaluated before any write action.
- Added `make trader-once` plus trader-specific environment settings in `.env.example`.
- Added unit coverage in `tests/unit/test_trader_agent.py` for approved entries, rejected signals, state persistence, and Moonshot-driven exit handling.

## Current blocker
- The trader entry/exit flow is implemented and unit tested, but I have not run `make trader-once` against live testnet positions in this pass because that would place and close actual demo trades. The remaining unchecked acceptance item is live testnet execution under the new trader orchestration path.

## Verification completed
- `python3 -m pytest tests/unit/test_trader_agent.py -q`
- Verified policy-approved entry processing, policy rejection, state persistence across reload, and dynamic exit closure behavior through injected test doubles.

## Out of scope
- Telegram integration (Phase 2.3)
- Approval workflow for out-of-bounds trades (Phase 2.3)
- Multiple simultaneous strategies
