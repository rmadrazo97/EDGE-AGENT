---
phase: 1.0
title: Repo Skeleton
status: completed
depends_on: none
---

# PRD: Repo Skeleton

## Goal
Create the lean project structure that supports the EDGE-AGENT system without over-engineering. Only create directories and files that Phase 1-2 actually need.

## Requirements

### Directory structure
```
EDGE-AGENT/
├── src/
│   ├── agents/
│   │   ├── analyst/
│   │   ├── trader/
│   │   └── reporter/
│   ├── policy/
│   ├── clients/
│   └── shared/
├── configs/
│   ├── risk/
│   └── controllers/
├── infra/
│   ├── compose/
│   ├── env/
│   └── scripts/
├── openclaw/
│   └── workspace/
├── tasks/
├── tests/
│   ├── unit/
│   └── integration/
├── runtime/          # gitignored
├── .env.example
├── .gitignore
├── Makefile
├── pyproject.toml
└── README.md
```

### .gitignore
Must exclude: runtime/, .env, .env.*, infra/env/*.env, **/__pycache__/, *.log, *.db, openclaw/home/

### .env.example
Template with all required env vars (Binance keys, Hummingbot API URL, Moonshot API key, Telegram bot token) — no real values.

### Makefile
Targets: `up`, `down`, `logs`, `smoke`, `test` — stubs that will be filled in subsequent phases.

### pyproject.toml
Python 3.11+, initial deps: httpx, pydantic, python-telegram-bot, pytest

## Acceptance criteria
- [x] `git status` shows only the intended scaffold changes before commit
- [x] `.gitignore` prevents secrets and runtime data from being tracked
- [x] `make` shows available targets
- [x] `pip install -e .` works

## Implementation notes
- Added the Phase 1 package and directory skeleton under `src/`, `configs/`, `infra/`, `openclaw/workspace/`, and `tests/`.
- Added a root `.env.example` with placeholder values only for Binance, Hummingbot API, Moonshot, and Telegram settings.
- Added a minimal `Makefile` with documented stub targets for infrastructure and smoke-test phases plus a working `test` target.
- Added `pyproject.toml` with editable-install support for Python 3.11+ and initial dependencies: `httpx`, `pydantic`, `python-telegram-bot`, and `pytest`.
- Added a baseline unit test to verify the top-level Python packages are importable.

## Verification
- `make`
- `python3 -m pip install -e .`
- `make test`

## Out of scope
- Any actual code logic
- Docker compose files (Phase 1.1)
- OpenClaw workspace content (Phase 3.2)
