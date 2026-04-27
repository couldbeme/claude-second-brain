#!/usr/bin/env bash
# setup-new-machine.sh -- Full setup of Claude Code Toolkit + Second Brain on a fresh machine
#
# This script is MEANT TO BE READ, not blindly executed.
# Copy it to the new machine and run it step by step, or run the whole thing.
#
# Prerequisites:
#   1. Git installed
#   2. Python 3.10+ installed
#   3. SSH key added to GitHub (for git clone)
#   4. Claude Code CLI installed (optional -- can install after)
#
# Usage:
#   bash setup-new-machine.sh              # Interactive (pauses between steps)
#   bash setup-new-machine.sh --auto       # Non-interactive (no pauses)
#   bash setup-new-machine.sh --check      # Dry run: check prerequisites only
#
# Git host:
#   Defaults to github.com (single-account machine).
#   For multi-account SSH setups, set GIT_HOST before running:
#     GIT_HOST=github.com-personal bash setup-new-machine.sh
#
# What it does (in order):
#   1. Verifies prerequisites (git, python, claude)
#   2. Sets up SSH config for custom GIT_HOST (only if GIT_HOST != github.com)
#   3. Clones the second brain as ~/.claude/
#   4. Clones the toolkit repo to ~/Dev/claude-second-brain/
#   5. Runs the toolkit installer (symlinks commands/agents/MCP into ~/.claude/)
#   6. Fixes absolute paths in settings.json for this machine
#   7. Creates the memory directory + verifies the MCP server
#   8. Prints LM Studio setup instructions
#   9. Runs the verification checklist

set -euo pipefail

# --- Config ---
# GIT_HOST: override for multi-account SSH setups (e.g. github.com-personal)
GIT_HOST="${GIT_HOST:-github.com}"
SECOND_BRAIN_REPO="git@${GIT_HOST}:couldbeme/second-brain.git"
TOOLKIT_REPO="git@${GIT_HOST}:couldbeme/claude-second-brain.git"
CLAUDE_DIR="$HOME/.claude"
TOOLKIT_DIR="$HOME/Dev/claude-second-brain"
AUTO=false
CHECK_ONLY=false

case "${1:-}" in
    --auto)  AUTO=true ;;
    --check) CHECK_ONLY=true ;;
esac

# --- Colors ---
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
RESET='\033[0m'

ok()   { printf "${GREEN}[OK]${RESET}    %s\n" "$1"; }
fail() { printf "${RED}[FAIL]${RESET}  %s\n" "$1"; }
warn() { printf "${YELLOW}[WARN]${RESET}  %s\n" "$1"; }
info() { printf "${CYAN}[INFO]${RESET}  %s\n" "$1"; }
step() { printf "\n${BOLD}${CYAN}=== Step %s: %s ===${RESET}\n\n" "$1" "$2"; }

pause() {
    if ! $AUTO && ! $CHECK_ONLY; then
        printf "\n${YELLOW}Press Enter to continue (Ctrl+C to abort)...${RESET}"
        read -r
    fi
}

# =============================================================================
# Step 0: Check prerequisites
# =============================================================================
step "0" "Checking prerequisites"

PREREQS_OK=true

# Git
if command -v git &>/dev/null; then
    ok "git $(git --version | cut -d' ' -f3)"
else
    fail "git not found -- install with: brew install git (macOS) or apt install git (Linux)"
    PREREQS_OK=false
fi

# Python
if command -v python3 &>/dev/null; then
    PY_VERSION=$(python3 --version | cut -d' ' -f2)
    PY_MAJOR=$(echo "$PY_VERSION" | cut -d. -f1)
    PY_MINOR=$(echo "$PY_VERSION" | cut -d. -f2)
    if [[ "$PY_MAJOR" -ge 3 ]] && [[ "$PY_MINOR" -ge 10 ]]; then
        ok "Python $PY_VERSION"
    else
        fail "Python $PY_VERSION is too old (need 3.10+)"
        PREREQS_OK=false
    fi
else
    fail "python3 not found -- install Python 3.10+"
    PREREQS_OK=false
fi

# SSH key for GitHub (soft check -- warn only, don't block)
# Note: ssh -T always returns exit code 1 for GitHub (no shell access).
# We check stderr output for the success message instead.
SSH_OUTPUT=$(ssh -o ConnectTimeout=5 -T "git@${GIT_HOST}" 2>&1 || true)
if echo "$SSH_OUTPUT" | grep -qi "successfully authenticated"; then
    SSH_USER=$(echo "$SSH_OUTPUT" | grep -oi "Hi [^ !]*" | cut -d' ' -f2)
    ok "SSH auth to ${GIT_HOST} (${SSH_USER:-unknown})"
else
    warn "SSH auth to ${GIT_HOST} could not be verified"
    echo "    If git clone fails later, you'll need an SSH key for GitHub."
    echo "    Generate: ssh-keygen -t ed25519"
    echo "    Add to:   https://github.com/settings/keys"
    if [[ "$GIT_HOST" != "github.com" ]]; then
        echo "    SSH config: add Host $GIT_HOST entry in ~/.ssh/config"
    fi
    echo ""
fi

# Claude Code CLI
if command -v claude &>/dev/null; then
    ok "Claude Code CLI installed"
else
    warn "Claude Code CLI not found -- install with: npm install -g @anthropic-ai/claude-code"
    echo "    (you can install it later, but won't be able to test at the end)"
fi

# Check if ~/.claude already exists
if [[ -d "$CLAUDE_DIR" ]]; then
    if [[ -d "$CLAUDE_DIR/.git" ]]; then
        warn "~/.claude/ already exists and is a git repo (second brain already cloned?)"
    else
        warn "~/.claude/ already exists but is NOT a git repo"
        echo "    The script will skip cloning the second brain."
        echo "    If you want a fresh install, rename it first: mv ~/.claude ~/.claude.bak"
    fi
fi

# Check if toolkit dir already exists
if [[ -d "$TOOLKIT_DIR" ]]; then
    warn "$TOOLKIT_DIR already exists (toolkit already cloned?)"
fi

if ! $PREREQS_OK; then
    echo ""
    fail "Prerequisites not met. Fix the issues above and re-run."
    exit 1
fi

if $CHECK_ONLY; then
    echo ""
    ok "All prerequisites met. Run without --check to proceed."
    exit 0
fi

echo ""
ok "All prerequisites met."
pause

# =============================================================================
# Step 1: SSH config (only for multi-account setups)
# =============================================================================
if [[ "$GIT_HOST" != "github.com" ]]; then
    step "1" "SSH config for $GIT_HOST"

    SSH_CONFIG="$HOME/.ssh/config"

    if grep -q "Host ${GIT_HOST}" "$SSH_CONFIG" 2>/dev/null; then
        ok "SSH config for ${GIT_HOST} already exists"
    else
        info "Adding SSH config for ${GIT_HOST}..."
        mkdir -p "$HOME/.ssh"
        cat >> "$SSH_CONFIG" << EOF

# GitHub alias (added by setup-new-machine.sh)
Host ${GIT_HOST}
    HostName github.com
    User git
    IdentityFile ~/.ssh/id_personal
EOF
        chmod 600 "$SSH_CONFIG"
        ok "Added SSH config for ${GIT_HOST}"
        echo ""
        warn "Make sure ~/.ssh/id_personal exists and is added to GitHub."
        echo "    Generate:  ssh-keygen -t ed25519 -f ~/.ssh/id_personal"
        echo "    Add to GH: https://github.com/settings/keys"
    fi

    pause
else
    info "Using github.com directly (single-account setup -- skipping SSH config)"
fi

# =============================================================================
# Step 2: Clone the second brain as ~/.claude/
# =============================================================================
step "2" "Clone second brain to ~/.claude/"

if [[ -d "$CLAUDE_DIR/.git" ]]; then
    ok "Second brain already cloned at $CLAUDE_DIR"
    info "Pulling latest..."
    git -C "$CLAUDE_DIR" pull --ff-only 2>/dev/null || warn "Pull failed (maybe uncommitted changes)"
else
    if [[ -d "$CLAUDE_DIR" ]]; then
        info "~/.claude/ exists but isn't a git repo -- backing up..."
        mv "$CLAUDE_DIR" "${CLAUDE_DIR}.pre-setup-backup"
        warn "Backed up to ${CLAUDE_DIR}.pre-setup-backup"
    fi

    info "Cloning second brain..."
    git clone "$SECOND_BRAIN_REPO" "$CLAUDE_DIR"
    ok "Second brain cloned to $CLAUDE_DIR"
fi

# Verify key files exist
for f in CLAUDE.md settings.json SYSTEM.md; do
    if [[ -f "$CLAUDE_DIR/$f" ]]; then
        ok "  $f exists"
    else
        warn "  $f not found (may need to be created)"
    fi
done

pause

# =============================================================================
# Step 3: Clone the toolkit repo
# =============================================================================
step "3" "Clone toolkit repo"

mkdir -p "$(dirname "$TOOLKIT_DIR")"

if [[ -d "$TOOLKIT_DIR/.git" ]]; then
    ok "Toolkit already cloned at $TOOLKIT_DIR"
    info "Pulling latest..."
    git -C "$TOOLKIT_DIR" pull --ff-only 2>/dev/null || warn "Pull failed"
else
    info "Cloning toolkit..."
    git clone "$TOOLKIT_REPO" "$TOOLKIT_DIR"
    ok "Toolkit cloned to $TOOLKIT_DIR"
fi

pause

# =============================================================================
# Step 4: Run the toolkit installer
# =============================================================================
step "4" "Run toolkit installer (symlinks + venv)"

if [[ -x "$TOOLKIT_DIR/install.sh" ]]; then
    bash "$TOOLKIT_DIR/install.sh"
    ok "Toolkit installer completed"
else
    fail "install.sh not found or not executable at $TOOLKIT_DIR/install.sh"
    exit 1
fi

pause

# =============================================================================
# Step 5: Fix absolute paths in settings.json
# =============================================================================
step "5" "Fix paths in settings.json for this machine"

SETTINGS_FILE="$CLAUDE_DIR/settings.json"

if [[ -f "$SETTINGS_FILE" ]]; then
    # Detect the old home path from the file
    OLD_HOME=$(python3 -c "
import json, re
with open('$SETTINGS_FILE') as f:
    data = f.read()
match = re.search(r'(/(?:Users|home)/[^/]+)', data)
if match:
    print(match.group(1))
" 2>/dev/null || true)

    if [[ -n "$OLD_HOME" ]] && [[ "$OLD_HOME" != "$HOME" ]]; then
        info "Replacing $OLD_HOME with $HOME in settings.json..."
        if [[ "$(uname)" == "Darwin" ]]; then
            sed -i '' "s|${OLD_HOME}|${HOME}|g" "$SETTINGS_FILE"
        else
            sed -i "s|${OLD_HOME}|${HOME}|g" "$SETTINGS_FILE"
        fi
        ok "Paths updated"
    else
        ok "Paths already correct (home: $HOME)"
    fi

    # Verify the file is valid JSON
    if python3 -m json.tool "$SETTINGS_FILE" > /dev/null 2>&1; then
        ok "settings.json is valid JSON"
    else
        fail "settings.json is NOT valid JSON -- fix it manually"
    fi

    # Show the MCP config for review
    echo ""
    info "Current MCP config:"
    python3 -c "
import json
with open('$SETTINGS_FILE') as f:
    data = json.load(f)
mcp = data.get('mcpServers', {}).get('memory', {})
print(f\"  command: {mcp.get('command', 'NOT SET')}\")
print(f\"  args:    {mcp.get('args', ['NOT SET'])}\")
env = mcp.get('env', {})
for k, v in env.items():
    print(f\"  {k}: {v}\")
" 2>/dev/null || warn "Could not parse settings.json"
else
    warn "settings.json not found -- will be created from template"
    # Create from template
    if [[ -f "$TOOLKIT_DIR/memory-mcp/settings.json.template" ]]; then
        cp "$TOOLKIT_DIR/memory-mcp/settings.json.template" "$SETTINGS_FILE"
        if [[ "$(uname)" == "Darwin" ]]; then
            sed -i '' "s|REPLACE_WITH_VENV_PATH|${CLAUDE_DIR}/memory-mcp|g" "$SETTINGS_FILE"
            sed -i '' "s|REPLACE_WITH_MEMORY_MCP_PATH|${CLAUDE_DIR}/memory-mcp|g" "$SETTINGS_FILE"
            sed -i '' "s|REPLACE_WITH_HOME|${HOME}|g" "$SETTINGS_FILE"
        else
            sed -i "s|REPLACE_WITH_VENV_PATH|${CLAUDE_DIR}/memory-mcp|g" "$SETTINGS_FILE"
            sed -i "s|REPLACE_WITH_MEMORY_MCP_PATH|${CLAUDE_DIR}/memory-mcp|g" "$SETTINGS_FILE"
            sed -i "s|REPLACE_WITH_HOME|${HOME}|g" "$SETTINGS_FILE"
        fi
        ok "Created settings.json from template with correct paths"
    fi
fi

pause

# =============================================================================
# Step 6: Set up memory directory + verify MCP server
# =============================================================================
step "6" "Memory system setup"

mkdir -p "$CLAUDE_DIR/memory"
ok "Memory directory exists: $CLAUDE_DIR/memory/"

if [[ -f "$CLAUDE_DIR/memory/memory.db" ]]; then
    DB_SIZE=$(du -h "$CLAUDE_DIR/memory/memory.db" | cut -f1)
    ok "memory.db exists ($DB_SIZE)"
else
    warn "memory.db not found -- will be created on first use"
fi

# Verify MCP server
VENV_PYTHON="$CLAUDE_DIR/memory-mcp/.venv/bin/python3"
SERVER_PY="$CLAUDE_DIR/memory-mcp/server.py"

if [[ -x "$VENV_PYTHON" ]] && [[ -f "$SERVER_PY" ]]; then
    info "Testing MCP server health..."
    if "$VENV_PYTHON" "$SERVER_PY" --health-check 2>/dev/null; then
        ok "MCP server health check passed"
    else
        fail "MCP server health check failed"
        echo "    Try: cd $CLAUDE_DIR/memory-mcp && source .venv/bin/activate && pip install -r requirements.txt"
    fi
else
    fail "MCP venv or server.py not found"
    echo "    venv: $VENV_PYTHON"
    echo "    server: $SERVER_PY"
fi

pause

# =============================================================================
# Step 7: LM Studio setup instructions
# =============================================================================
step "7" "LM Studio (for semantic search)"

echo "LM Studio provides local embeddings for semantic memory search."
echo "Without it, the memory system still works (keyword-only search)."
echo ""
echo "Setup:"
echo "  1. Download from https://lmstudio.ai"
echo "  2. Open LM Studio"
echo "  3. Search tab: search for 'nomic-embed-text-v1.5'"
echo "  4. Download: nomic-ai/nomic-embed-text-v1.5-GGUF"
echo "  5. Developer tab: load the model, start the server"
echo ""
echo "Verify:"
echo "  curl http://localhost:1234/v1/models"
echo ""

# Check if LM Studio is already running
if curl -s http://localhost:1234/v1/models > /dev/null 2>&1; then
    ok "LM Studio is running and responding"
else
    info "LM Studio not running (start it when you need semantic search)"
fi

pause

# =============================================================================
# Step 8: Verification checklist
# =============================================================================
step "8" "Final verification"

PASS=0
TOTAL=0

check() {
    TOTAL=$((TOTAL + 1))
    if eval "$2" > /dev/null 2>&1; then
        ok "$1"
        PASS=$((PASS + 1))
    else
        fail "$1"
    fi
}

check "CLAUDE.md exists"          "[[ -f $CLAUDE_DIR/CLAUDE.md ]]"
check "settings.json valid"       "python3 -m json.tool $CLAUDE_DIR/settings.json"
check "SYSTEM.md exists"          "[[ -f $CLAUDE_DIR/SYSTEM.md ]]"
check "Commands installed"        "[[ \$(ls $CLAUDE_DIR/commands/*.md 2>/dev/null | wc -l) -ge 20 ]]"
check "Agents installed"          "[[ \$(ls $CLAUDE_DIR/agents/*.md 2>/dev/null | wc -l) -ge 15 ]]"
check "Commands are symlinks"     "[[ -L $CLAUDE_DIR/commands/tdd.md ]]"
check "Agents are symlinks"       "[[ -L $CLAUDE_DIR/agents/architect.md ]]"
check "MCP venv exists"           "[[ -d $CLAUDE_DIR/memory-mcp/.venv ]]"
check "MCP server.py exists"      "[[ -f $CLAUDE_DIR/memory-mcp/server.py ]]"
check "MCP health check"          "$VENV_PYTHON $SERVER_PY --health-check"
check "Memory directory exists"   "[[ -d $CLAUDE_DIR/memory ]]"
check "Second brain git remote"   "git -C $CLAUDE_DIR remote -v | grep -q couldbeme"
check "Toolkit git remote"        "git -C $TOOLKIT_DIR remote -v | grep -q couldbeme"

echo ""
printf "${BOLD}Result: $PASS/$TOTAL checks passed${RESET}\n"

if [[ $PASS -eq $TOTAL ]]; then
    echo ""
    printf "${GREEN}${BOLD}Setup complete!${RESET}\n"
    echo ""
    echo "Next steps:"
    echo "  1. Start LM Studio and load nomic-embed-text-v1.5 (for semantic search)"
    echo "  2. Open Claude Code: claude"
    echo "  3. Try: /guide tour"
    echo "  4. Try: /status"
    echo ""
    echo "To sync memories from another machine:"
    echo "  On old machine:  cd ~/.claude/memory-mcp && .venv/bin/python sync.py export --pretty"
    echo "  Transfer:        scp old:~/.claude/memory/memories-export.json ~/.claude/memory/"
    echo "  On this machine: cd ~/.claude/memory-mcp && .venv/bin/python sync.py import"
    echo ""
else
    echo ""
    warn "Some checks failed. Review the output above and fix issues."
fi
