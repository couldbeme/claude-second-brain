# Skills

_Auto-generated from `skills/*/SKILL.md` frontmatter. Edit the source, not this file._

- **`context-status`** — Show current Claude Code context-window usage as a percentage and recommend whether to /context-save or /compact now (manual companion to the built-in /context command + the PreCompact auto-trigger)
- **`ingest`** — Sync markdown auto-memory → sqlite-vec memory.db so /recall finds recent writes (idempotent; runs auto via SessionStart hook if configured)
- **`iterate`** — Modify-one-file under a wall-clock budget — single-agent loop edits target_file, runs eval_command, keeps the best version. Karpathy `autoresearch` shape retargeted for prose-agent and code-agent work. Output is best version at T+budget, not "the answer."
- **`karpathy-bar`** — Run the Karpathy-grade quality bar against an artifact (README, doc, skill, module, commit diff) — every claim has a runnable proof; no marketing fluff; ≥20% cut on second draft. Catches inaccuracies before commit.
- **`memory-lint`** — Health-check pass over the auto-memory + audit-log layers — finds dead path refs, orphan files, broken index links, stale obsolete strings, audit-log schema violations
- **`pain-scout`** — >
- **`publish-safety`** — >
- **`reflect`** — End-of-session retrospective through a single persona-bound lens. Reads session_bridge.md and outputs three blocks - what shifted, what stayed wrong, one move forward. Honest when there is not enough substrate to say anything.
- **`remind`** — Append-only date-tagged TODO journal — schedule a reminder without ceremony, list overdue items, mark done
- **`resume`** — Re-orient after compact or new session — reads checkpoint + most recent pre-compact snapshot + recent commits + auto-memory state, produces a 1-page summary of where we left off
- **`self-audit`** — Deterministic toolkit health checker — finds underused Claude Code platform features in commands/, agents/, skills/, and CLAUDE.md.template
- **`startup-advisor`** — >
- **`tribunal`** — Multi-lens decision against a hard binary — bind N personas as lenses, each issues a structured verdict (or refusal), output is the named disagreement (majority + dissents + unresolved residue), not consensus. The operator owns the final move.
- **`whats-new`** — Surface new Claude Code platform features (hooks, skills, MCP, slash commands, settings, model defaults, CLI flags) since last local check — uses GitHub Releases as source
