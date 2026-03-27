# Runbook: Bootstrap

How to set up EDGE-AGENT from scratch on a new machine.

## Prerequisites

- Python 3.11+
- Docker and Docker Compose
- Git
- Binance Futures testnet account with API key
- Telegram bot token (from @BotFather)
- Moonshot.ai API key

## Steps

### 1. Clone and set up Python environment

```bash
git clone <repo-url> EDGE-AGENT
cd EDGE-AGENT
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

### 2. Create environment files

```bash
cp infra/env/hummingbot.env.example infra/env/hummingbot.env
cp infra/env/edge-agent.env.example infra/env/edge-agent.env
```

Edit each `.env` file and fill in real credentials. Never commit these files.

### 3. Start infrastructure

```bash
make up
```

This starts Hummingbot API, PostgreSQL, and EMQX via Docker Compose.

### 4. Verify infrastructure

```bash
make smoke
```

All health checks should pass.

### 5. Configure Binance testnet

- Set `BINANCE_API_KEY` and `BINANCE_SECRET` in `infra/env/hummingbot.env`
- Ensure connector is set to `binance_perpetual_testnet`
- Verify with: ask OpenClaw "What's my balance?" or check via Hummingbot API directly

### 6. Sync OpenClaw workspace

```bash
./openclaw/sync/sync_to_home.sh
```

### 7. Run tests

```bash
make test
```

### 8. Test the pipeline

```bash
make analyst-once   # generates a signal
make trader-once    # processes the signal
```

Check `runtime/signals/analyst.jsonl` and `runtime/audit/policy.jsonl` for output.
