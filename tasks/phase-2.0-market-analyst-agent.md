---
phase: 2.0
title: Market Analyst Agent
status: completed
depends_on: phase-1.4
---

# PRD: Market Analyst Agent

## Goal
Build the first AI agent that analyzes Binance market data and generates short signals. This is the core value of the entire system.

## Requirements

### Agent architecture (`src/agents/analyst/`)
- `agent.py` — main agent loop
- `signals.py` — signal data model
- `prompts.py` — system prompts for the analyst

### Data inputs (from Phase 1.3 clients)
The analyst receives:
- Current price and 24h change
- Funding rate (positive = longs paying shorts → favorable for shorts)
- Order book imbalance (heavy bids vs asks)
- Recent candlestick data (1h, 4h candles)
- 24h volume and volatility

### Signal output model
```python
class ShortSignal:
    pair: str               # e.g., "BTC-USDT"
    confidence: float       # 0.0 to 1.0
    entry_price: float      # suggested entry
    stop_loss_price: float  # must be within 3% of entry
    reasoning: str          # why this signal
    data_snapshot: dict     # market data at signal time
    timestamp: datetime
```

### LLM integration
- Use Moonshot.ai API (model TBD with user)
- System prompt defines the analyst's role: conservative short-bias analyst
- Structured output via function calling to produce `ShortSignal`
- Agent runs on a loop: analyze every N minutes (configurable, default 15min)

### Signal filtering
Before passing to trader:
- Confidence must be above threshold (default 0.7)
- Must not conflict with existing open position on same pair
- Must pass basic sanity checks (stop loss within 3%, reasonable entry price)

### Logging
- Every analysis cycle logged (even when no signal produced)
- Signals logged with full data snapshot for later review

## Acceptance criteria
- [x] Agent connects to Moonshot.ai and produces structured output
- [x] Signals conform to ShortSignal model
- [x] Agent runs on configurable interval
- [x] Low-confidence signals are filtered out
- [x] All cycles and signals are logged to file
- [x] Agent handles API errors gracefully (retries, backoff)

## Implementation notes
- Added `src/agents/analyst/agent.py` with a configurable Moonshot-backed analysis loop, live market snapshot collection, retry/backoff handling, JSONL cycle logging, and deterministic signal filtering.
- Added `src/agents/analyst/signals.py` with typed `MarketSnapshot`, `ProposedShortSignal`, `ShortSignal`, and `AnalystCycleRecord` models.
- Added `src/agents/analyst/prompts.py` with a conservative short-bias analyst system prompt and structured market snapshot user prompt builder.
- Added `src/shared/moonshot.py` as a minimal Moonshot chat completions client using the official OpenAI-compatible `/v1/chat/completions` API and function/tool calling.
- Updated the Moonshot client to use `temperature=1.0`, which is required by the currently configured `kimi-k2.5` model.
- Extended `src/shared/config.py` and `.env.example` with analyst and Moonshot configuration settings, and added `make analyst-once` for a single-cycle run.
- Added unit coverage in `tests/unit/test_market_analyst.py` for accepted signals, low-confidence filtering, existing-position suppression, no-tool-call behavior, and retry handling.

## Verification completed
- `python3 -m pytest tests/unit/test_market_analyst.py tests/unit/test_api_clients.py tests/unit/test_trading_client.py tests/unit/test_package_layout.py tests/unit/test_config.py -q`
- `make up`
- `make smoke`
- `make analyst-once`
- `make analyst-once` successfully collected live BTC/ETH testnet market snapshots, completed live Moonshot API calls, and logged clean `no_signal` cycle records for both pairs in `runtime/analyst/*.jsonl`.

## Open questions
- What Moonshot.ai model specifically? (need to confirm with user)
- Initial analysis interval: 15min reasonable?
- Should the analyst also suggest exit signals for open positions, or is that the trader's job?

## Out of scope
- Trade execution (Phase 2.1)
- Historical backtesting of signals
- Sentiment analysis / news feeds (Phase 4+)
- Altcoin pairs (Phase 3+)
