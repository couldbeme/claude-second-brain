#!/usr/bin/env bash
# Hourly memory sync: backup DB to git, reembed missing vectors, optionally push.
# Called by launchd agent com.claude.sync-memories.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_PYTHON="${SCRIPT_DIR}/.venv/bin/python3"
SYNC_PY="${SCRIPT_DIR}/sync.py"
LOG_DIR="${HOME}/.claude/logs"
mkdir -p "$LOG_DIR"

log() { echo "$(date '+%Y-%m-%d %H:%M:%S') $*"; }

log "=== Memory sync starting ==="

# 1. Backup (git add + commit memory.db)
log "Step 1: Backup"
"$VENV_PYTHON" "$SYNC_PY" backup --push 2>&1 || log "Backup failed (non-fatal)"

# 2. Reembed missing vectors (only if LM Studio is running)
if curl -sf http://localhost:1234/v1/models >/dev/null 2>&1; then
    log "Step 2: Reembed (LM Studio detected)"
    "$VENV_PYTHON" "$SYNC_PY" reembed 2>&1 || log "Reembed failed (non-fatal)"
else
    log "Step 2: Skipped reembed (LM Studio not running)"
fi

log "=== Memory sync complete ==="
