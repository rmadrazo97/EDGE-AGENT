---
phase: 3.1
title: OpenClaw Workspace
status: pending
depends_on: phase-2.4
---

# PRD: OpenClaw Workspace Setup

## Goal
Set up the OpenClaw workspace as the deeper control plane for the trading system. Telegram handles quick interactions; OpenClaw handles complex operations, memory, and multi-agent coordination.

## Requirements

### Workspace structure (`openclaw/workspace/`)
```
openclaw/workspace/
├── AGENTS.md          # Agent definitions and operating rules
├── SOUL.md            # System personality and principles
├── TOOLS.md           # Available tools and when to use them
├── IDENTITY.md        # System identity
├── USER.md            # Operator profile
├── MEMORY.md          # Memory index
├── memory/
│   ├── venues.md      # Binance-specific notes and quirks
│   ├── risk-policy.md # Current risk parameters and rationale
│   ├── signals.md     # Signal quality notes and learnings
│   └── incidents.md   # Issues encountered and resolutions
├── runbooks/
│   ├── bootstrap.md
│   ├── go-live.md
│   ├── pause-trading.md
│   ├── incident-response.md
│   └── rotate-credentials.md
└── skills/
    └── local/
        ├── check-positions.md
        ├── deploy-strategy.md
        └── risk-override.md
```

### AGENTS.md content
Define 3 agents with clear boundaries:
- **Market Analyst**: read-only, generates signals, never trades
- **Trader**: executes within policy, manages positions
- **Reporter**: read-only, formats and sends reports

Operating rules:
- No agent can modify risk policy
- No agent can bypass the policy layer
- Trader must always go through policy evaluation

### Hummingbot MCP integration
- Install Hummingbot skills into OpenClaw workspace
- Configure MCP connection to Hummingbot API
- Verify: operator can ask OpenClaw for balances, positions, market data

### Local skills
- `check-positions`: detailed position view with P&L
- `deploy-strategy`: start/stop agents with specific config
- `risk-override`: temporarily adjust risk parameters (logged)

### Sync to OpenClaw home
- Script: `openclaw/sync/sync_to_home.sh` — copies workspace to `~/.openclaw/workspace`
- Pattern A from blueprint: repo is source of truth, synced to home

## Acceptance criteria
- [ ] OpenClaw workspace synced and functional
- [ ] Hummingbot MCP tools accessible from OpenClaw
- [ ] Operator can query balances and positions via OpenClaw
- [ ] Memory files index correctly
- [ ] Runbooks are accessible
- [ ] Local skills work

## Out of scope
- Pattern B (separate workspace repo)
- Multi-project OpenClaw setup
- Custom MCP tool development
