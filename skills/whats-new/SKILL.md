---
description: Surface new Claude Code platform features (hooks, skills, MCP, slash commands, settings, model defaults, CLI flags) since last local check — uses GitHub Releases as source
argument-hint: Optional flags (e.g., "--since v2.1.100", "--format markdown", "--no-network", "--quiet")
---

# /whats-new — Platform-Update Surfacer

Diffs the latest 20 GitHub releases of `anthropics/claude-code` against a local state file and reports new releases grouped by category. Resolves the `[unverified]` evidence string emitted by `/self-audit`.

The driving question: *what changed in Claude Code since I last looked, and which buckets do those changes fall into?*

No LLM calls. Every parse step is regex / structural. Deterministic — same inputs, same outputs.

## What it surfaces

Releases are split into buckets by regex match on each bullet. Order matters; first match wins:

| Bucket | Trigger keywords (case-insensitive) |
|---|---|
| Hooks | `hook`, `PreCompact`, `PostToolUse`, `UserPromptSubmit`, `SessionStart`, `Stop hook` |
| Skills | `skill`, `SKILL.md` |
| MCP | `mcp server`, `mcp__`, `mcp` |
| Slash Commands | `slash command`, `/<name> command`, `command:` |
| Settings | `settings.json`, `setting:`, `config flag` |
| Model | `opus`, `sonnet`, `haiku`, `claude-{opus,sonnet,haiku}-N`, `model:` |
| CLI | `--<flag>`, `claude --` |
| Misc | unmatched bullets — never dropped |

## Run it

### Standard (text output, fetch + diff)

```bash
~/.claude/memory-mcp/.venv/bin/python3 \
  ~/Dev/claude-second-brain/memory-mcp/whats_new_check.py
```

### JSON output (for scripting / CI)

```bash
~/.claude/memory-mcp/.venv/bin/python3 \
  ~/Dev/claude-second-brain/memory-mcp/whats_new_check.py --format json
```

### Markdown report

```bash
~/.claude/memory-mcp/.venv/bin/python3 \
  ~/Dev/claude-second-brain/memory-mcp/whats_new_check.py --format markdown
```

### Force-list since a specific tag (ignores state)

```bash
~/.claude/memory-mcp/.venv/bin/python3 \
  ~/Dev/claude-second-brain/memory-mcp/whats_new_check.py --since v2.1.100
```

### Offline (replay last cached diff)

```bash
~/.claude/memory-mcp/.venv/bin/python3 \
  ~/Dev/claude-second-brain/memory-mcp/whats_new_check.py --no-network
```

### Quiet mode (suppress output when no new releases)

```bash
~/.claude/memory-mcp/.venv/bin/python3 \
  ~/Dev/claude-second-brain/memory-mcp/whats_new_check.py --quiet
```

## Exit codes

| Code | Meaning |
|---|---|
| `0` | Success — output written, state updated. Includes 304 Not Modified, rate-limited, offline, upstream errors (graceful degradation). |
| `1` | Hard error — corrupt state file, malformed local state JSON. Network failures never produce exit 1. |

## Failure modes (output banners)

| Banner | Meaning | What to do |
|---|---|---|
| `[OFFLINE]` | Network unreachable; replaying cached state | Re-run when online |
| `[RATE-LIMIT]` | GitHub returned 403; rate-limit reset time included | Re-run after reset |
| `[UPSTREAM-ERROR]` | GitHub 5xx or unexpected response shape | Re-run later; persists if GitHub is degraded |
| `[NOT-MODIFIED]` | ETag match — no new releases since last check | None; expected when up-to-date |

## State file

**Path:** `~/.claude/projects/-Users-macbook-Dev/memory/whats_new_state.json`

Carries: `last_checked_at`, `last_checked_version`, `last_etag`, `seen_releases` (FIFO-rotated at 200 entries).

The file is atomically written (`tempfile` + `os.replace`). A corrupt state file is **never** silently overwritten — you'll get a hard exit-1 with the path so you can decide.

## When to use

- Before running `/self-audit` (refreshes the catalog evidence base)
- After a long break — surface what happened in Claude Code while you were away
- Before upgrading the toolkit — see what platform primitives you might want to wire up
- As input to a release-notes blog post or changelog roll-up

## When NOT to use

- To roll back a release — this is read-only
- To inspect one specific release — use `gh release view <tag>` instead
- As a real-time monitor — GitHub Releases are batched, so polling every minute is wasteful (cadence is ~2-3/week)

## Privacy guarantees

- Outbound traffic: a single HTTPS GET to `api.github.com`. No request body, no auth header, no cookies.
- The User-Agent string is `claude-second-brain-whats-new/0.1` — no machine identifier, no email, no path leakage.
- The state file lives entirely on the local machine; nothing is uploaded.
- `--no-network` disables all outbound traffic.

## Implementation

- Module: `~/Dev/claude-second-brain/memory-mcp/whats_new_check.py` (stdlib only — `urllib`, `json`, `re`, `argparse`)
- Tests: `~/Dev/claude-second-brain/memory-mcp/tests/test_whats_new.py` (58 tests, all green)
- Design: `~/Dev/claude-second-brain/docs/WHATS-NEW-DESIGN.md`
- Recon: `~/.claude/projects/-Users-macbook-Dev-claude-second-brain/memory/launch_archive/whats-new-recon-2026-05-06.md`
- Runs in < 1 second on a warm DNS cache.
