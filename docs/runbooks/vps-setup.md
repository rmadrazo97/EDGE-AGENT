# VPS Setup Runbook

## Recommended Specs

| Resource | Minimum | Recommended |
|----------|---------|-------------|
| CPU      | 2 vCPU  | 2 vCPU      |
| RAM      | 4 GB    | 4 GB        |
| Disk     | 40 GB SSD | 40 GB SSD |
| OS       | Ubuntu 22.04+ | Ubuntu 24.04 LTS |

### Region Selection

Choose a region close to Binance servers for lowest latency:

- **Singapore** (preferred) -- lowest latency to Binance
- **Tokyo** -- good alternative, slightly higher latency
- Avoid US/EU regions unless required for compliance

## Initial Setup

### 1. SSH access

```sh
# Generate a key pair locally if you don't have one
ssh-keygen -t ed25519 -C "edge-agent-vps"

# Copy your public key to the VPS
ssh-copy-id user@your-vps-ip

# Disable password authentication on the VPS
sudo sed -i 's/#PasswordAuthentication yes/PasswordAuthentication no/' /etc/ssh/sshd_config
sudo systemctl restart sshd
```

### 2. Firewall

```sh
# On the VPS
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw enable
```

No other inbound ports are needed. All exchange communication is outbound HTTPS.

### 3. Install Docker

```sh
# Install Docker Engine (official method)
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER

# Log out and back in, then verify
docker --version
docker compose version
```

### 4. Clone the repository

```sh
sudo mkdir -p /opt/edge-agent
sudo chown $USER:$USER /opt/edge-agent
git clone <your-repo-url> /opt/edge-agent
cd /opt/edge-agent
```

### 5. Configure environment

```sh
# Copy env templates and fill in real values
cp infra/env/api.env.example infra/env/api.env
cp infra/env/mcp.env.example infra/env/mcp.env

# Edit with your exchange API keys and credentials
# NEVER commit these files
nano infra/env/api.env
nano infra/env/mcp.env
```

Alternatively, deploy env files from your local machine:

```sh
# From your local machine
./infra/scripts/deploy.sh --with-env user@your-vps-ip
```

## Start Services

```sh
cd /opt/edge-agent

# Create required runtime directories
mkdir -p runtime/hummingbot-api/bots runtime/hummingbot-mcp runtime/audit runtime/trader

# Start all services
docker compose -f infra/compose/docker-compose.prod.yml up -d --build

# Check status
docker compose -f infra/compose/docker-compose.prod.yml ps
```

## Monitoring

### Health check cron job

Set up a periodic health check that sends Telegram alerts on failure:

```sh
crontab -e
```

Add the following (runs every 5 minutes):

```
*/5 * * * * /opt/edge-agent/infra/scripts/health-check.sh user@localhost 2>&1 | tail -1 | grep -q 'HEALTHY' || curl -s "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage?chat_id=${TELEGRAM_CHAT_ID}&text=EDGE-AGENT: Health check failed on $(hostname) at $(date -u +\%H:\%M:\%Z)"
```

For remote monitoring from your local machine:

```
*/5 * * * * /path/to/edge-agent/infra/scripts/health-check.sh user@your-vps-ip 2>&1 | tail -1 | grep -q 'HEALTHY' || curl -s "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage?chat_id=${TELEGRAM_CHAT_ID}&text=EDGE-AGENT: Health check failed"
```

### Manual health check

```sh
# From your local machine
make health VPS=user@your-vps-ip
```

## Backup Schedule

Set up daily backups via cron:

```sh
crontab -e
```

Add:

```
0 2 * * * /path/to/edge-agent/infra/scripts/backup.sh user@your-vps-ip >> /path/to/edge-agent/backups/backup.log 2>&1
```

This runs at 02:00 daily and downloads configs, audit logs, and trader state.

## Deployment

```sh
# Deploy latest code
make deploy VPS=user@your-vps-ip

# Deploy with env files
./infra/scripts/deploy.sh --with-env user@your-vps-ip

# Rollback to previous version
make rollback VPS=user@your-vps-ip

# Rollback to a specific commit or tag
./infra/scripts/rollback.sh user@your-vps-ip v1.0.0
```

## Security Checklist

- [ ] SSH key authentication only (password auth disabled)
- [ ] UFW firewall enabled (SSH only inbound)
- [ ] No exposed container ports (except MQTT 1883 internal)
- [ ] Secrets in env files only, never in code/scripts
- [ ] Regular `apt update && apt upgrade` schedule
- [ ] Docker images pinned by digest (already done in compose)
- [ ] `.env` files excluded from git and rsync

## Troubleshooting

### Services not starting

```sh
# Check logs for a specific service
docker compose -f infra/compose/docker-compose.prod.yml logs --tail=50 <service-name>

# Check all logs
docker compose -f infra/compose/docker-compose.prod.yml logs --tail=100
```

### Disk space issues

```sh
# Check disk usage
df -h

# Clean up Docker artifacts
docker system prune -f
docker volume prune -f  # WARNING: removes unused volumes
```

### Agent crashes

```sh
# Check agent container logs
docker compose -f infra/compose/docker-compose.prod.yml logs --tail=100 edge-agent-agents

# Restart just the agent container
docker compose -f infra/compose/docker-compose.prod.yml restart edge-agent-agents
```
