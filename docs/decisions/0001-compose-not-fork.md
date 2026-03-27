# ADR 0001: Composition Over Forking Hummingbot

## Status

Accepted

## Context

EDGE-AGENT depends on Hummingbot for exchange connectivity and order execution. We had two architectural options:

1. **Fork** the Hummingbot Gateway and Dashboard repositories, modify them in-tree, and maintain our own versions.
2. **Compose** around upstream Hummingbot Docker images, using their API as a black box and keeping all EDGE-AGENT logic in this separate repository.

## Decision

We chose the composition approach. EDGE-AGENT is a standalone repository that orchestrates upstream Hummingbot containers via `infra/compose/docker-compose.dev.yml` and communicates through the Hummingbot REST API.

## Rationale

- **Faster development.** No need to understand Hummingbot internals or maintain a fork. We treat Hummingbot as infrastructure.
- **Cleaner upgrades.** When Hummingbot releases a new version, we pull the new image rather than rebasing a fork.
- **Separation of concerns.** Trading logic, risk policy, and AI agents live in `src/`. Exchange plumbing lives in Hummingbot.
- **Fork only when blocked.** If we ever need to modify Hummingbot behavior that cannot be achieved through its API, we fork at that point -- not preemptively.

## Consequences

- We are limited to what the Hummingbot API exposes (e.g., no native stop-loss order types; we implement managed stop losses in `src/clients/trading.py`).
- Debugging exchange-level issues requires inspecting Hummingbot container logs rather than stepping through source code.
- Upstream breaking changes to the API could require adaptation in `src/clients/`.
