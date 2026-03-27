# EDGE-AGENT

EDGE-AGENT is a semi-autonomous crypto shorting system for Binance Futures perpetuals. The initial repository skeleton focuses on the minimum structure needed for Phase 1 and Phase 2 work: packaging, task organization, infrastructure placeholders, and strict secret hygiene for a public repository.

## Repository Layout

```text
EDGE-AGENT/
├── configs/
├── infra/
├── openclaw/
├── src/
│   ├── agents/
│   ├── clients/
│   ├── policy/
│   └── shared/
├── tasks/
└── tests/
```

## Quick Start

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e .
cp .env.example .env
make
```

Populate `.env` with your own credentials. Never commit real secrets, runtime state, or operator session data.

## Current Make Targets

- `make up`
- `make down`
- `make logs`
- `make smoke`
- `make test`

## Infrastructure Stack

Phase 1.1 wires a local Docker Compose stack in `infra/compose/docker-compose.dev.yml` with:

- `postgres:16.9` pinned by digest
- `emqx/emqx:5.10.0` pinned by digest
- `hummingbot/hummingbot-api:1.0.1` pinned by digest
- `hummingbot/hummingbot-mcp` pinned by digest

The Hummingbot API image does not currently expose `/health`, so the compose stack mounts a tiny wrapper module at `infra/compose/hummingbot_api_health.py` and starts `uvicorn` against that wrapped app to provide a stable health endpoint without forking the upstream image.

## Infrastructure Quick Start

```bash
make up
make smoke
make logs
make down
```

`make up` auto-creates ignored local env files at `infra/env/api.env` and `infra/env/mcp.env` with development defaults if they do not exist yet. The committed templates remain in:

- `infra/env/api.env.example`
- `infra/env/mcp.env.example`

Runtime state stays under `runtime/`, which remains gitignored.
