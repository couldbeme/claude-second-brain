---
description: Re-orient after compact or new session — reads checkpoint + most recent pre-compact snapshot + recent commits + auto-memory state, produces a 1-page summary of where we left off
argument-hint: (none — auto-detects state)
---

# /resume — Post-Compact Re-Orientation

> Use first whenever you (re)open Claude Code on this project. Three commands in order: `/resume` → check; if anything feels wrong → `/memory lint` → `/context-status`.

## What it does

Read these files in order, then synthesize a 1-page summary:

1. **`~/.claude/checkpoint.md`** — manually-written dense state from the prior session (full read; primary anchor)
2. **Most recent `~/.claude/projects/<slug>/memory/context_pre_compact_*.md`** if any (sort by mtime; read the latest) — auto-snapshot from PreCompact hook with token usage + plan-file pointers; also read **`continuity_pre_compact_*.md`** from the same dir (sort by mtime; read the latest) — content-rich snapshot with decisions, open threads, in-flight state, and voice signals written by `continuity_dump.py`
3. **`git -C ~/.claude log --oneline -8`** — recent second-brain commits (rules + memories)
4. **`git -C ~/Dev/claude-second-brain log --oneline -10`** — recent toolkit commits (code + docs)
5. **`git -C ~/.claude branch --show-current` + `git -C ~/Dev/claude-second-brain branch --show-current`** — confirm branches match expectations
6. **`/memory lint` invocation** — surface any drift since last lint run

## Output shape

Produce a single response with these sections (terse — match the user's preferred style; no preamble):

```markdown
## Resume — <date>

### Where we left off
<1-2 sentences from checkpoint's "Current task" + "Next Step">

### Just shipped (last session)
- <bullet from recent commits>
- <bullet>
- <bullet>

### Currently in flight
<from checkpoint's "Currently working" or "Pending" sections; or "nothing" if clean>

### Open decisions / blockers
<from checkpoint's "Decisions" or "Open questions"; explicit list>

### Recent context (token usage)
<from most recent context_pre_compact_*.md if exists; else "no prior compact this session">

### Memory state
<from /memory lint output: clean | N findings — <category breakdown>>

### Recommended next move
<single sentence — what's the obvious next action?>
```

## When to use

- **First action of every new Claude Code session** on this project
- **Immediately after `/compact`** fires (manually or auto-trigger)
- **Returning after a break** of more than a few hours
- **Anytime continuity feels off** — Claude responses missing earlier-session context

## When NOT to use

- Mid-flow on a single coherent task — disrupts focus for no gain
- Within the same uninterrupted session — the context is already loaded
- If `checkpoint.md` is older than 7 days — it's likely stale; ask user to confirm scope before relying on it

## Constraints

- **Per CLAUDE.md rule 9 (NEVER re-read unchanged files):** if any of the above files were already read in *this* session, reference the earlier read instead. Only Read files genuinely new to this conversation.
- **Per /memory lint pattern:** if lint surfaces stale-pattern hits (intentional historical context references in `MEMORY.md` / `user_profile.md`), note them as expected; don't flag as drift.
- **Privacy:** never share checkpoint content beyond this session. Stays local.

## Roadmap

- v0.1 (this) — manual invocation; reads files; produces summary
- v0.2 — integrates `/whats-new` output (any platform updates since last session)
- v0.3 — diff-aware summary (only surface what changed since last `/resume`)

## Implementation notes

This is a *workflow skill* (no backing script). The skill body IS the workflow. Claude reads files per the list above and produces the summary structure. Compare to `/memory lint` and `/context-status` which both have backing Python scripts; `/resume` is pure prompt engineering applied to a fixed file set.
