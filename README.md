# EDGE-AGENT

Semi-autonomous crypto day trading agent for Binance Futures perpetuals. Uses AI agents to find high-conviction long and short opportunities, execute within hard risk limits, and report via Telegram.

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
| 2.3 | Telegram notifications & approvals | Done |
| 2.3b | OpenClaw workspace | Done |
| 2.5 | Generalize to day trading (long + short) | Done |
| 3.2 | Signal quality iteration tools | Done |
| 4.0 | Altcoin opportunity scanner | Done |
| 4.1 | Portfolio Advisor + Risk Monitor agents | Done |
| 4.2 | VPS deployment infrastructure | Done |
| 2.4 | Testnet integration (24-48h run) | Ready |
| 3.0 | Go live (real Binance) | Prepared |

See `tasks/` for detailed PRDs per phase.

## Architecture

```
Operator (Telegram + OpenClaw)
    → Push notifications & approvals (Telegram notifier)
    → Commands & queries (OpenClaw via Telegram channel)
        → Portfolio Advisor (weekly Moonshot-backed reviews)
        → Risk Monitor (continuous rule-based surveillance)
            → Policy/Risk Layer (hard limits, human-set)
                → Hummingbot MCP / API (execution)
                    → Binance Futures (exchange)
```

### Agents (5)
- **Market Analyst** — Moonshot.ai-powered signal generation. Analyzes price, volume, funding rates, order book. Identifies both long and short opportunities. Read-only, never trades.
- **Trader** — Executes signals within risk bounds. Opens longs or shorts based on analyst conviction. Manages positions and dynamic LLM-driven exits. Every action goes through policy.
- **Reporter** — Push notifications to Telegram. Trade alerts, approval requests, periodic and daily reports.
- **Portfolio Advisor** — Weekly Moonshot-backed portfolio reviews. Suggests rebalancing, exposure changes, and parameter adjustments.
- **Risk Monitor** — Continuous rule-based surveillance. Alerts on approaching limits, funding rate flips, unusual volatility. No LLM, pure speed.

### Supporting tools
- **Altcoin Scanner** — Ranks Binance perp pairs by opportunity score (volume, funding, volatility). Read-only suggestions.
- **Signal Quality Tools** — Export signals to CSV, compute metrics (win rate, R:R, drawdown), update OpenClaw memory journal.

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
| Allowed sides | long, short |

Config: `configs/risk/policy.yml`. Reloads on change, no restart needed. Conservative live config available at `configs/risk/policy-live-conservative.yml`.

## Repository layout

```text
EDGE-AGENT/
├── src/
│   ├── agents/
│   │   ├── analyst/        # Market analysis + signal generation
│   │   ├── trader/         # Trade execution + position management
│   │   ├── reporter/       # Telegram notifications + reports
│   │   ├── advisor/        # Portfolio advisor (Moonshot-backed)
│   │   ├── risk_monitor/   # Continuous risk surveillance
│   │   └── scanner/        # Altcoin opportunity scanner
│   ├── clients/            # Typed Hummingbot API wrappers
│   ├── policy/             # Risk engine, rules, audit logging
│   ├── shared/             # Config, models, Moonshot client
│   └── strategies/         # Hummingbot V2 controllers
├── tools/                  # Signal export, metrics, journal tools
├── configs/
│   └── risk/               # policy.yml, altcoins.yml, live-conservative.yml
├── docs/
│   ├── runbooks/           # Operational guides
│   └── decisions/          # Architecture decision records
├── infra/
│   ├── compose/            # Docker Compose (dev + prod)
│   ├── env/                # .env.example templates
│   ├── scripts/            # up, down, smoke, deploy, backup, health
│   └── Dockerfile          # Agent container for production
├── openclaw/
│   ├── workspace/          # AGENTS, SOUL, TOOLS, memory, runbooks, skills
│   └── sync/               # Sync script to ~/.openclaw/workspace
├── tasks/                  # Phase PRDs
├── tests/
│   ├── unit/
│   └── integration/
└── runtime/                # Gitignored: bot state, logs, audit
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

### Core operations
| Target | Description |
|---|---|
| `make up` | Start Docker infrastructure (Hummingbot API, Postgres, EMQX, MCP) |
| `make down` | Stop infrastructure |
| `make logs` | Tail infrastructure logs |
| `make smoke` | Verify infrastructure health |
| `make test` | Run Python test suite |

### Agent operations
| Target | Description |
|---|---|
| `make analyst-once` | Run one market analysis cycle |
| `make trader-once` | Run one full trader cycle (analyst → policy → execute → review) |
| `make reporter` | Start Telegram reporter (notifications, approvals, reports) |
| `make advisor-once` | Run one portfolio advisory review |
| `make risk-monitor` | Start continuous risk surveillance |
| `make scan-altcoins` | Scan and rank altcoin opportunities |
| `make test-trade` | Run hardcoded BTC-USDT short pipeline on testnet |

### Integration & analysis
| Target | Description |
|---|---|
| `make integration-test` | Run all agents for 24-48h testnet validation |
| `make integration-report` | Post-run analysis of integration test |
| `make signal-export` | Export signals to CSV |
| `make signal-metrics` | Export + compute signal quality metrics |
| `make signal-journal` | Full signal quality pipeline + OpenClaw journal update |

### VPS deployment
| Target | Description |
|---|---|
| `make deploy VPS=user@host` | Deploy to remote VPS |
| `make rollback VPS=user@host` | Rollback to previous version |
| `make backup VPS=user@host` | Download configs and state from VPS |
| `make health VPS=user@host` | Check remote system health |

## Infrastructure

### Development
Docker Compose stack in `infra/compose/docker-compose.dev.yml`:
- **PostgreSQL 16.9** — Hummingbot API state
- **EMQX 5.10.0** — MQTT broker for bot communication
- **Hummingbot API 1.0.1** — FastAPI execution layer
- **Hummingbot MCP** — Agent-to-exchange bridge

### Production
`infra/compose/docker-compose.prod.yml` adds restart policies, memory limits, log rotation, and an agent container. See `docs/runbooks/vps-setup.md` for deployment guide.

## Documentation

### Runbooks (`docs/runbooks/`)
- `integration-test.md` — 24-48h testnet validation procedure
- `go-live.md` — Switch from testnet to real Binance
- `disable-trading.md` — Emergency stop (4 methods)
- `rollback.md` — Revert from live to testnet
- `vps-setup.md` — VPS provisioning and deployment

### Architecture decisions (`docs/decisions/`)
- `0001-compose-not-fork.md` — Composition over forking upstream repos
- `0002-risk-gateway.md` — Policy layer between AI and execution
- `0003-generalist-day-trading.md` — Direction-agnostic long + short

### OpenClaw workspace (`openclaw/workspace/`)
Agent definitions, memory files (venues, risk policy, signals, incidents), operational runbooks, and local skills for position checking, strategy deployment, and risk overrides.

## Stack

- **Python 3.11+** — primary language
- **Hummingbot API** — exchange execution
- **Hummingbot MCP** — agent bridge
- **Moonshot.ai (kimi-k2.5)** — LLM inference (analyst, trader, advisor)
- **OpenClaw** — AI agent orchestration, memory, sessions
- **Telegram** — operator notifications, approvals, commands
- **Docker Compose** — dev and production infrastructure
- **PostgreSQL + EMQX** — Hummingbot state and messaging

## Security

This is a **public open-source repository**. See `AGENTS.md` for full security rules.

- Never commit secrets, API keys, or tokens
- Only `.env.example` with placeholders in git
- All credentials via environment variables
- `runtime/` is gitignored (state, logs, audit)
- Testnet safety guard prevents accidental live trading
- Policy layer enforces hard limits — no AI override possible
