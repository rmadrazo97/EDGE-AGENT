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
- `make test-trade`
- `make analyst-once`
- `make trader-once`
- `make telegram-bot`

`make test-trade` runs a hardcoded BTC-USDT Binance Futures demo short through Hummingbot, arms a managed 3% stop-loss trigger locally, waits 60 seconds, and then closes the position while logging the full lifecycle to `runtime/test-trade/*.jsonl`.
`make analyst-once` runs one Moonshot-backed market analysis cycle for the configured analyst pairs and logs the cycle results to `runtime/analyst/*.jsonl`.
`make trader-once` runs one trader cycle: consume analyst signals, evaluate them through policy, open approved testnet shorts, and review open positions for model-driven exits while persisting state to `runtime/trader/state.json`.
`make telegram-bot` starts the Telegram operator bot for `/status`, `/positions`, `/balance`, `/signals`, `/pause`, `/resume`, `/kill`, `/risk`, and `/pnl`, plus approval prompts and periodic reports.

## Telegram Bot

Phase 2.3 adds a Telegram operator interface under `src/agents/reporter/`:

- `telegram_bot.py` boots the polling bot and scheduled jobs
- `commands.py` handles operator commands, approval callbacks, and runtime event polling
- `formatters.py` formats concise mobile-first alerts and reports
- `approvals.py` persists pending approval requests under `runtime/reporter/approvals.json`

Required local `.env` settings:

- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_OPERATOR_CHAT_ID`
- `EDGE_AGENT_TELEGRAM_REPORT_INTERVAL_HOURS` (default `4`)
- `EDGE_AGENT_TELEGRAM_DAILY_REPORT_TIME` (default `21:00`)
- `EDGE_AGENT_TIMEZONE` (default `UTC`)

The bot only responds to the configured `TELEGRAM_OPERATOR_CHAT_ID`. All operator commands are audit-logged to `runtime/audit/telegram.jsonl`.

## Infrastructure Stack

Phase 1.1 wires a local Docker Compose stack in `infra/compose/docker-compose.dev.yml` with:

- `postgres:16.9` pinned by digest
- `emqx/emqx:5.10.0` pinned by digest
- `hummingbot/hummingbot-api:1.0.1` pinned by digest
- `hummingbot/hummingbot-mcp` pinned by digest

The Hummingbot API image does not currently expose `/health`, so the compose stack mounts a tiny wrapper module at `infra/compose/hummingbot_api_health.py` and starts `uvicorn` against that wrapped app to provide a stable health endpoint without forking the upstream image.

For local host access, PostgreSQL is published on port `5454` to avoid collisions with other apps that already use the default `5432`.

## Infrastructure Quick Start

```bash
make up
make smoke
make logs
make down
```

`make up` auto-creates ignored local env files at `infra/env/api.env` and `infra/env/mcp.env` with development defaults if they do not exist yet. It also prepares the Hummingbot runtime tree under `runtime/hummingbot-api/bots/credentials/` so connector credentials can be persisted correctly. The committed templates remain in:

- `infra/env/api.env.example`
- `infra/env/mcp.env.example`

Runtime state stays under `runtime/`, which remains gitignored.

The Docker socket mount on the Hummingbot API container is intentional for local bot management only. Treat it as a privileged development-only setup, not a production default.
