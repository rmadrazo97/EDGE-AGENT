---
phase: 1.2
title: Smoke Test Suite
status: completed
depends_on: phase-1.1
---

# PRD: Smoke Test Suite

## Goal
Verify the infrastructure is running and the basic API contract works before building anything on top of it.

## Requirements

### Smoke test script (`infra/scripts/smoke.sh`)
Checks:
1. Hummingbot API `/health` returns 200
2. Hummingbot API `/docs` returns 200
3. Can list accounts (empty is fine)
4. Can query market data endpoint (even if no exchange connected yet)
5. MCP server is reachable

### Integration test (`tests/integration/test_api_connectivity.py`)
- Uses httpx to hit Hummingbot API
- Verifies response schemas match expected structure
- Skipped if services aren't running (pytest marker)

## Acceptance criteria
- [x] `make smoke` runs all checks and reports pass/fail
- [x] Smoke test exits non-zero on any failure
- [x] Integration test passes when services are up
- [x] Integration test is skipped gracefully when services are down

## Implementation notes
- Extended `infra/scripts/smoke.sh` to verify API health, docs, the accounts endpoint, live market-data pricing on `binance_perpetual_testnet`, PostgreSQL readiness, and Hummingbot MCP health.
- Added `tests/integration/test_api_connectivity.py` using `httpx` to validate the accounts and market-data endpoints.
- The integration test skips gracefully when the local infrastructure is not running, using the live `/health` probe as the gate.

## Verification
- `make up`
- `make smoke`
- `python3 -m pytest tests/integration/test_api_connectivity.py`
- `make down`
- `python3 -m pytest tests/integration/test_api_connectivity.py -q`

## Out of scope
- Exchange connectivity tests (Phase 1.3)
- Strategy tests
