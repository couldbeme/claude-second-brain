# Migration Guide: Manual Copy → Symlink Install

If you previously installed the toolkit with `cp -r`, this guide migrates you to the symlink-based system.

## Why migrate?

| Before (manual copy) | After (symlinks) |
|----------------------|-------------------|
| `git pull` then manually `cp -r` | `git pull` auto-syncs |
| Installed files drift out of date | Always in sync with repo |
| Personal files mixed with base files | Personal files clearly separated |
| Memory-MCP updates require manual copy | Memory-MCP auto-synced via symlinks |

## Prerequisites

- The toolkit repo cloned locally
- No unsaved personal files in `~/.claude/agents/` or `~/.claude/commands/` that you want to keep (if you do, back them up first)

## Quick migration (recommended)

```bash
cd /path/to/claude-code-team-toolkit
./install.sh --migrate
```

The `--migrate` flag:
1. Snapshots your current `~/.claude/` state (commits if it's a git repo)
2. Removes toolkit-managed files from second-brain git tracking
3. Updates `~/.claude/.gitignore` to ignore symlinked files
4. Deletes stale regular copies (replaced by symlinks)
5. Runs the standard install (creates symlinks)

## Manual migration (if you prefer control)

### Step 1: Backup

```bash
# If ~/.claude/ is a git repo ("second brain")
cd ~/.claude
git add -A
git commit -m "chore: snapshot before toolkit symlink migration"
```

### Step 2: Remove toolkit files from second-brain tracking

```bash
cd ~/.claude
git rm --cached agents/*.md
git rm --cached commands/*.md
git rm --cached memory-mcp/server.py memory-mcp/db.py memory-mcp/embeddings.py \
    memory-mcp/hybrid_search.py memory-mcp/sync.py memory-mcp/requirements.txt
```

`--cached` removes from git tracking but keeps the files on disk.

### Step 3: Update second-brain .gitignore

Add these lines to `~/.claude/.gitignore`:

```gitignore
# Toolkit-managed (symlinks to claude-code-team-toolkit)
agents/*.md
commands/*.md
memory-mcp/*.py
memory-mcp/requirements.txt
```

The second brain continues tracking: `memory/`, `settings.json`, `CLAUDE.md`, and any personal files.

```bash
git add .gitignore
git commit -m "chore: stop tracking toolkit files — now managed via symlinks"
```

### Step 4: Delete stale copies

```bash
rm ~/.claude/agents/*.md
rm ~/.claude/commands/*.md
rm ~/.claude/memory-mcp/server.py ~/.claude/memory-mcp/db.py \
   ~/.claude/memory-mcp/embeddings.py ~/.claude/memory-mcp/hybrid_search.py \
   ~/.claude/memory-mcp/sync.py
```

### Step 5: Run the installer

```bash
cd /path/to/claude-code-team-toolkit
./install.sh
```

### Step 6: Verify

```bash
# Should show symlink arrows
ls -la ~/.claude/agents/architect.md
# architect.md -> /path/to/claude-code-team-toolkit/agents/architect.md

# Memory-MCP should resolve to repo version
ls -la ~/.claude/memory-mcp/server.py
# server.py -> /path/to/claude-code-team-toolkit/memory-mcp/server.py

# Open Claude Code and test
# /guide tour
```

## What's preserved

| Item | Preserved? | Notes |
|------|-----------|-------|
| `~/.claude/memory/memory.db` | Yes | Never touched by installer |
| `~/.claude/settings.json` | Yes | Never touched by installer |
| `~/.claude/CLAUDE.md` | Yes | Never overwritten after first install |
| `~/.claude/memory-mcp/.venv/` | Yes | Venv stays local, only deps updated |
| Personal agents/commands | Yes | Regular files are never touched |

## Rollback

If something goes wrong:

```bash
# Remove all toolkit symlinks, keep personal files
cd /path/to/claude-code-team-toolkit
./uninstall.sh

# Go back to manual copy
cp -r commands/ ~/.claude/commands/
cp -r agents/ ~/.claude/agents/
```
