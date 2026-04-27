---
description: Health-check pass over the auto-memory + audit-log layers — finds dead path refs, orphan files, broken index links, stale obsolete strings, audit-log schema violations
argument-hint: (none — scans the user's auto-memory by default)
---

# /memory lint — Health-Check Pass

> Concept inspired by [Andrej Karpathy's April 2026 LLM Wiki gist](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) which proposes ingest/query/lint operations over a personal knowledge layer. **This is an independent implementation** for our memory architecture (markdown auto-memory + sqlite + audit-log + frontmatter-typed files). Different layout = different checks.

## What it does

Runs five deterministic, LLM-free checks over `~/.claude/projects/<slug>/memory/`:

| Check | Catches |
|---|---|
| **dead-paths** | `file:line` references in memory files where the path no longer exists |
| **orphan-files** | Topic files in the memory dir that aren't linked from `MEMORY.md` |
| **broken-index** | `MEMORY.md` links pointing at files that no longer exist |
| **stale-patterns** | Configurable list of obsolete strings (`~/Dev/work/`, old repo names, etc.) |
| **audit-log-schema** | `learning_audit.tsv` rows with wrong column count vs the 9-col schema |

Out of scope (v0.1): semantic contradictions, persona drift, auto-fix. Those need an LLM call and arrive in v0.2+.

## Workflow

### 1. Run the lint

```bash
~/.claude/memory-mcp/.venv/bin/python3 \
  ~/Dev/claude-second-brain/memory-mcp/lint_memory.py
```

Default scans `~/.claude/projects/<slug>/memory/` and audit-log at `learning_audit.tsv` in the same dir. Custom paths:

```bash
python3 lint_memory.py --memory-dir /path/to/memory --audit-log /path/to/audit.tsv
```

Optional: custom stale-patterns file (one substring per line, `#` for comments):

```bash
python3 lint_memory.py --patterns ~/.claude/lint-patterns.txt
```

### 2. Review findings

The report groups findings by kind:

```
🔍 memory lint — 3 finding(s) in /Users/.../memory/

## dead-path (1)
  - learning_session_2026-04-27.md: missing /old/path/file.py:42

## stale-pattern (2)
  - feedback_old.md: contains obsolete: '~/Dev/work/'
  - project_legacy.md: contains obsolete: 'claude-code-team-toolkit'
```

### 3. Decide per finding

For each finding, the typical response:

- **dead-path** → either the path is wrong (fix the reference) or the file was renamed/moved (update the reference). Sometimes the memory is stale and the entry should be deleted entirely.
- **orphan-file** → either add an index entry to `MEMORY.md` or delete the file. Don't leave orphans — they don't auto-load.
- **broken-index** → either restore the missing file or remove the broken link from `MEMORY.md`.
- **stale-pattern** → likely a memory written before a rename/migration; update the text or delete.
- **audit-log-schema** → schema drifted. Investigate the writer (`session_flush.py` or manual edit) and reconcile.

### 4. Re-run after fixes

Lint should be idempotent. Re-running after fixes should report `✅ memory layer clean`.

## When to run

- After a repo rename or major refactor (catches the `~/Dev/work/`-style stale paths)
- Before sharing or syncing memory to another machine (catches orphans)
- Periodically (weekly?) — surfaces drift before it accumulates
- Before any release/launch that ships memory artifacts publicly (catches accidental leaks)

## Exit codes

- `0` always (default) — designed not to break CI
- `1` if findings AND `--exit-on-finding` is passed — for strict CI gates

## Implementation notes

- Pure Python, no external dependencies (uses only stdlib `re`, `pathlib`, `argparse`, `dataclasses`)
- Reuses the memory-mcp venv (no new venv to manage)
- All checks are deterministic — no LLM calls, no flakiness
- Tests at `~/Dev/claude-second-brain/memory-mcp/tests/test_lint_memory.py` (13 tests, all green)

## Roadmap

- **v0.2** — semantic contradiction detection (LLM-assisted; flags conflicting claims within 30 days)
- **v0.2** — persona drift detection in `user_profile.md` (Stable Facts vs auto-updated sections)
- **v0.3** — `--fix` mode for safe auto-corrections (broken index links → remove; orphans → prompt)
- **v0.3** — sqlite memory.db lint (different concern, similar shape)

## Attribution

The conceptual seed comes from Karpathy's LLM Wiki gist's three-op model (ingest / query / lint). This implementation is independently written, targets a different memory layout (ours: markdown + sqlite + audit-log; his: raw/ + wiki/ + CLAUDE.md schema), and ships different checks. Concept attribution is included in the module docstring at `memory-mcp/lint_memory.py`.
