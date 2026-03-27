# Hummingbot + Controllers + MCP + OpenClaw project blueprint

Date: 2026-03-27

## 1. Executive recommendation

Build this as a **composition repo**, not a deep fork.

Recommended baseline:

1. Use **Hummingbot API** as the central execution and orchestration server.
2. Put your custom strategy logic in **Hummingbot Strategy V2 Controllers**.
3. Use **Hummingbot MCP** for tool access from AI agents.
4. Use **OpenClaw** as the operator shell: workspace, skills, memory, sessions, and optional chat surfaces.
5. Put a small **custom policy/risk layer** in front of write actions in production.

Why this is the right default:

- Hummingbot API is explicitly positioned as the central hub for trading operations and AI assistant integration. [S1][S2]
- Hummingbot Strategy V2 explicitly recommends Controllers for production-grade, configurable, long-running, multi-strategy deployments. [S4][S5]
- Hummingbot MCP is explicitly an interface to Hummingbot API for AI assistants. [S8][S9]
- OpenClaw docs explicitly recommend keeping the workspace and config outside the upstream repo so updates do not hurt local tailoring. [S17]

Only fork upstream repos when you hit a real boundary such as:

- you need to patch a connector,
- you need new API router behavior,
- you need to change MCP tool behavior,
- or you need to modify Hummingbot core controller/executor internals.

## 2. What each moving part should own

### Hummingbot API

Use this as the control plane and execution plane. Official docs describe it as a FastAPI server backed by PostgreSQL and EMQX, with router groups for docker management, accounts, connectors, portfolio, trading, bot orchestration, scripts/controllers, market data, backtesting, archived bots, and Gateway / DEX operations. [S1][S3]

This should own:

- exchange accounts and credentials,
- portfolio state,
- order placement and position management,
- bot lifecycle,
- strategy config CRUD,
- market data access,
- backtesting,
- Gateway lifecycle and DEX operations.

### Hummingbot core: Controllers, Scripts, Executors

Hummingbot Strategy V2 has three core building blocks:

- **Executors**: discrete trading workflows
- **Scripts**: simple Python entry points for learning and prototyping
- **Controllers**: production-grade modular sub-strategies for advanced deployments [S4]

Controllers are the important one for this repo. Official docs say they:

- are production-grade,
- interface with `MarketDataProvider`,
- emit `ExecutorActions`,
- are loaded by `v2_with_controllers.py`,
- and can run multiple controllers in one bot instance. [S5][S6]

This means your actual alpha and execution logic should live here, while the agent should handle planning, operations, and approvals around them.

### Hummingbot MCP

Hummingbot MCP is the agent bridge. Official docs say it gives AI assistants access to data sources, tools, and workflows including balances, order history, market prices, funding rates, place orders, manage positions, execute swaps, and deploy bots. [S8]

The tools reference groups capability into accounts, portfolio, trading, market data, bot orchestration, executors, scripts/controllers, Gateway/DEX, and archived bots. [S10]

### Hummingbot Skills

Hummingbot also publishes installable skills for AI agents and specifically documents OpenClaw support. The docs show `npx skills add hummingbot/skills --yes` and note that for OpenClaw the skills are installed into the OpenClaw workspace skill area. [S11]

Useful published skills include:

- `hummingbot` for CLI-like workflows over the API [S12]
- `hummingbot-deploy` for standing up the API / MCP / Condor stack [S13]
- `hummingbot-developer` for source-based dev stack workflows [S11]

### OpenClaw

OpenClaw should be the operator-facing layer, not the exchange adapter.

Relevant OpenClaw facts from the docs:

- Tailoring should live outside the upstream repo, in `~/.openclaw/workspace` plus `~/.openclaw/openclaw.json`. [S17]
- The agent runtime expects a workspace and documents bootstrap files like `AGENTS.md`, `SOUL.md`, `TOOLS.md`, `IDENTITY.md`, and `USER.md`, plus a workspace skills area. [S18]
- Memory indexing is Markdown-first: `MEMORY.md`, `memory/**/*.md`, and extra Markdown paths. [S19]
- Sessions and transcripts live under `~/.openclaw/agents/<agentId>/sessions/`. [S18][S20]

That makes OpenClaw ideal for:

- operator conversations,
- human approvals,
- runbooks and memory,
- scheduled or channel-triggered ops,
- and local skills that wrap your own project logic.

### Your custom code

Your own repo should own the things the upstream stack does not:

- policy and risk checks,
- approval workflows,
- deployment wrappers,
- audit logging,
- observability,
- strategy config generation,
- and any house rules about venues, pairs, notional, leverage, or allowed controller types.

## 3. Recommended production architecture

Use this mental model:

```text
Operator / team
    |
    v
OpenClaw workspace + channels + memory
    |
    +--> Hummingbot Skills (high-level task wrappers)
    |
    +--> Optional local OpenClaw skills for your own workflows
    |
    v
Policy / Risk service (your code; recommended in prod)
    |
    v
Hummingbot MCP or direct Hummingbot API client
    |
    v
Hummingbot API
    |-- PostgreSQL
    |-- EMQX
    |-- optional Gateway for DEX / CLMM / swaps
    |-- bot instances
            |
            v
      v2_with_controllers.py
            |
            v
      custom Controllers
            |
            v
        Executors
            |
            v
        Exchanges / DEXs
```

Important design choice:

- In **development**, direct MCP -> Hummingbot API is fine for speed. [S8][S9]
- In **production**, put a thin policy service between the agent and any write action so the LLM never becomes the final authority for order placement. This is a recommendation, not an official requirement.

## 4. Recommended repository structure

Start with a lean composition repo.

```text
trading-agent/
├── README.md
├── docs/
│   ├── architecture.md
│   ├── source-notes.md
│   ├── runbooks/
│   │   ├── bootstrap.md
│   │   ├── deploy.md
│   │   ├── incident.md
│   │   └── rollback.md
│   └── decisions/
│       ├── 0001-compose-not-fork.md
│       └── 0002-risk-gateway.md
├── infra/
│   ├── compose/
│   │   ├── docker-compose.dev.yml
│   │   ├── docker-compose.prod.yml
│   │   └── docker-compose.obs.yml
│   ├── env/
│   │   ├── api.env.example
│   │   ├── mcp.env.example
│   │   ├── openclaw.env.example
│   │   ├── gateway.env.example
│   │   └── risk.env.example
│   ├── monitoring/
│   └── scripts/
│       ├── up.sh
│       ├── down.sh
│       └── reset-dev.sh
├── src/
│   ├── policy_gateway/
│   │   ├── app.py
│   │   ├── routes/
│   │   ├── adapters/
│   │   │   └── hummingbot_api/
│   │   ├── risk/
│   │   ├── approvals/
│   │   └── audit/
│   ├── strategies/
│   │   ├── controllers/
│   │   │   ├── market_making/
│   │   │   ├── directional/
│   │   │   └── common/
│   │   ├── scripts/
│   │   └── templates/
│   ├── clients/
│   │   ├── accounts.py
│   │   ├── portfolio.py
│   │   ├── trading.py
│   │   ├── bot_orchestration.py
│   │   ├── controllers.py
│   │   ├── executors.py
│   │   ├── market_data.py
│   │   └── gateway.py
│   └── shared/
│       ├── config.py
│       ├── models.py
│       └── logging.py
├── configs/
│   ├── controllers/
│   ├── scripts/
│   ├── accounts/
│   ├── gateway/
│   ├── risk/
│   └── openclaw/
├── openclaw/
│   ├── workspace/
│   │   ├── AGENTS.md
│   │   ├── MEMORY.md
│   │   ├── memory/
│   │   ├── prompts/
│   │   ├── skills/
│   │   │   └── local/
│   │   └── runbooks/
│   └── sync/
│       ├── sync_to_home.sh
│       └── sync_from_home.sh
├── tools/
│   ├── bootstrap_dev.sh
│   ├── create_controller_config.py
│   ├── deploy_controller.py
│   ├── smoke_test_api.sh
│   ├── smoke_test_mcp.md
│   └── export_openclaw_context.py
├── tests/
│   ├── unit/
│   ├── integration/
│   └── smoke/
├── runtime/
│   ├── bots/
│   ├── logs/
│   ├── exports/
│   └── tmp/
├── .env.example
├── .gitignore
└── Makefile
```

## 5. Why this layout is efficient for a coding agent

### Mirror upstream boundaries instead of inventing your own

Hummingbot API itself is laid out around `bots`, `database`, `models`, `routers`, `services`, and `utils`. [S15]

Hummingbot core itself is laid out around `conf`, `controllers`, `scripts`, `hummingbot`, `logs`, and `test`. [S14]

If your repo mirrors those boundaries, a coding agent can infer where new code belongs and avoid cross-layer sprawl.

### Keep your wrapper modules aligned with official router groups

Your internal API client should mirror the Hummingbot API router groups documented by Hummingbot: accounts, connectors, portfolio, trading, bot orchestration, executors, scripts/controllers, market data, backtesting, archived bots, and Gateway. [S3]

This makes it easier for the agent to:

- map code to docs,
- generate test coverage per router family,
- and avoid random one-off helper scripts.

### Keep trading logic in Controllers, not in OpenClaw prompts

Official docs recommend Controllers for production-grade V2 deployments, while Scripts are for simpler or learning use cases. [S4][S5]

That means:

- business logic and execution logic belong in `src/strategies/controllers/`
- operator guidance belongs in `openclaw/workspace/AGENTS.md` and runbooks
- dynamic parameter values belong in `configs/controllers/`

### Keep memory in Markdown because OpenClaw indexes Markdown

OpenClaw memory search is designed around `MEMORY.md`, `memory/**/*.md`, and extra Markdown paths. [S19]

So keep these as Markdown:

- architecture notes,
- incident runbooks,
- venue quirks,
- controller tuning notes,
- postmortems,
- and approval rules.

This gives your coding / ops agent much better retrieval than burying knowledge in JSON or source comments.

## 6. What should live in git vs not in git

### Commit to git

- custom controllers and scripts
- config templates
- OpenClaw workspace source files that contain prompts, memory, and runbooks
- infra compose files and bootstrap scripts
- tests
- docs and decisions

### Do not commit

- exchange secrets
- generated runtime bot state
- Postgres volumes
- EMQX volumes
- OpenClaw sessions and transcripts
- exported reports or PnL snapshots unless explicitly curated

Suggested `.gitignore` targets:

```text
runtime/
.env
.env.*
!.env.example
infra/env/*.env
openclaw/home/
**/__pycache__/
.pytest_cache/
.mypy_cache/
*.db
*.sqlite
*.log
```

## 7. The important split: templates vs runtime state

Do not mix source-of-truth templates with generated runtime files.

Use:

- `configs/controllers/` for committed YAML templates
- `runtime/bots/` for generated or deployed bot-specific state
- `openclaw/workspace/` for committed agent steering and memory
- the actual OpenClaw home directory for live sessions and credentials, which live outside the repo by design. [S17][S18][S20]

## 8. How to handle OpenClaw cleanly

OpenClaw docs recommend that your real workspace live outside the upstream repo and even suggest making the workspace a private git repo. [S17]

Two good patterns:

### Pattern A: repo is source of truth, synced into OpenClaw home

- Keep `openclaw/workspace/` in this repo.
- Sync or symlink it to your actual OpenClaw workspace on the dev machine.
- Keep live credentials and sessions in the normal OpenClaw home directories.

This is the safest and cleanest default.

### Pattern B: dedicated private OpenClaw workspace repo

- Keep a separate private repo just for `~/.openclaw/workspace`.
- Reference it from this project in docs or as a submodule.

This is better if one OpenClaw workspace will operate multiple projects.

For most teams, Pattern A is simpler.

## 9. How to handle Hummingbot upstream repos

Use two modes.

### Mode 1: image-first composition (recommended to start)

- Use official containers or cloned repos only for deployment.
- Keep your code in this repo.
- Do not vendor upstream repos yet.

Choose this when:

- you are mostly building controllers, configs, tooling, and agent workflows,
- you do not need to patch Hummingbot internals,
- and you want the coding agent to move fast.

### Mode 2: source-dev mode (add later if needed)

Add:

```text
upstream/
├── hummingbot/
├── hummingbot-api/
└── mcp/
```

Use these as pinned submodules or pinned clone refs.

Choose this when:

- you need source-level debugging,
- you need to patch core controller behavior,
- you need MCP tool changes,
- or you need API router / service changes.

## 10. Coding-agent kickoff plan

Give your coding agent this order of work.

### Phase 1: infra bootstrap

1. Create the repo skeleton above.
2. Add compose and env example files for Hummingbot API, PostgreSQL, EMQX, optional Gateway, and your policy service.
3. Add a smoke test that checks API health and API docs availability. Hummingbot docs explicitly call out `/health` and `/docs` for verification. [S2][S15]

Deliverable: `make up`, `make down`, `make smoke-api`.

### Phase 2: client wrappers

1. Build a thin internal client organized by official Hummingbot API router groups. [S3]
2. Add typed request / response models for the endpoints you will actually use first: accounts, portfolio, trading, bot orchestration, controllers, executors, market data.

Deliverable: a minimal SDK your own code can use without touching raw HTTP everywhere.

### Phase 3: strategy package

1. Add `src/strategies/controllers/`.
2. Start with one simple controller family only.
3. Add config templates under `configs/controllers/`.
4. Add deployment helpers that generate or push configs and then start the relevant bot.

Deliverable: one repeatable controller deployment path.

### Phase 4: OpenClaw workspace

1. Create `openclaw/workspace/AGENTS.md` with clear operating rules.
2. Create `MEMORY.md` and `memory/` notes for exchange rules, risk limits, and runbooks. OpenClaw memory indexes Markdown only. [S19]
3. Add a local OpenClaw skill that calls your policy service for dangerous actions.
4. Keep general read-only Hummingbot workflows available through Hummingbot MCP / skills.

Deliverable: an operator can ask OpenClaw for balances, status, deployment, and controlled actions.

### Phase 5: risk and approvals

1. Build a write-path guard that validates:
   - venue allowlist
   - pair allowlist
   - max notional
   - leverage ceiling
   - order type rules
   - controller allowlist
2. Require explicit approval for destructive or high-risk actions.
3. Log every approved action to an append-only audit file or DB table.

Deliverable: no trade or deployment happens without passing policy.

### Phase 6: tests and runbooks

1. Unit test risk rules.
2. Integration test API wrappers.
3. Add Markdown runbooks for bootstrap, incident response, rollback, and credential rotation.
4. Add postmortem templates to OpenClaw memory.

Deliverable: the coding agent has both code tests and human-readable ops guidance.

## 11. Specific file conventions that help the agent

### Controller naming

Mirror Hummingbot's own controller naming style, which maps folder paths into dotted controller names. [S5]

Example:

```text
src/strategies/controllers/market_making/pmm_spread_guard.py
src/strategies/controllers/directional/funding_basis_reversion.py
src/strategies/controllers/common/signals.py
```

### Config naming

Follow a deterministic pattern:

```text
configs/controllers/<strategy_family>/<venue>/<pair>/<profile>.yml
```

Example:

```text
configs/controllers/market_making/binance_perpetual/ETH-USDT/default.yml
configs/controllers/directional/hyperliquid_perpetual/SOL-USDC/conservative.yml
```

### Runbook naming

Because OpenClaw memory is Markdown-first, keep runbooks human-readable and stable:

```text
docs/runbooks/bootstrap.md
docs/runbooks/controller-deploy.md
docs/runbooks/disable-trading.md
docs/runbooks/rotate-secrets.md
```

### OpenClaw workspace contents

Keep the workspace small and operational:

```text
openclaw/workspace/
├── AGENTS.md
├── MEMORY.md
├── memory/
│   ├── venues.md
│   ├── controller-notes.md
│   ├── risk-policy.md
│   └── incidents.md
├── runbooks/
└── skills/local/
```

## 12. Useful operational shortcuts

### Use Hummingbot's published building blocks instead of reinventing them

- Hummingbot API already provides router groups and execution primitives. [S1][S3]
- Hummingbot V2 already provides Controllers, Scripts, Executors, and `v2_with_controllers.py`. [S4][S5][S6][S7]
- Hummingbot MCP already exposes broad capability groups to agents. [S8][S10]
- Hummingbot Skills already provide OpenClaw-compatible packaged workflows. [S11][S12][S13]

### Keep custom logic thin around those primitives

Your custom layer should mostly do:

- policy,
- approvals,
- naming,
- config generation,
- audit,
- and house-specific workflow glue.

## 13. Anti-patterns to avoid

- Do not start by forking all three upstream repos.
- Do not put trading logic mainly in prompts.
- Do not let OpenClaw or MCP place trades in production without a policy gate.
- Do not commit OpenClaw live state, sessions, or credentials. [S17][S18][S20]
- Do not mix config templates with runtime-generated bot state.
- Do not target V1 strategies through Hummingbot API; Hummingbot's agent-facing skill docs explicitly note API support is V2-only. [S12]

## 14. Minimal source map for the coding agent

Use these first when the agent needs grounding.

### Core Hummingbot API

- [S1] Hummingbot API overview
- [S2] Hummingbot API installation and verification
- [S3] Hummingbot API routers
- [S15] Hummingbot API repository tree

### Core Hummingbot strategy layer

- [S4] Hummingbot Strategies overview and V2 component guidance
- [S5] Controllers docs
- [S6] Controller walkthrough
- [S7] Sample scripts and `v2_with_controllers.py`
- [S14] Hummingbot core repository tree

### Agent bridge and skills

- [S8] Hummingbot MCP overview
- [S9] Hummingbot MCP installation
- [S10] MCP tools reference
- [S11] Hummingbot Skills docs
- [S12] `hummingbot` skill page
- [S13] `hummingbot-deploy` skill page
- [S16] Hummingbot MCP repository tree

### OpenClaw runtime

- [S17] OpenClaw setup and workspace guidance
- [S18] OpenClaw agent runtime
- [S19] OpenClaw memory behavior
- [S20] OpenClaw session management

## 15. Final recommendation in one sentence

Start with a **private composition repo** that keeps **Hummingbot API + MCP + OpenClaw** as mostly upstream components, puts your edge into **custom V2 Controllers + policy/risk wrappers + Markdown runbooks**, and only introduces forks when a concrete upstream boundary forces it.

---

## Sources

- [S1] Hummingbot API overview: https://hummingbot.org/hummingbot-api/
- [S2] Hummingbot API installation: https://hummingbot.org/hummingbot-api/installation/
- [S3] Hummingbot API routers: https://hummingbot.org/hummingbot-api/routers/
- [S4] Hummingbot Strategies overview: https://hummingbot.org/strategies/
- [S5] Hummingbot Controllers docs: https://hummingbot.org/strategies/v2-strategies/controllers/
- [S6] Hummingbot Controller walkthrough: https://hummingbot.org/strategies/v2-strategies/walkthrough-controller/
- [S7] Hummingbot Sample Scripts: https://hummingbot.org/strategies/scripts/examples/
- [S8] Hummingbot MCP overview: https://hummingbot.org/mcp/
- [S9] Hummingbot MCP installation: https://hummingbot.org/mcp/installation/
- [S10] Hummingbot MCP tools reference: https://hummingbot.org/mcp/tools/
- [S11] Hummingbot Skills docs: https://hummingbot.org/mcp/skills/
- [S12] Hummingbot skill page: https://skills.hummingbot.org/skill/hummingbot
- [S13] Hummingbot deploy skill page: https://skills.hummingbot.org/skill/hummingbot-deploy
- [S14] Hummingbot core repo: https://github.com/hummingbot/hummingbot
- [S15] Hummingbot API repo: https://github.com/hummingbot/hummingbot-api
- [S16] Hummingbot MCP repo: https://github.com/hummingbot/mcp
- [S17] OpenClaw setup: https://openclaw.im/docs/start/setup
- [S18] OpenClaw agent runtime: https://openclaw.im/docs/concepts/agent
- [S19] OpenClaw memory: https://openclaw.im/docs/concepts/memory
- [S20] OpenClaw session management: https://openclaw.im/docs/concepts/session
- [S21] Hummingbot guide category (official strategy guides): https://hummingbot.org/guides/
- [S22] Awesome Hummingbot community index: https://github.com/hummingbot/awesome-hummingbot
