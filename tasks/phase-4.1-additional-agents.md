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
