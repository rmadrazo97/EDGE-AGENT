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

The infrastructure and smoke targets are stubs in this phase and will be wired in later tasks.
