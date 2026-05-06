---
description: Append-only date-tagged TODO journal — schedule a reminder without ceremony, list overdue items, mark done
argument-hint: <date> <text>  |  list  |  done <id>
---

# /remind — Date-Tagged TODO Journal

> Solves "schedule-without-ceremony": one line in chat creates a durable, dated reminder that surfaces at session start. No cron, no calendar plumbing — just append-only markdown that auto-loads via `MEMORY.md`.

## Storage

Single file: `~/.claude/projects/<slug>/memory/reminders.md`

Each entry:

```
- [open] <hex-id> | <YYYY-MM-DD> | <text>
```

`<hex-id>` is 8 hex characters (random; collision-safe in practice). Status is `[open]` or `[done]`. The file is auto-loaded into context via the `MEMORY.md` index entry, so overdue items surface at session start without an explicit command.

## Workflow

### `/remind <date> <text>` — schedule

Resolve `<date>` to absolute `YYYY-MM-DD`:
- Already absolute (`2026-05-15`) → use as-is.
- Day name (`monday`, `next monday`, `friday`) → resolve to next occurrence from today.
- Relative (`in 2 weeks`, `in 3 days`, `tomorrow`, `next month`) → compute from today.
- Ambiguous → ask once, don't guess.

Generate an 8-character hex id (e.g., via `python3 -c "import secrets; print(secrets.token_hex(4))"` or in-context). Append to `reminders.md`:

```
- [open] a3f7c2d9 | 2026-05-12 | follow up on benchmark plan with the team
```

Confirm in one sentence: `Scheduled: [a3f7c2d9] 2026-05-12 — follow up on benchmark plan with the team`.

### `/remind list` — show open + overdue

Read `reminders.md`, filter to `[open]` entries, sort by date ascending. Render:

```
OVERDUE (2):
  [a3f7c2d9] 2026-04-25 (3 days ago) — follow up on benchmark plan
  [b81f2e07] 2026-04-26 (2 days ago) — re-run /memory lint after schema change

UPCOMING (3):
  [c5a2d18b] 2026-04-30 (in 2 days)  — review SELF-LEARNING-PROPOSAL merge
  [d29ef74c] 2026-05-12 (in 14 days) — check if Anthropic shipped the requested feature
  [e7c0a915] 2026-06-01 (in 34 days) — quarterly memory.db sweep
```

If no open items: emit `No open reminders.` and stop.

### `/remind done <id>` — mark complete

Find the entry whose hex-id starts with `<id>` (prefix match — 4+ chars usually unique). In-place edit the line: replace `[open]` → `[done]`. Append today's date as a trailing tag for audit:

```
- [done] a3f7c2d9 | 2026-05-12 | follow up on benchmark plan with the team | done:2026-04-28
```

Confirm: `Marked done: [a3f7c2d9] follow up on benchmark plan`.

If `<id>` matches multiple entries: list them and ask for a longer prefix.

If `<id>` matches none: report `No open reminder matches '<id>'`.

## Auto-surface at session start

Per `MEMORY.md` index entry, `reminders.md` auto-loads into context. When the file contains `[open]` items with dates ≤ today, surface a one-line nudge before the user's first substantive prompt:

```
2 reminders overdue: [a3f7c2d9] follow up on benchmark plan, [b81f2e07] re-run /memory lint. Run `/remind list` to see all.
```

Don't do this if there are zero overdue items — silent is the right default.

## Constraints

- **Append-only.** Never delete entries. `/remind done` toggles the bracket; the line stays. History is preserved.
- **Hex-id stable.** Once assigned, never reuse. Don't compress, don't reflow.
- **Date resolution is deterministic.** Same input → same output. If a phrase is ambiguous (`next friday` two weekends out?) ask once.
- **Privacy:** `reminders.md` stays local — gitignore'd at the personal layer (the `~/.claude/.gitignore` re-ignore list excludes `reminders.md` if added; double-check before adding sensitive content).
- **No notification side-channels.** This skill never emails, slacks, or pushes. It's a passive journal that surfaces at session start. Active notification is out of scope.

## When to use

- Catching a follow-up the user mentions in passing: "remind me to check this in 2 weeks."
- Self-scheduling re-checks: cron-like patterns, but lightweight. After a flag flip, schedule the cleanup.
- Tracking soak windows: "verify metric X 3 days post-deploy."
- Personal TODOs that need a date but don't deserve a ticket.

## When NOT to use

- Time-of-day-precise reminders (use the OS calendar — this is date-only).
- Team coordination (those go in shared trackers — Linear, GitHub Issues).
- Recurring schedules (this skill is one-shot per entry; for recurring patterns use `cron` or a scheduled agent).
- Sensitive content (encryption-grade secrets, customer data) — this is a plain markdown file in personal scope.

## Roadmap

- v0.1 (this) — manual invocation; date-only; auto-surface at session start
- v0.2 — `/remind snooze <id> <date>` to push an item forward without losing audit trail
- v0.3 — natural-language date parsing for fuzzier inputs ("end of next sprint", "after the launch")
- v0.4 — optional integration with `/whats-new` so Claude Code release-note checks can self-schedule

## Implementation notes

This is a *workflow skill* — the SKILL.md body IS the workflow. Claude reads/writes `reminders.md` directly via the Read/Edit tools; there's no backing script. Compare to `/memory lint` (Python script) and `/context-status` (Python script + JSONL parsing). `/remind` is closer to `/resume` and `/ingest`'s skill flavor: structured prompt engineering against a fixed file.
