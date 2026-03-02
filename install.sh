#!/usr/bin/env bash
# install.sh — Install/sync Claude Code Team Toolkit to ~/.claude/
#
# Usage:
#   ./install.sh            Full install (first time or re-sync)
#   ./install.sh --check    Dry-run: show what would change
#   ./install.sh --migrate  Full migration from manual-copy setup
#
# What it does:
#   1. Creates per-file symlinks for each base agent and command
#   2. Symlinks memory-mcp source files (not .venv or __pycache__)
#   3. Creates/updates memory-mcp virtualenv + deps
#   4. Copies CLAUDE.md.template on first install (never overwrites)
#   5. Installs git post-merge hook for auto-sync on git pull
#   6. Preserves all personal (non-symlink) files
#
# Personal files: any regular .md file in ~/.claude/agents/ or ~/.claude/commands/
# that is NOT a symlink is considered personal and is never touched.

set -euo pipefail

TOOLKIT_DIR="$(cd "$(dirname "$0")" && pwd)"
CLAUDE_DIR="${HOME}/.claude"
DRY_RUN=false
MIGRATE=false
CREATED=0
UPDATED=0
SKIPPED=0
CONFLICTS=0

case "${1:-}" in
    --check)  DRY_RUN=true ;;
    --migrate) MIGRATE=true ;;
esac

# --- Colors ---
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
CYAN='\033[0;36m'
DIM='\033[0;90m'
RESET='\033[0m'

info()    { printf "${GREEN}[+]${RESET} %s\n" "$1"; }
warn()    { printf "${YELLOW}[!]${RESET} %s\n" "$1"; }
skip()    { printf "${DIM}[=]${RESET} %s\n" "$1"; }
conflict(){ printf "${RED}[!]${RESET} %s\n" "$1"; }

# --- Core: link a single file ---
link_file() {
    local src="$1" dst="$2"
    local name
    name="$(basename "$dst")"

    if [[ -L "$dst" ]]; then
        local current
        current="$(readlink "$dst")"
        if [[ "$current" == "$src" ]]; then
            SKIPPED=$((SKIPPED + 1))
            return 0
        fi
        # Symlink exists but points elsewhere — update
        if $DRY_RUN; then
            warn "UPDATE $name → $src"
            UPDATED=$((UPDATED + 1))
            return 0
        fi
        ln -sf "$src" "$dst"
        info "Updated $name"
        UPDATED=$((UPDATED + 1))
    elif [[ -e "$dst" ]]; then
        # Regular file with same name as base — collision
        conflict "CONFLICT: $dst is a regular file (personal?)"
        if $DRY_RUN; then
            warn "  Would backup to ${name}.personal-backup and create symlink"
            CONFLICTS=$((CONFLICTS + 1))
            return 0
        fi
        mv "$dst" "${dst}.personal-backup"
        ln -s "$src" "$dst"
        warn "  Backed up to ${name}.personal-backup → created symlink"
        CONFLICTS=$((CONFLICTS + 1))
    else
        # New symlink
        if $DRY_RUN; then
            info "CREATE $name → $src"
            CREATED=$((CREATED + 1))
            return 0
        fi
        ln -s "$src" "$dst"
        CREATED=$((CREATED + 1))
    fi
}

# --- Sync all .md files from a repo dir to a target dir ---
sync_md_files() {
    local src_dir="$1" dst_dir="$2" label="$3"
    mkdir -p "$dst_dir"

    local count=0
    for src_file in "$src_dir"/*.md; do
        [[ -f "$src_file" ]] || continue
        link_file "$src_file" "$dst_dir/$(basename "$src_file")"
        count=$((count + 1))
    done
    skip "  $label: $count base files checked"
}

# --- Sync memory-mcp source files (not .venv, not __pycache__) ---
sync_memory_mcp() {
    local src_dir="$TOOLKIT_DIR/memory-mcp"
    local dst_dir="$CLAUDE_DIR/memory-mcp"
    mkdir -p "$dst_dir"

    for src_file in "$src_dir"/*.py "$src_dir"/requirements.txt; do
        [[ -f "$src_file" ]] || continue
        link_file "$src_file" "$dst_dir/$(basename "$src_file")"
    done
}

# --- Manage memory-mcp venv ---
setup_venv() {
    local venv_dir="$CLAUDE_DIR/memory-mcp/.venv"
    local req_file="$TOOLKIT_DIR/memory-mcp/requirements.txt"

    if $DRY_RUN; then
        if [[ ! -d "$venv_dir" ]]; then
            info "Would create venv at $venv_dir"
        fi
        info "Would install/update memory-mcp dependencies"
        return 0
    fi

    if [[ ! -d "$venv_dir" ]]; then
        info "Creating memory-mcp venv..."
        python3 -m venv "$venv_dir"
    fi

    # Check if requirements changed (compare checksums)
    local checksum_file="$venv_dir/.requirements-checksum"
    local current_checksum
    current_checksum="$(shasum "$req_file" 2>/dev/null | cut -d' ' -f1)"

    if [[ -f "$checksum_file" ]] && [[ "$(cat "$checksum_file")" == "$current_checksum" ]]; then
        skip "  memory-mcp deps up to date"
        return 0
    fi

    info "Installing memory-mcp dependencies..."
    "$venv_dir/bin/pip" install -q -r "$req_file" 2>&1 | tail -1 || true
    echo "$current_checksum" > "$checksum_file"
}

# --- Install git post-merge hook ---
install_hook() {
    local hook_dir="$TOOLKIT_DIR/.git/hooks"
    local hook_file="$hook_dir/post-merge"

    if [[ -f "$hook_file" ]] && grep -q "toolkit-auto-sync" "$hook_file" 2>/dev/null; then
        skip "  Post-merge hook already installed"
        return 0
    fi

    if $DRY_RUN; then
        info "Would install post-merge hook at $hook_file"
        return 0
    fi

    mkdir -p "$hook_dir"

    # Append to existing hook if present, or create new
    if [[ -f "$hook_file" ]]; then
        cat >> "$hook_file" << 'HOOK'

# --- toolkit-auto-sync ---
TOOLKIT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
echo "[toolkit] Auto-syncing to ~/.claude/ ..."
"$TOOLKIT_DIR/install.sh" 2>&1 | sed 's/^/  /'
# --- end toolkit-auto-sync ---
HOOK
    else
        cat > "$hook_file" << 'HOOK'
#!/usr/bin/env bash
# --- toolkit-auto-sync ---
TOOLKIT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
echo "[toolkit] Auto-syncing to ~/.claude/ ..."
"$TOOLKIT_DIR/install.sh" 2>&1 | sed 's/^/  /'
# --- end toolkit-auto-sync ---
HOOK
    fi
    chmod +x "$hook_file"
    info "Installed post-merge hook"
}

# --- Migration: clean up second-brain tracking ---
run_migration() {
    if ! $MIGRATE; then return 0; fi

    echo ""
    printf "${CYAN}--- Second Brain Migration ---${RESET}\n"

    if [[ ! -d "$CLAUDE_DIR/.git" ]]; then
        warn "~/.claude/ is not a git repo — skipping migration"
        return 0
    fi

    local brain_dir="$CLAUDE_DIR"
    local gitignore="$brain_dir/.gitignore"

    # Pre-flight: show what will be preserved
    echo ""
    info "PRESERVED (never touched):"
    echo "    ~/.claude/CLAUDE.md"
    echo "    ~/.claude/README.md"
    echo "    ~/.claude/SYSTEM.md"
    echo "    ~/.claude/settings.json"
    echo "    ~/.claude/memory/memory.db"
    echo "    ~/.claude/memory-mcp/.venv/"
    echo "    ~/.claude/memory-mcp/README.md"
    echo "    ~/.claude/memory-mcp/tests/"
    echo "    ~/.claude/plans/"
    echo "    ~/.claude/projects/"
    echo "    ~/.claude/history.jsonl"
    echo "    + all Claude Code internal dirs (backups, cache, debug, etc.)"
    echo ""
    info "WILL REPLACE with symlinks:"
    echo "    ~/.claude/agents/*.md       ($(ls "$brain_dir/agents/"*.md 2>/dev/null | wc -l | tr -d ' ') files)"
    echo "    ~/.claude/commands/*.md      ($(ls "$brain_dir/commands/"*.md 2>/dev/null | wc -l | tr -d ' ') files)"
    echo "    ~/.claude/memory-mcp/*.py    (5 files)"
    echo "    ~/.claude/memory-mcp/requirements.txt"
    echo ""

    # Step 1: Ensure clean state
    info "Checking second-brain git status..."
    if ! (cd "$brain_dir" && git diff --quiet 2>/dev/null); then
        warn "Second brain has uncommitted changes — committing snapshot first"
        (cd "$brain_dir" && git add -A && git commit -m "chore: snapshot before toolkit symlink migration" 2>/dev/null) || true
    fi

    # Step 2: Remove toolkit files from tracking (keep on disk for now)
    info "Removing toolkit-managed files from second-brain tracking..."
    (
        cd "$brain_dir"
        # Remove agents and commands from git index
        git rm --cached agents/*.md 2>/dev/null || true
        git rm --cached commands/*.md 2>/dev/null || true
        # Remove memory-mcp source from git index
        for f in server.py db.py embeddings.py hybrid_search.py sync.py requirements.txt; do
            git rm --cached "memory-mcp/$f" 2>/dev/null || true
        done
    )

    # Step 3: Update .gitignore
    info "Updating second-brain .gitignore..."
    local ignore_marker="# Toolkit-managed (symlinks to claude-code-team-toolkit)"
    if ! grep -q "$ignore_marker" "$gitignore" 2>/dev/null; then
        cat >> "$gitignore" << IGNORE

$ignore_marker
agents/*.md
commands/*.md
memory-mcp/*.py
memory-mcp/requirements.txt
IGNORE
    fi

    # Step 4: Commit
    (cd "$brain_dir" && git add .gitignore && git commit -m "chore: stop tracking toolkit files — now managed via symlinks" 2>/dev/null) || true

    # Step 5: Delete the stale regular files (symlinks will replace them)
    info "Removing stale copies (will be replaced by symlinks)..."
    for f in "$brain_dir"/agents/*.md; do
        [[ -L "$f" ]] && continue  # Already a symlink — skip
        [[ -f "$f" ]] && rm "$f"
    done
    for f in "$brain_dir"/commands/*.md; do
        [[ -L "$f" ]] && continue
        [[ -f "$f" ]] && rm "$f"
    done
    for f in server.py db.py embeddings.py hybrid_search.py sync.py requirements.txt; do
        local target="$brain_dir/memory-mcp/$f"
        [[ -L "$target" ]] && continue
        [[ -f "$target" ]] && rm "$target"
    done

    info "Migration complete — stale files removed, ready for symlinks"
}

# =============================================================================
# Main
# =============================================================================

echo ""
printf "${CYAN}Claude Code Team Toolkit Installer${RESET}\n"
echo "===================================="
echo "Toolkit: $TOOLKIT_DIR"
echo "Target:  $CLAUDE_DIR"
$DRY_RUN && printf "${YELLOW}Mode: DRY RUN (no changes)${RESET}\n"
$MIGRATE && printf "${YELLOW}Mode: MIGRATE (includes second-brain cleanup)${RESET}\n"
echo ""

# Migration (if requested)
run_migration

# 1. Agents
printf "${CYAN}--- Agents ---${RESET}\n"
sync_md_files "$TOOLKIT_DIR/agents" "$CLAUDE_DIR/agents" "Agents"

# Count personal agents
PERSONAL_AGENTS=0
for f in "$CLAUDE_DIR/agents"/*.md; do
    [[ -f "$f" ]] && [[ ! -L "$f" ]] && PERSONAL_AGENTS=$((PERSONAL_AGENTS + 1))
done

# 2. Commands
printf "${CYAN}--- Commands ---${RESET}\n"
sync_md_files "$TOOLKIT_DIR/commands" "$CLAUDE_DIR/commands" "Commands"

# Count personal commands
PERSONAL_COMMANDS=0
for f in "$CLAUDE_DIR/commands"/*.md; do
    [[ -f "$f" ]] && [[ ! -L "$f" ]] && PERSONAL_COMMANDS=$((PERSONAL_COMMANDS + 1))
done

# 3. Memory-MCP
printf "${CYAN}--- Memory MCP ---${RESET}\n"
sync_memory_mcp
setup_venv

# 4. CLAUDE.md (first-time only)
if [[ -f "$TOOLKIT_DIR/CLAUDE.md.template" ]]; then
    if [[ ! -f "$CLAUDE_DIR/CLAUDE.md" ]]; then
        if $DRY_RUN; then
            info "Would copy CLAUDE.md.template → ~/.claude/CLAUDE.md"
        else
            cp "$TOOLKIT_DIR/CLAUDE.md.template" "$CLAUDE_DIR/CLAUDE.md"
            info "Installed CLAUDE.md from template"
        fi
    else
        skip "  CLAUDE.md exists — not overwriting"
    fi
fi

# 5. Git hook
printf "${CYAN}--- Git Hook ---${RESET}\n"
install_hook

# Summary
echo ""
printf "${CYAN}===================================${RESET}\n"
printf "${GREEN}Summary:${RESET}\n"

BASE_AGENTS=$(ls "$CLAUDE_DIR/agents"/*.md 2>/dev/null | wc -l | tr -d ' ')
BASE_COMMANDS=$(ls "$CLAUDE_DIR/commands"/*.md 2>/dev/null | wc -l | tr -d ' ')

echo "  Agents:   $BASE_AGENTS total ($PERSONAL_AGENTS personal)"
echo "  Commands: $BASE_COMMANDS total ($PERSONAL_COMMANDS personal)"
echo "  Created:  $CREATED  Updated: $UPDATED  Skipped: $SKIPPED  Conflicts: $CONFLICTS"

if [[ $CONFLICTS -gt 0 ]]; then
    echo ""
    warn "  $CONFLICTS file(s) backed up as .personal-backup — review them"
fi

echo ""
info "Done. Run 'git pull' anytime — auto-sync via post-merge hook."
