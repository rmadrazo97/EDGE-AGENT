#!/usr/bin/env sh
# Sync workspace to OpenClaw home directory
set -eu
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
WORKSPACE_SRC="$SCRIPT_DIR/../workspace"
WORKSPACE_DST="${OPENCLAW_HOME:-$HOME/.openclaw}/workspace"
mkdir -p "$WORKSPACE_DST"
rsync -av --delete "$WORKSPACE_SRC/" "$WORKSPACE_DST/"
echo "Synced workspace to $WORKSPACE_DST"
