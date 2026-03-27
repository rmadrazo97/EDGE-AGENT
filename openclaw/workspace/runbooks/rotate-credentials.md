# Runbook: Rotate Credentials

How to rotate API keys and tokens used by EDGE-AGENT.

## Binance API keys

### 1. Generate new keys

- Log in to Binance > API Management
- Create a new API key with Futures permissions only (no withdrawal)
- For testnet: use the testnet portal at `https://testnet.binancefuture.com`

### 2. Update environment

Edit `infra/env/hummingbot.env`:

```
BINANCE_API_KEY=<new_key>
BINANCE_SECRET=<new_secret>
```

### 3. Restart

```bash
make down
make up
make smoke
```

### 4. Verify

Ask OpenClaw: "What's my balance?" -- should return correct data.

### 5. Revoke old keys

Delete the old API key from Binance API Management.

## Telegram bot token

### 1. Generate new token

Message @BotFather on Telegram: `/revoke` to revoke the old token, then `/token` to get a new one.

### 2. Update environment

Edit `infra/env/edge-agent.env`:

```
TELEGRAM_BOT_TOKEN=<new_token>
```

### 3. Restart the reporter

```bash
make reporter
```

### 4. Verify

Send a test message to the bot. Check that notifications arrive.

## Moonshot.ai API key

### 1. Generate new key

Go to the Moonshot.ai dashboard and create a new API key.

### 2. Update environment

Edit `infra/env/edge-agent.env`:

```
MOONSHOT_API_KEY=<new_key>
```

### 3. Restart the analyst

```bash
make analyst-once
```

### 4. Verify

Check that a signal is generated in `runtime/signals/analyst.jsonl`.

### 5. Revoke old key

Delete the old key from the Moonshot.ai dashboard.

## General notes

- Never commit `.env` files to git
- After rotating, verify each affected component individually
- Log the rotation in `memory/incidents.md` if it was triggered by a security event
