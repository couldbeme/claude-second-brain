---
description: Sync markdown auto-memory → sqlite-vec memory.db so /recall finds recent writes (idempotent; runs auto via SessionStart hook if configured)
argument-hint: (none, or "--dry-run" for preview)
---

# /ingest — Markdown Auto-Memory → sqlite Sync

> Closes the layer gap between markdown auto-memory (auto-loads into context) and sqlite memory.db (queryable via `/recall`). After `/ingest`, today's markdown writes become semantically searchable.

## What it does

Walks `~/.claude/projects/<slug>/memory/*.md`, parses YAML frontmatter, maps `type:` field → memory category, content-hash dedups against existing DB rows, inserts new ones.

| Frontmatter `type` | sqlite `category` |
|---|---|
| `user` | `persona` |
| `project` | `context` |
| `feedback` | `pattern` |
| `reference` | `context` |
| `learning` | `learning` |
| (missing) | `context` (default) |

Content hash dedup ensures repeat runs are idempotent.

## Workflow

### Manual invocation

```bash
# Dry-run (preview — default)
~/.claude/memory-mcp/.venv/bin/python3 \
  ~/Dev/claude-second-brain/memory-mcp/ingest_markdown.py

# Apply (writes to DB)
~/.claude/memory-mcp/.venv/bin/python3 \
  ~/Dev/claude-second-brain/memory-mcp/ingest_markdown.py --apply

# Quiet mode (for hooks)
~/.claude/memory-mcp/.venv/bin/python3 \
  ~/Dev/claude-second-brain/memory-mcp/ingest_markdown.py --apply --quiet
```

Report lands at `~/.claude/plans/ingest-dryrun-report.md` (overwritten each run).

### Auto via SessionStart hook (recommended)

In `~/.claude/settings.json`:

```json
"hooks": {
  "SessionStart": [{
    "hooks": [{
      "type": "command",
      "command": "<HOME>/.claude/memory-mcp/.venv/bin/python3 <HOME>/Dev/claude-second-brain/memory-mcp/ingest_markdown.py --apply --quiet"
    }]
  }]
}
```

Silent on success; idempotent on repeat session starts.

## When to use

- After writing new markdown auto-memory files (if the SessionStart hook isn't configured yet)
- Before `/recall` queries when you suspect new memory hasn't synced
- After importing memories from another machine

## When NOT to use

- If memory.db doesn't exist yet — run `bash memory-mcp/setup.sh` first
- If you're mid-flow and the hook should already have fired — it's idempotent, but unnecessary

## Constraints

- **CLAUDE.md rule 9:** the script reads markdown files; if you've already read them this session, the script's read is independent (filesystem read, not Claude's tool — doesn't add to your context)
- **Hash dedup is strict:** any whitespace difference creates a new hash, so reformatting a file → next ingest treats as new content. Acceptable trade-off; preserves full history.
- **`source` field set to `"auto-memory-sync"`** so these rows are distinguishable from manual `/learn` calls or other one-off imports

## Roadmap

- v0.1 (this) — insert-only on hash dedup; updates flagged but not auto-applied (manual review)
- v0.2 — auto-update with the newer-wins policy on hash mismatch
- v0.3 — incremental mode (only scan files modified since last run via timestamp)

## Tests

`memory-mcp/tests/test_ingest_markdown.py` — 13 tests covering type mapping, frontmatter parse, dedup, idempotency, dry-run.
