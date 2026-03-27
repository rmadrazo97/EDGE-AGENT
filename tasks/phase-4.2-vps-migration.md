---
phase: 4.2
title: VPS Migration
status: pending
depends_on: phase-3.0
---

# PRD: VPS Migration

## Goal
Move the system from local Mac to a VPS for true 24/7 operation with reliability.

## Requirements

### VPS requirements
- Linux (Ubuntu 22.04+ recommended)
- Minimum: 2 vCPU, 4GB RAM, 40GB SSD
- Stable network connection with low latency to Binance
- Region: consider Singapore or Tokyo for Binance latency

### Docker Compose production file
- `infra/compose/docker-compose.prod.yml`
- All services with restart policies (`restart: unless-stopped`)
- Resource limits per container
- Healthchecks on all services
- Log rotation configured

### Deployment
- Script: `infra/scripts/deploy.sh` — deploys to VPS via SSH
- Handles: pull latest code, rebuild images, restart services
- Zero-downtime approach: new containers start before old ones stop
- Rollback: `infra/scripts/rollback.sh` — reverts to previous deployment

### Monitoring
- Container health monitoring
- Disk space alerts
- Process crash detection and auto-restart
- Telegram alert if any service goes down
- Optional: simple metrics dashboard (Grafana/Prometheus if justified)

### Security
- SSH key auth only (no password)
- Firewall: only SSH and outbound HTTPS
- No exposed ports except SSH
- Secrets managed via environment variables on VPS
- Regular security updates

### Backup
- Daily backup of: configs, audit logs, position state
- Backup to local machine or cloud storage
- Restore procedure documented in runbook

## Acceptance criteria
- [ ] System runs on VPS for 72h without intervention
- [ ] Auto-restart works on service crash
- [ ] Deploy script works end-to-end
- [ ] Rollback script tested
- [ ] Telegram alerts on service failure
- [ ] Backup and restore tested
- [ ] No secrets in deployment scripts

## Out of scope
- Kubernetes
- Multi-region deployment
- CDN / load balancing
- Auto-scaling

## Implementation Notes

### Files created
- `infra/compose/docker-compose.prod.yml` -- Production compose with restart policies, memory limits, log rotation, tighter health checks, and no EMQX dashboard port. Includes `edge-agent-agents` service.
- `infra/Dockerfile` -- Minimal Python 3.11-slim image for the agent container.
- `infra/scripts/deploy.sh` -- Deploys to VPS via rsync + SSH. Supports `--with-env` flag. Prompts for confirmation if containers are already running.
- `infra/scripts/rollback.sh` -- Stops containers, reverts to a given commit/tag (default HEAD~1), restarts, verifies health.
- `infra/scripts/backup.sh` -- Downloads configs, audit logs, and trader state to local `backups/<date>/` directory.
- `infra/scripts/health-check.sh` -- Checks container status, API health, disk space, agent processes, and Docker disk usage. Outputs clean status report.
- `docs/runbooks/vps-setup.md` -- Full setup guide covering specs, region, Docker install, security, monitoring cron, backup schedule, and troubleshooting.

### Makefile targets added
- `make deploy VPS=user@host`
- `make rollback VPS=user@host`
- `make backup VPS=user@host`
- `make health VPS=user@host`

### Design decisions
- Remote deploy path is `/opt/edge-agent` (standard Linux convention for third-party apps).
- All scripts are POSIX sh compatible (`#!/usr/bin/env sh`, `set -eu`).
- Deploy script requires interactive confirmation when containers are running (no auto-restart).
- Production compose removes EMQX dashboard port (18083) and all other non-essential ports.
- Memory limits: postgres 512MB, emqx 512MB, hummingbot-api 1GB, mcp 256MB, agents 512MB.
- Log rotation: 10MB max size, 3 files max per container.
