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
