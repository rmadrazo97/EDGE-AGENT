# ADR 0002: Policy Layer Between AI and Execution

## Status

Accepted

## Context

EDGE-AGENT uses LLM-based agents (market analyst, trader) to generate trade signals and execution decisions. These agents could, in principle, call the trading API directly.

Allowing an LLM to place orders without guardrails poses unacceptable risk: hallucinated confidence scores, outsized position requests, or trades on disallowed pairs could result in significant losses.

## Decision

A deterministic policy layer (`src/policy/engine.py`) sits between the AI agents and the `TradingClient`. Every trade proposal must pass through `PolicyEngine.evaluate()` before execution. The policy is configured via `configs/risk/policy.yml` and enforces hard limits on:

- Per-trade risk (`max_risk_per_trade_pct`)
- Daily loss (`max_daily_loss_pct`)
- Total exposure (`max_total_exposure_pct`)
- Single position size (`max_single_position_pct`)
- Leverage (`max_leverage`)
- Allowed trading pairs and sides
- Stop-loss requirements

## Rationale

- **LLM should never be the final authority on order placement.** The policy engine is deterministic code, not a probabilistic model.
- **Defense in depth.** Even if the LLM produces a bad signal, the policy layer caps downside exposure.
- **Hot-reloadable.** The policy YAML is checked on every evaluation cycle, so an operator can tighten parameters or kill trading without restarting agents.
- **Auditable.** Every evaluation is logged to `runtime/audit/policy.jsonl` with full context.

## Consequences

- The policy layer can reduce position sizes or reject trades entirely, which may cause the agents to miss opportunities.
- The operator must maintain `configs/risk/policy.yml` and understand its parameters.
- Adding new risk rules requires changes to `src/policy/rules.py` and `src/policy/engine.py`.
