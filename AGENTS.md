# AGENTS.md — EDGE-AGENT

## Project overview
Semi-autonomous crypto shorting system for Binance Futures perpetuals. Uses Hummingbot (execution), OpenClaw (AI orchestration), Moonshot.ai (LLM inference), and Telegram (operator interface).

## CRITICAL: This is a public open-source repository

This repo is **public**. Every commit is visible to the world. Treat every file as if it will be read by strangers.

### Secrets and credentials — absolute rules
- **NEVER** commit API keys, tokens, passwords, or secrets of any kind
- **NEVER** commit `.env` files — only `.env.example` with placeholder values
- **NEVER** hardcode Binance API keys, Telegram bot tokens, Moonshot.ai API keys, database passwords, or any credential in source code
- **NEVER** commit OpenClaw session data, transcripts, or live state
- **ALWAYS** use environment variables for all secrets
- **ALWAYS** check `git diff` before committing to verify no secrets are staged
- If you see a secret in code during review, **flag it immediately** — do not proceed

### Files that must NEVER exist in git
- `*.env` (except `*.env.example`)
- `infra/env/*.env`
- Any file containing real API keys or tokens
- `runtime/` directory contents
- `openclaw/home/` directory contents
- Database files (`*.db`, `*.sqlite`)
- Log files (`*.log`)

### .env.example convention
All `.env.example` files must use obvious placeholders:
```
BINANCE_API_KEY=your_binance_api_key_here
BINANCE_SECRET=your_binance_secret_here
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
MOONSHOT_API_KEY=your_moonshot_api_key_here
```

## Architecture

```
Operator (Telegram / OpenClaw)
    → Policy/Risk Layer (hard limits, human-set)
        → Hummingbot MCP / API (execution)
            → Binance Futures (exchange)
```

### Agents (3 core, expand later)
- **Market Analyst** — reads market data, generates short signals. Read-only, never trades.
- **Trader** — executes signals within risk bounds, manages positions. Goes through policy layer for every action.
- **Reporter** — sends Telegram notifications and reports. Read-only.

### Risk rules (non-negotiable)
| Rule | Value |
|---|---|
| Max risk per trade | 2% of equity |
| Max daily loss | 5% of equity |
| Max total exposure | 30% of equity |
| Max single position | 10% of equity |
| Max leverage | 3x |
| Stop loss per position | 3% of entry |
| Allowed pairs | BTC-USDT, ETH-USDT (expand later) |

These are **hard-coded human-set limits**. No agent or LLM may override them. The AI optimizes strategy within these bounds.

## Project structure
- `tasks/` — phased PRDs (phase-X.Y-name.md), the build plan
- `src/agents/` — agent implementations (analyst, trader, reporter)
- `src/policy/` — risk policy engine (the gate between AI and trades)
- `src/clients/` — thin wrappers around Hummingbot API endpoints
- `src/shared/` — config, models, logging
- `src/strategies/` — Hummingbot V2 controllers and scripts
- `configs/` — YAML config templates (risk rules, controller params)
- `infra/` — Docker Compose, env examples, deploy scripts
- `openclaw/workspace/` — OpenClaw agent definitions, memory, runbooks
- `tests/` — unit and integration tests
- `runtime/` — gitignored, ephemeral bot state and logs

## Stack
- **Python 3.11+** — primary language
- **Hummingbot API** — exchange execution and bot orchestration
- **Hummingbot MCP** — agent-to-exchange bridge
- **OpenClaw** — AI agent workspace, memory, sessions
- **Moonshot.ai** — LLM inference (cost-efficient, supports function calling)
- **Telegram** — primary operator interface
- **Docker Compose** — local and production infrastructure
- **PostgreSQL** — Hummingbot API state
- **EMQX** — MQTT broker for bot communication

## Conventions
- Controllers follow Hummingbot V2 naming: `src/strategies/controllers/<family>/<name>.py`
- Configs follow: `configs/controllers/<family>/<venue>/<pair>/<profile>.yml`
- All agents communicate through typed Pydantic models, not raw dicts
- Policy evaluation is mandatory before any write action (order, position, config change)
- Audit log is append-only: `runtime/audit/policy.jsonl`
- Markdown for all documentation and OpenClaw memory (indexed by OpenClaw)

## Testing
- Unit tests for risk rules: 100% coverage required
- Integration tests for API clients: run against live services
- Smoke tests: `make smoke` verifies infrastructure health
- Testnet first: all new features validated on Binance testnet before live

## Build phases
See `tasks/` folder for detailed PRDs:
1. **Phase 1** (Weekend 1): Repo skeleton → Infrastructure → Smoke tests → Binance testnet → First trade pipeline
2. **Phase 2** (Weekend 2): Market Analyst → Trader → Risk Policy → Telegram → Testnet integration
3. **Phase 3** (Weekend 3): Go live (conservative) → OpenClaw workspace → Signal iteration
4. **Phase 4** (Ongoing): Altcoin expansion → Additional agents → VPS migration
