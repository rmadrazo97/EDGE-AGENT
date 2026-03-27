# ADR 0003: Direction-Agnostic Day Trading

## Status

Accepted

## Context

EDGE-AGENT originally operated as a short-only system. The market analyst would identify overextended price action and the trader agent would open short positions with defined stop losses.

This approach limited the system to bearish setups only, leaving profitable long opportunities on the table and making the system idle during sustained uptrends.

## Decision

Generalize to direction-agnostic day trading. The system supports both long and short positions, controlled by the `allowed_sides` field in `configs/risk/policy.yml`.

## Rationale

- **More opportunities.** The analyst can flag setups in either direction rather than waiting exclusively for short entries.
- **Better capital efficiency.** The system can stay active in trending markets regardless of direction.
- **Configurable.** An operator can restrict to long-only or short-only at any time by editing `allowed_sides` in the policy file. The `PolicyEngine` enforces this on every trade proposal.
- **Same risk controls.** All existing policy limits (exposure caps, stop-loss requirements, daily loss limits) apply identically to both directions.

## Consequences

- The market analyst prompt and scoring logic were updated to evaluate both long and short setups (see Phase 2.5 task: `tasks/phase-2.5-generalize-to-day-trading.md`).
- The trader agent must handle position direction when setting stop losses and closing positions.
- Simultaneous long and short positions on the same pair are possible in hedge mode, which increases complexity.
