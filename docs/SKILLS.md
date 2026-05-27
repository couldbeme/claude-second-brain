# Skills

_Auto-generated from `skills/*/SKILL.md` frontmatter. Edit the source, not this file._

- **`context-status`** — Show current Claude Code context-window usage as a percentage and recommend whether to /context-save or /compact now (manual companion to the built-in /context command + the PreCompact auto-trigger)
- **`ingest`** — Sync markdown auto-memory → sqlite-vec memory.db so /recall finds recent writes (idempotent; runs auto via SessionStart hook if configured)
- **`memory-lint`** — Health-check pass over the auto-memory + audit-log layers — finds dead path refs, orphan files, broken index links, stale obsolete strings, audit-log schema violations
- **`remind`** — Append-only date-tagged TODO journal — schedule a reminder without ceremony, list overdue items, mark done
- **`resume`** — Re-orient after compact or new session — reads checkpoint + most recent pre-compact snapshot + recent commits + auto-memory state, produces a 1-page summary of where we left off
- **`self-audit`** — Deterministic toolkit health checker — finds underused Claude Code platform features in commands/, agents/, skills/, and CLAUDE.md.template
- **`whats-new`** — Surface new Claude Code platform features (hooks, skills, MCP, slash commands, settings, model defaults, CLI flags) since last local check — uses GitHub Releases as source
