#!/usr/bin/env sh
set -eu

usage() {
  printf 'Usage: %s user@host\n' "$(basename "$0")" >&2
  exit 1
}

if [ $# -lt 1 ]; then
  usage
fi

VPS_HOST="$1"
REMOTE_DIR="/opt/edge-agent"
ROOT_DIR="$(CDPATH='' cd -- "$(dirname -- "$0")/../.." && pwd)"
BACKUP_DATE="$(date +%Y%m%d-%H%M%S)"
BACKUP_DIR="$ROOT_DIR/backups/$BACKUP_DATE"

printf '==> Backing up from %s\n' "$VPS_HOST"
printf '==> Saving to %s\n' "$BACKUP_DIR"

mkdir -p "$BACKUP_DIR/configs" "$BACKUP_DIR/runtime/audit" "$BACKUP_DIR/runtime/trader"

# Download configs
printf '==> Downloading configs/\n'
rsync -az "$VPS_HOST:$REMOTE_DIR/configs/" "$BACKUP_DIR/configs/" 2>/dev/null || printf '  (no configs found)\n'

# Download audit logs
printf '==> Downloading runtime/audit/\n'
rsync -az "$VPS_HOST:$REMOTE_DIR/runtime/audit/" "$BACKUP_DIR/runtime/audit/" 2>/dev/null || printf '  (no audit logs found)\n'

# Download trader state
printf '==> Downloading runtime/trader/state.json\n'
rsync -az "$VPS_HOST:$REMOTE_DIR/runtime/trader/state.json" "$BACKUP_DIR/runtime/trader/state.json" 2>/dev/null || printf '  (no state.json found)\n'

# Print summary
printf '\n==> Backup summary:\n'
if command -v du >/dev/null 2>&1; then
  du -sh "$BACKUP_DIR"/* 2>/dev/null || true
fi
printf '==> Backup complete: %s\n' "$BACKUP_DIR"
