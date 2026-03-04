# Troubleshooting

## Installation Issues

| Problem | Cause | Fix |
|---------|-------|-----|
| `install.sh: Permission denied` | Script not executable | `chmod +x install.sh && ./install.sh` |
| `python3: command not found` | Python not installed | Install Python 3.12+ via pyenv or system package manager |
| `pip install sqlite-vec` fails | Missing C compiler or arch mismatch | `pip install --only-binary :all: sqlite-vec` or install Xcode CLT |
| Symlinks not created | Existing files in `~/.claude/commands/` | Delete existing files first, then re-run `install.sh` |

## Command Issues

| Problem | Cause | Fix |
|---------|-------|-----|
| `/command` not recognized | Symlink broken or missing | Re-run `./install.sh` from toolkit directory |
| Command runs but no output | Agent failed silently | Check Claude Code output for error messages |
| `/tdd` skips red phase | Test already passes | Write a test that actually fails first |
| `/verify` shows stale results | Cached test output | Run `pytest --cache-clear` then `/verify` again |

## Memory System Issues

| Problem | Cause | Fix |
|---------|-------|-----|
| `memory_save` returns error | MCP server not configured | Check `~/.claude/settings.json` has `mcpServers.memory` entry |
| `memory_search` returns no results | Empty database or no embeddings | Check with `memory_list` first; run `python sync.py reembed` |
| Search returns irrelevant results | No embeddings (keyword-only mode) | Start LM Studio and run `python sync.py reembed` |
| `sqlite-vec not found` at runtime | Broken venv | `cd ~/.claude/memory-mcp && .venv/bin/pip install -r requirements.txt` |
| LM Studio connection refused | Server not running | `lms server start` — memory system still works without it (keyword search) |
| MCP server won't start | Import error or path issue | Run `.venv/bin/python server.py --health-check` for diagnostics |

## Sync Issues

| Problem | Cause | Fix |
|---------|-------|-----|
| Launchd agent not running | Not loaded or crashed | `launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.claude.sync-memories.plist` |
| Sync runs but nothing commits | No changes to memory.db | Normal — sync only commits when DB has changed |
| Git push fails in sync | SSH key or auth issue | Check `git remote -v` in `~/.claude` and test `git push` manually |
| Import creates duplicates | Timestamp collision | Sync uses newer-wins by timestamp; duplicates mean different content |

## Agent Issues

| Problem | Cause | Fix |
|---------|-------|-----|
| Agent returns empty result | Timeout or tool permission denied | Grant tool permissions when prompted; increase timeout |
| `/team` selects wrong agents | Stack detection mismatch | Provide explicit task context; modify team proposal before confirming |
| `/orchestrate` agents conflict | Same file modified by multiple agents | Orchestrator detects conflicts; choose the better version when prompted |
