---
phase: 4.1
title: Additional Agents
status: pending
depends_on: phase-3.2
---

# PRD: Additional Agents

## Goal
Expand the agent team from 3 to 5-6 as justified by operational needs and proven profitability.

## Requirements

### Agent: Advisor
**Role:** Strategic advisor that reviews overall portfolio and suggests adjustments.

Responsibilities:
- Weekly portfolio review: concentration, correlation, sector exposure
- Suggest rebalancing when too concentrated
- Flag macro events that might affect short bias (e.g., major crypto events, regulatory news)
- Suggest when to increase/decrease overall exposure
- Input: portfolio state, recent signals, market conditions, news (if available)
- Output: advisory recommendations to operator via Telegram/OpenClaw

### Agent: Risk Monitor
**Role:** Continuous risk surveillance independent of the trader.

Responsibilities:
- Real-time monitoring of all open positions
- Alert on approaching risk limits (80% of any limit)
- Alert on unusual market conditions (extreme volatility, liquidity drops)
- Alert on funding rate flips (negative funding = shorts paying longs)
- Can trigger emergency position reduction if multiple risk signals converge
- Independent from trader — acts as a check on the trader's judgment

### Agent: Opportunity Seeker (if not built in 4.0)
**Role:** Scans broader market for new opportunities.

Responsibilities:
- Monitor pairs not in active watchlist
- Track funding rate anomalies across all Binance perps
- Identify regime changes (trending → ranging, low vol → high vol)
- Suggest new pairs, strategy adjustments, or timing changes

### Agent coordination
- All agents share state through a common state store
- No agent can override another's decisions
- Conflicts escalated to operator via Telegram
- Clear hierarchy: Risk Monitor can halt trading, others can only suggest

## Acceptance criteria
- [ ] Each new agent runs independently
- [ ] Advisor produces weekly review
- [ ] Risk Monitor alerts are timely and actionable
- [ ] Agent-to-agent communication works without conflicts
- [ ] LLM costs tracked per agent (justify each agent's cost vs value)

## Out of scope
- Fully autonomous multi-agent negotiation
- Agent self-modification
- Custom agent training/fine-tuning

## Implementation Notes (Phase 4.1)

### Advisor Agent (`src/agents/advisor/`)
- `PortfolioAdvisorAgent` runs weekly (configurable via `EDGE_AGENT_ADVISOR_INTERVAL_DAYS`, default 7)
- Uses Moonshot.ai with `emit_advisory` function calling tool to produce structured `PortfolioAdvisory` output
- Collects: open positions, recent 7-day closed trades, risk usage (exposure/daily loss vs limits), market conditions for active pairs
- Logs all advisory cycles to `runtime/advisor/*.jsonl`
- Sends advisory summary to Telegram via `TelegramNotifier.send_advisory()`
- System prompt emphasizes conservative bias: when in doubt, suggest reducing exposure

### Risk Monitor Agent (`src/agents/risk_monitor/`)
- `RiskMonitorAgent` runs on a fast loop (configurable via `EDGE_AGENT_RISK_MONITOR_INTERVAL_SECONDS`, default 120)
- Pure rule-based checks, no LLM calls, for speed and reliability
- Alert types implemented:
  - `stop_proximity`: position unrealized loss >= 80% of stop-loss distance
  - `exposure_limit`: total exposure >= 80% of max exposure limit
  - `daily_loss_limit`: daily loss >= 80% of max daily loss limit
  - `adverse_funding`: funding rate adverse for position direction (above 0.01% threshold)
  - `unusual_volatility`: current volatility > 2x baseline (exponential moving average)
- Emergency convergence detection: alerts operator when 2+ critical signals fire simultaneously
- Logs all checks to `runtime/risk-monitor/*.jsonl`
- Sends alerts via `TelegramNotifier.send_risk_alert()`

### Config additions in `ClientSettings`
- `advisor_interval_days` (env: `EDGE_AGENT_ADVISOR_INTERVAL_DAYS`, default 7)
- `risk_monitor_interval_seconds` (env: `EDGE_AGENT_RISK_MONITOR_INTERVAL_SECONDS`, default 120)

### Makefile targets
- `make advisor-once` -- single advisory cycle
- `make risk-monitor` -- continuous risk monitoring loop

### Tests
- `tests/unit/test_advisor.py` -- 7 tests covering advisory generation, no-tool-call handling, caution health, formatting, and summarization helpers
- `tests/unit/test_risk_monitor.py` -- 17 tests covering all alert threshold checks (stop proximity, exposure, daily loss, funding rate, volatility), run_once integration, and formatting
