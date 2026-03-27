# EDGE-AGENT

Semi-autonomous crypto shorting system for Binance Futures perpetuals. Uses AI agents to find short opportunities, execute within hard risk limits, and report via Telegram.

## Status

| Phase | Description | Status |
|---|---|---|
| 1.0 | Repo skeleton | Done |
| 1.1 | Docker infrastructure | Done |
| 1.2 | Smoke tests | Done |
| 1.3 | Binance testnet connection | Done |
| 1.4 | First trade pipeline | Done |
| 2.0 | Market analyst agent | Done |
| 2.1 | Trader agent | Done |
| 2.2 | Risk policy layer | Done |
| 2.3 | Telegram notifications & approvals | In progress |
| 2.3b | OpenClaw workspace + Telegram channel | Pending |
| 2.4 | Testnet integration (24-48h) | Pending |
| 3.0 | Go live (real Binance) | Pending |

See `tasks/` for detailed PRDs per phase.

## Architecture

```
Operator (Telegram + OpenClaw)
    → Push notifications & approvals (custom Telegram notifier)
    → Commands & queries (OpenClaw via Telegram channel)
        → Policy/Risk Layer (hard limits, human-set)
            → Hummingbot MCP / API (execution)
                → Binance Futures (exchange)
```

### Agents
- **Market Analyst** — Moonshot.ai-powered signal generation. Analyzes price, volume, funding rates, order book. Read-only, never trades.
- **Trader** — Executes signals within risk bounds. Manages positions and dynamic LLM-driven exits. Every action goes through policy.
- **Reporter** — Push notifications to Telegram. Trade alerts, approval requests, periodic and daily reports.

### Risk rules (non-negotiable, human-set)
| Rule | Value |
|---|---|
| Max risk per trade | 2% of equity |
| Max daily loss | 5% of equity |
| Max total exposure | 30% of equity |
| Max single position | 10% of equity |
| Max leverage | 3x |
| Stop loss per position | 3% of entry |
| Allowed pairs | BTC-USDT, ETH-USDT |

Config: `configs/risk/policy.yml`. Reloads on change, no restart needed.

## Repository layout

```text
EDGE-AGENT/
├── src/
│   ├── agents/
│   │   ├── analyst/      # Market analysis + signal generation
│   │   ├── trader/       # Trade execution + position management
│   │   └── reporter/     # Telegram notifications + reports
│   ├── clients/          # Typed Hummingbot API wrappers
│   ├── policy/           # Risk engine, rules, audit logging
│   ├── shared/           # Config, models, Moonshot client
│   └── strategies/       # Hummingbot V2 controllers
├── configs/
│   └── risk/             # policy.yml (committed defaults)
├── infra/
│   ├── compose/          # Docker Compose + health wrapper
│   ├── env/              # .env.example templates
│   └── scripts/          # up, down, logs, smoke
├── openclaw/
│   └── workspace/        # OpenClaw agent workspace (Phase 2.3b)
├── tasks/                # Phase PRDs
├── tests/
│   ├── unit/
│   └── integration/
└── runtime/              # Gitignored: bot state, logs, audit
```

## Quick start

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e .
cp .env.example .env
# Edit .env with your credentials
make
```

## Make targets

| Target | Description |
|---|---|
| `make up` | Start Docker infrastructure (Hummingbot API, Postgres, EMQX, MCP) |
| `make down` | Stop infrastructure |
| `make logs` | Tail infrastructure logs |
| `make smoke` | Verify infrastructure health |
| `make test` | Run Python test suite |
| `make test-trade` | Run hardcoded BTC-USDT short pipeline on testnet |
| `make analyst-once` | Run one Moonshot-backed market analysis cycle |
| `make trader-once` | Run one full trader cycle (analyst → policy → execute → review) |
| `make reporter` | Start Telegram reporter (notifications, approvals, reports) |

## Infrastructure

Docker Compose stack in `infra/compose/docker-compose.dev.yml`:

- **PostgreSQL 16.9** — Hummingbot API state
- **EMQX 5.10.0** — MQTT broker for bot communication
- **Hummingbot API 1.0.1** — FastAPI execution layer
- **Hummingbot MCP** — Agent-to-exchange bridge

All images pinned by digest. `make up` auto-creates local env files with dev defaults if missing. PostgreSQL published on port `5454` to avoid collisions.

The upstream Hummingbot API image lacks `/health`, so a thin wrapper (`infra/compose/hummingbot_api_health.py`) is mounted into the container.

Docker socket mount on Hummingbot API is for local bot management only — not a production default.

## Telegram reporter

Push notifications and approval flow under `src/agents/reporter/`:

- `notifier.py` — sends push alerts and approval requests
- `agent.py` — polling loop for approval callbacks and scheduled reports
- `formatters.py` — concise mobile-first message formatting
- `approvals.py` — persistent approval state with timeout handling

Required `.env` settings:
```
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
TELEGRAM_OPERATOR_CHAT_ID=your_chat_id_here
```

Optional settings: `EDGE_AGENT_REPORT_INTERVAL_HOURS` (default 4), `EDGE_AGENT_DAILY_REPORT_HOUR_UTC` (default 21), `EDGE_AGENT_APPROVAL_TIMEOUT_SECONDS` (default 300).

Reporter only sends to the configured operator chat ID. All notifications logged to `runtime/audit/telegram.jsonl`, approvals to `runtime/audit/policy.jsonl`.

## Stack

- **Python 3.11+**
- **Hummingbot API** — exchange execution
- **Hummingbot MCP** — agent bridge
- **Moonshot.ai (kimi-k2.5)** — LLM inference
- **OpenClaw** — AI agent orchestration (Phase 2.3b)
- **Telegram** — operator notifications + commands
- **Docker Compose** — local infrastructure

## Security

This is a **public open-source repository**. See `AGENTS.md` for full security rules.

- Never commit secrets, API keys, or tokens
- Only `.env.example` with placeholders in git
- All credentials via environment variables
- `runtime/` is gitignored (state, logs, audit)
- Testnet safety guard prevents accidental live trading
