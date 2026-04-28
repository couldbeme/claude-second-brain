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

## Security & Portability

The toolkit ships hardened defaults. If you hit one of these, here's the
why and the fix.

### Embedding URL refused — "non-localhost address"

| Symptom | `embeddings.py` raises `ValueError("Refusing remote embedding URL ...")` on `MemoryDB.__init__` or first `embed()` call |
|---|---|
| Cause | `LMS_EMBEDDING_URL` is set to a non-localhost address. Sending memory content to a remote endpoint without explicit consent is treated as silent exfiltration. |
| Fix (local) | Point `LMS_EMBEDDING_URL` at `http://localhost:1234/v1/embeddings` (LM Studio default) or `http://127.0.0.1:...`. |
| Fix (remote, opt-in) | Set `LMS_EMBEDDING_ALLOW_REMOTE=1` to acknowledge the data-egress risk. The system will warn at startup and POST memory content to your remote URL. Use only with services you trust. |

### `visibility must be one of ('personal', 'team', 'public')`

| Symptom | `MemoryDB.save()` raises `ValueError("visibility must be one of ...")` |
|---|---|
| Cause | Caller passed a `visibility` value outside the allowed set. The DB enforces this on save. |
| Fix | Pass one of `personal` / `team` / `public`. Default is `personal`; sensitive categories like `persona` and `user_model` are forced to `personal` regardless. |

### Hook config doesn't expand `<HOME>` or `<slug>`

| Symptom | `SessionStart` or `PreCompact` hook fails to fire after copy-pasting from `docs/RESUME.md` or `skills/ingest/SKILL.md` |
|---|---|
| Cause | The toolkit docs use `<HOME>` (your absolute home path) and `<slug>` (Claude Code's per-project memory-dir slug — your absolute cwd with `/` replaced by `-`) as portability placeholders. Claude Code's hook runner does NOT expand placeholders — paths must be literal. |
| Fix | Replace `<HOME>` with the output of `echo $HOME` (e.g. `/Users/yourname` on macOS, `/home/yourname` on Linux). Replace `<slug>` with the output of `pwd | sed 's:/:-:g'` for your active project directory. |

### MCP version mismatch / Pydantic / anyio errors at install

| Symptom | `pip install -r memory-mcp/requirements.txt` warns about resolver conflicts; runtime errors mention `mcp.server.lowlevel`, `pydantic.BaseModel`, or anyio task groups |
|---|---|
| Cause | The toolkit pins `mcp>=1.23.0`, `pydantic>=2.4.0`, `anyio>=4.4.0` — older versions have known issues (DNS rebinding in mcp <1.23, ReDoS in pydantic <2.4, race in anyio <4.4). |
| Fix | `cd memory-mcp && pip install --upgrade -r requirements.txt`. If a conflicting version is pinned upstream, upgrade or pin in your project requirements. |

### `<slug>` placeholder breaks shell `open` commands

| Symptom | `open ~/.claude/projects/<slug>/memory/launch_archive/...` returns `no such file or directory: slug` |
|---|---|
| Cause | The literal string `<slug>` is a documentation placeholder, not a shell variable. The shell tries to interpret `<` as redirection. |
| Fix | Substitute the literal slug: run `pwd | sed 's:/:-:g'` to get yours, or for the toolkit's own project-memory dir, expand `<slug>` to whatever your active project's encoded path is. The placeholder is correct in code (where it's runtime-derived) but breaks in interactive shell use. |
