---
phase: 2.3b
title: OpenClaw Workspace + Telegram Channel
status: in-progress
depends_on: phase-2.3
---

# PRD: OpenClaw Workspace + Telegram Channel

## Goal
Set up the OpenClaw workspace as the conversational control plane and connect it to Telegram as a channel. Operator sends natural language commands via Telegram; OpenClaw routes them through agents with full context, memory, and tools.

## What changed
This merges the old Phase 3.1 (OpenClaw Workspace) with the command/query portion of the old Phase 2.3 (Telegram Bot). OpenClaw replaces custom command handlers.

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
        ├── pause-resume.md
        └── risk-override.md
```

### AGENTS.md content
Define agent boundaries:
- **Market Analyst**: read-only, generates signals, never trades
- **Trader**: executes within policy, manages positions
- **Reporter**: read-only, formats and sends notifications

Operating rules:
- No agent can modify risk policy without operator confirmation
- No agent can bypass the policy layer
- Trader must always go through policy evaluation
- OpenClaw is the conversational interface, not the execution layer

### Telegram channel setup
- Connect OpenClaw to Telegram as a channel
- Operator messages in Telegram → OpenClaw processes with full context
- OpenClaw responds in Telegram with formatted answers

### Commands via OpenClaw (natural language, not slash commands)
Instead of rigid `/status`, `/positions` etc., the operator asks naturally:

| What operator says | What OpenClaw does |
|---|---|
| "What's my status?" | Queries positions, balance, daily P&L via Hummingbot MCP |
| "Show positions" | Detailed position view with unrealized P&L |
| "What's my balance?" | Account equity and available margin |
| "Any recent signals?" | Reads analyst JSONL logs, summarizes last 6h |
| "Pause trading" | Sets `trading_enabled: false` in policy config |
| "Resume trading" | Sets `trading_enabled: true` in policy config |
| "Kill everything" | Closes all positions and pauses (with confirmation) |
| "Show risk limits" | Reads policy.yml and shows current values + usage |
| "How did today go?" | Today's realized + unrealized P&L summary |

### Hummingbot MCP integration
- Install Hummingbot skills into OpenClaw workspace: `npx skills add hummingbot/skills --yes`
- Configure MCP connection to Hummingbot API
- Verify: operator can ask OpenClaw for balances, positions, market data

### Local skills
- `check-positions`: reads trader state + live positions, formats summary
- `deploy-strategy`: start/stop agent processes with specific config
- `pause-resume`: toggles `trading_enabled` in `configs/risk/policy.yml` (logged)
- `risk-override`: temporarily adjust risk parameters (logged, requires confirmation)

### Sync to OpenClaw home
- Script: `openclaw/sync/sync_to_home.sh` — copies workspace to `~/.openclaw/workspace`
- Pattern A from blueprint: repo is source of truth, synced to home

## Acceptance criteria
- [x] OpenClaw workspace synced and functional
- [ ] Telegram channel connected — messages route to OpenClaw
- [ ] Operator can query balances and positions via Telegram/OpenClaw
- [ ] Operator can pause/resume trading via Telegram/OpenClaw
- [ ] Hummingbot MCP tools accessible
- [x] Memory files index correctly
- [x] Runbooks are accessible
- [x] Local skills work
- [ ] Kill command requires confirmation

## Implementation notes (Phase 2.3b workspace)

**Completed — workspace files created (2026-03-27):**
- All workspace Markdown files created under `openclaw/workspace/`
- 3 agents defined (Market Analyst, Trader, Reporter) with clear boundaries
- 4 memory files under `memory/` (venues, risk-policy, signals, incidents)
- 5 runbooks under `runbooks/` (bootstrap, go-live, pause-trading, incident-response, rotate-credentials)
- 4 local skills under `skills/local/` (check-positions, deploy-strategy, pause-resume, risk-override)
- Sync script at `openclaw/sync/sync_to_home.sh`

**Remaining — requires runtime setup:**
- Telegram channel connection (requires bot token + OpenClaw channel config)
- Hummingbot MCP skill installation (`npx skills add hummingbot/skills --yes`)
- End-to-end testing of natural language commands via Telegram
- Kill command confirmation flow (depends on Telegram channel)

## Out of scope
- Push notifications (handled by Phase 2.3 notifier)
- Approval inline keyboards (handled by Phase 2.3 notifier)
- Pattern B (separate workspace repo)
- Multi-project OpenClaw setup
