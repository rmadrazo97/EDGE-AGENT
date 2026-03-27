---
phase: 2.5
title: Generalize from Short-Only to Day Trading
status: completed
depends_on: phase-2.3
---

# PRD: Generalize from Short-Only to Day Trading

## Goal
Remove the short-only constraint across the entire codebase. EDGE-AGENT becomes a generalist crypto day trading agent that can go long or short on Binance Futures perpetuals, with the AI deciding direction based on market conditions.

## Motivation
The original design locked the system to short-only. A generalist day trading agent that can take both sides of the market has:
- More opportunities (can profit in both directions)
- Better capital efficiency (not sitting idle during uptrends)
- More flexibility for the AI to express conviction in either direction

## Scope of changes

### Layer 1: Signal models (`src/agents/analyst/signals.py`)

**Current:** `ProposedShortSignal`, `ShortSignal` — hardcoded to short direction.

**Target:** `ProposedTradeSignal`, `TradeSignal` — direction-agnostic.

Changes:
- Rename `ProposedShortSignal` → `ProposedTradeSignal`
- Rename `ShortSignal` → `TradeSignal`
- Add `side: str` field (value: `"long"` or `"short"`)
- Update stop-loss validator:
  - Short: stop must be ABOVE entry (current behavior)
  - Long: stop must be BELOW entry
- Keep 3% max stop-loss distance for both directions

### Layer 2: Analyst agent (`src/agents/analyst/`)

**`agent.py`:**
- Rename tool from `emit_short_signal` → `emit_trade_signal`
- Add `"side"` field to tool schema: `{"type": "string", "enum": ["long", "short"]}`
- Update `_filter_signal` to handle both directions
- Update type annotations from `ShortSignal` → `TradeSignal`

**`prompts.py`:**
- Remove short-bias language from system prompt
- New prompt: "conservative day trader looking for high-conviction setups in either direction"
- Add guidance for both directions:
  - Long signals: strong bid support, positive momentum, oversold conditions
  - Short signals: heavy selling pressure, negative momentum, overbought conditions
  - Funding rate interpretation: positive rate favors shorts, negative favors longs
- Update user prompt builder to not bias toward shorts

### Layer 3: Trading client (`src/clients/trading.py`)

**Current:** `open_short()` only.

**Target:** Add `open_long()` and generalize.

Changes:
- Add `open_long(pair, size, leverage)` → submits BUY with position_action OPEN
- Rename `open_short` internals to be clear about direction
- `close_position` already handles both directions (checks `is_short` flag) — no change needed
- `set_stop_loss` → update to accept direction parameter:
  - Short: trigger when price goes ABOVE stop (current)
  - Long: trigger when price goes BELOW stop

### Layer 4: Policy engine (`src/policy/`)

**`engine.py`:**
- Remove: `if proposal.side.lower() != "short": violations.append("only short trades are allowed")`
- Replace with: validate `proposal.side` is one of `["long", "short"]`
- Stop-loss validation needs direction awareness:
  - Short: stop_loss_price > entry_price
  - Long: stop_loss_price < entry_price

**`models.py`:**
- `TradeProposal.side` — document allowed values: `"long"`, `"short"`
- No structural changes needed

**`policy.yml`:**
- Remove any implicit short-only assumption
- Add: `allowed_sides: ["long", "short"]` (configurable, so you can still restrict to short-only if desired)

### Layer 5: Trader agent (`src/agents/trader/`)

**`agent.py`:**
- `_build_trade_proposal` → handle both directions:
  - Short: stop above entry (current)
  - Long: stop below entry, risk = entry - stop_loss
- `process_signal` → call `open_long()` or `open_short()` based on signal side
- Update type annotations from `ShortSignal` → `TradeSignal`
- Update close tool description from "Close an existing short position" → "Close an existing position"

**`position_manager.py`:**
- `ManagedPosition` → add `side: str` field
- `record_close` → P&L calculation based on direction:
  - Short: `(entry - exit) * size` (current)
  - Long: `(exit - entry) * size`
- Update type annotations from `ShortSignal` → `TradeSignal`

**`prompts.py`:**
- Remove "short positions" language
- Generalize to: "manage already-open positions conservatively"
- Exit review should work for both long and short

### Layer 6: Reporter / Notifier (`src/agents/reporter/`)

- Update type imports from `ShortSignal` → `TradeSignal`
- Formatters: include direction in trade alert messages ("Opened LONG BTC-USDT" vs "Opened SHORT BTC-USDT")
- Approval messages: show direction clearly

### Layer 7: Test short controller (`src/strategies/controllers/test_short.py`)

- Keep as-is for short pipeline validation
- Add `test_long.py` — same pattern but opens a long position
- Or: generalize into `test_trade.py` that accepts `--side long|short`

### Layer 8: Tests

Files to update:
- `tests/unit/test_market_analyst.py` — update model names, add long signal test
- `tests/unit/test_trading_client.py` — add `open_long` test, update model names
- `tests/unit/test_policy_engine.py` — remove short-only violation test, add side validation test, add long stop-loss test
- `tests/unit/test_trader_agent.py` — update model names, add long signal processing test
- `tests/unit/test_notifier.py` — update model names
- `tests/unit/test_approval_store.py` — update model names

### Layer 9: Documentation

- `AGENTS.md` — remove "crypto shorting system", update to "crypto day trading system"
- `README.md` — same
- `tasks/` PRDs — update references in future phases
- `configs/risk/policy.yml` — add `allowed_sides`

## What does NOT change
- Risk limits (2% per trade, 5% daily, 30% exposure, etc.) — apply equally to longs and shorts
- Infrastructure (Hummingbot API, Docker, etc.)
- OpenClaw workspace structure
- Telegram notification flow
- Audit logging
- Position sizing logic (just needs direction-aware stop distance)
- Market data collection

## Migration approach

This is a refactor, not a feature addition. Do it in one pass:

1. **Rename models** — `ShortSignal` → `TradeSignal`, `ProposedShortSignal` → `ProposedTradeSignal`
2. **Add `side` field** to signal, position, and tool schema
3. **Update validators** for direction-aware stop-loss
4. **Update policy** to allow both sides (or configurable)
5. **Add `open_long`** to trading client
6. **Update prompts** to be direction-neutral
7. **Update all imports and type annotations** across the codebase
8. **Update tests** — fix model names, add long-direction tests
9. **Update docs** — AGENTS.md, README.md

## Acceptance criteria
- [ ] Analyst can emit both long and short signals
- [ ] Trader executes both long and short trades on testnet
- [ ] Policy validates both directions correctly
- [ ] Stop-loss logic is direction-aware (above entry for short, below for long)
- [ ] P&L calculation is direction-aware
- [ ] `allowed_sides` config allows restricting to one direction if desired
- [ ] All existing tests updated and passing
- [ ] New tests for long direction added
- [ ] No "short-only" language remaining in code or prompts (except test_short.py legacy)
- [ ] `make test-trade` still works for short pipeline validation

## Risk
- LLM prompt changes may affect signal quality. Monitor first few cycles after deployment.
- The analyst may initially favor one direction over another based on prompt wording. Tune if needed.

## Out of scope
- Spot trading (futures perps only, for now)
- Hedging (simultaneous long + short on same pair)
- Multi-strategy (one analyst, one trader — same as before)
