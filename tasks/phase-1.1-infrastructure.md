---
phase: 1.1
title: Docker Infrastructure
status: completed
depends_on: phase-1.0
---

# PRD: Docker Infrastructure

## Goal
Stand up Hummingbot API, PostgreSQL, EMQX, and Hummingbot MCP via Docker Compose so the execution layer is running locally.

## Requirements

### docker-compose.dev.yml
Services:
- **hummingbot-api**: FastAPI server, exposed on port 8000
- **postgres**: PostgreSQL for Hummingbot API state
- **emqx**: MQTT broker for bot communication
- **hummingbot-mcp**: MCP server connecting to Hummingbot API

### Environment files
- `infra/env/api.env.example` — Hummingbot API config (DB URL, EMQX host, credentials)
- `infra/env/mcp.env.example` — MCP server config (API URL, auth)

### Makefile targets
- `make up` — starts all services
- `make down` — stops all services
- `make logs` — tails logs from all services
- `make smoke` — runs smoke test (Phase 1.2)

### Health verification
- Hummingbot API responds on `/health`
- Hummingbot API docs available on `/docs`
- PostgreSQL accepts connections
- EMQX dashboard accessible

## Acceptance criteria
- [x] `make up` brings all 4 services to healthy state
- [x] `curl localhost:8000/health` returns 200
- [x] `curl localhost:8000/docs` returns Swagger UI
- [x] `make down` cleanly stops everything
- [x] No secrets committed to git

## Implementation notes
- Added `infra/compose/docker-compose.dev.yml` with pinned PostgreSQL, EMQX, Hummingbot API, and Hummingbot MCP images.
- Added `infra/env/api.env.example` and `infra/env/mcp.env.example` for committed templates, while `make up` bootstraps ignored local `api.env` and `mcp.env` files with development defaults if they are missing.
- Wired `make up`, `make down`, `make logs`, and `make smoke` through dedicated scripts in `infra/scripts/`.
- Added `infra/compose/hummingbot_api_health.py` to expose `/health` on top of the upstream Hummingbot API app because the pinned upstream image does not currently provide that route.

## Verification
- `docker compose -f infra/compose/docker-compose.dev.yml config`
- `make up`
- `make smoke`
- `curl -i http://localhost:8000/health`
- `curl -i http://localhost:8000/docs`
- `curl -I http://localhost:18083`
- `make down`

## Notes
- Use official Hummingbot Docker images where available
- Pin image versions for reproducibility
- Gateway (DEX) is NOT needed yet — add later if altcoin DEX support is required

## Out of scope
- Production compose file
- Monitoring/observability stack
- Gateway service
