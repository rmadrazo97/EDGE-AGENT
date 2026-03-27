---
phase: 1.0
title: Repo Skeleton
status: pending
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
- [ ] `git status` shows clean structure
- [ ] `.gitignore` prevents secrets and runtime data from being tracked
- [ ] `make` shows available targets
- [ ] `pip install -e .` works

## Out of scope
- Any actual code logic
- Docker compose files (Phase 1.1)
- OpenClaw workspace content (Phase 3.2)
