# Continuity + /resume — Hands-On Demo

## What continuity is and why it matters

Claude Code's `/compact` command compresses context to reclaim token budget.
It keeps the compressed summary but loses structural session state: the
decisions you made, the tasks mid-flight, the open threads you meant to
return to. A fresh session after `/compact` is oriented — it knows the
summary — but not contextualized. It doesn't know you rejected two
alternatives before landing on the current approach, or that the migration
job was still running.

The continuity layer fixes this. During a session, Claude appends structural
entries to a `session_bridge.md` journal (decisions, in-flight tasks, open
threads). When `/compact` fires, a PreCompact hook reads that journal and
writes a `continuity_pre_compact_<session_id>.md` snapshot to your per-project
memory directory. The next session's `/resume` reads the snapshot and
re-orients in under 60 seconds — not just "what the project is" but "where
we were and why."

---

## Pre-flight

You need Step 6 of [SETUP-MEMORY.md](../SETUP-MEMORY.md) complete:

- PreCompact hook registered (Step 6a) — verify: `grep -A 6 PreCompact ~/.claude/settings.json`
- Bridge journal rule in `~/.claude/CLAUDE.md` (Step 6b) — tells Claude when to log entries
- Privacy gitignore lines added (Step 6c) — keeps the journal out of backups

If those three checks pass, continue.

---

## Session 1 — Working on a feature, building the journal

You're adding a background job system to a web app. The session proceeds
and structural events fire.

**Event 1 — Architecture decision lands:**

Claude runs internally:

```bash
<your-toolkit-path>/memory-mcp/.venv/bin/python3 \
  <your-toolkit-path>/memory-mcp/bridge_append.py DECISION \
  "Use Celery + Redis for background jobs | WHY: already have Redis for caching, Celery has better retry semantics than RQ | REJECTED: RQ (simpler but no beat scheduler), in-process threading (no retry)"
```

**Event 2 — Agent dispatch:**

```bash
<your-toolkit-path>/memory-mcp/.venv/bin/python3 \
  <your-toolkit-path>/memory-mcp/bridge_append.py INFLIGHT \
  "task=implement background job system | step=tdd-agent writing send_email task | next=celery beat config"
```

**Event 3 — Unresolved branch flagged:**

```bash
<your-toolkit-path>/memory-mcp/.venv/bin/python3 \
  <your-toolkit-path>/memory-mcp/bridge_append.py THREAD-OPEN \
  "a1b2c3d4 | Celery worker autoscaling: how many workers in prod? Needs infra input before config lands"
```

**The `session_bridge.md` after these three events** — flat append-only log, one entry per line:

```
[2026-04-28T14:23:11Z] [DECISION] Use Celery + Redis for background jobs | WHY: already have Redis for caching, Celery has better retry semantics than RQ | REJECTED: RQ (simpler but no beat scheduler), in-process threading (no retry)
[2026-04-28T14:31:05Z] [INFLIGHT] task=implement background job system | step=tdd-agent writing send_email task | next=celery beat config
[2026-04-28T14:44:52Z] [THREAD-OPEN] a1b2c3d4 | Celery worker autoscaling: how many workers in prod? Needs infra input before config lands
```

Each entry is one line, prefixed with an ISO-8601 UTC timestamp and the type tag in brackets. Payloads are structural metadata only — never message body. The CLI caps entries at 500 chars and strips newlines as defense-in-depth.

---

## `/compact` fires

Context is getting heavy. You run `/compact` (or Claude triggers it
automatically). The PreCompact hook fires before compression and reads the
bridge journal.

The hook writes `continuity_pre_compact_<session_id>.md` to your per-project
memory directory (`~/.claude/projects/<slug>/memory/`):

```markdown
# Continuity Snapshot — 2026-04-28T15:02:33Z

## Session context
Project: my-web-app
Captured from: session_bridge.md (3 entries)

## Decisions
- **Celery + Redis for background jobs** — chose over RQ (no beat scheduler)
  and in-process threading (no retry). Redis already in use for caching.

## In-flight tasks
- Background job system: tdd-agent was writing `send_email` task.
  Next step: Celery beat config.

## Open threads
- [a1b2c3d4] Celery worker autoscaling: prod worker count unknown.
  Needs infra input before config can land. UNRESOLVED.

## What to do on /resume
1. Check tdd-agent output for send_email task (should be done or mid-write).
2. Continue with Celery beat config.
3. Ping infra team about [a1b2c3d4] before merging the config.
```

The snapshot is written once, atomically, at compaction time. It does not
depend on the compressed context summary — it reads the raw journal entries
the model appended during the session.

---

## Session 2 — Fresh session, `/resume`

New Claude Code session, new context window. The project context summary is
loaded (from `/compact`). Now run:

```
/resume
```

Claude reads the latest `continuity_pre_compact_*.md` from the per-project
memory directory and outputs:

```
Resuming from continuity snapshot (2026-04-28T15:02:33Z)
=========================================================

Where we were:
  Implementing a background job system using Celery + Redis.
  tdd-agent was mid-write on the send_email task.
  Next step: Celery beat config.

Decisions locked:
  - Celery + Redis (not RQ, not in-process threading). Decision made.
    Don't relitigate unless new constraints emerge.

Open threads (1 unresolved):
  - [a1b2c3d4] Celery worker autoscaling — prod count unknown.
    Needs infra input. Block the config merge until this is resolved.

Recommend: confirm tdd-agent output for send_email, then continue with
Celery beat config. Ping infra about autoscaling before merging.
```

You didn't re-explain the decision history. You didn't remember which
alternatives were rejected. You didn't manually track what was mid-flight.
The continuity layer did it.

---

## Try it yourself — 5-step walkthrough

**Step 1.** Open Claude Code in any project. Confirm Step 6 pre-flight
(see above).

**Step 2.** Start a session and make a non-trivial decision. Claude will
log it automatically when the bridge rule fires. To trigger manually:

```bash
<your-toolkit-path>/memory-mcp/.venv/bin/python3 \
  <your-toolkit-path>/memory-mcp/bridge_append.py DECISION \
  "Chose PostgreSQL over MySQL | WHY: JSONB support | REJECTED: MySQL (no JSONB)"
```

**Step 3.** Run `/compact`:

```
/compact
```

**Step 4.** Verify the snapshot was written:

```bash
ls ~/.claude/projects/<slug>/memory/continuity_pre_compact_*.md
```

You should see one file per compaction event.

**Step 5.** Start a new session in the same project and run:

```
/resume
```

The output should include the decision from Step 2, any in-flight tasks,
and any open threads — without you providing that context manually.

---

## What the bridge CLI accepts

| Type | Fire when | Payload format |
|---|---|---|
**Manual triggers** — Claude calls these via the CLI as events fire:

| Type | Fire when | Payload format |
|---|---|---|
| `DECISION` | A non-trivial decision lands | `<text> \| WHY: <rationale> \| REJECTED: <alt>` |
| `INFLIGHT` | Agent dispatch or major phase transition | `task=<text> \| step=<text> \| next=<text>` |
| `THREAD-OPEN` | Flag an unresolved branch | `<8-hex-id> \| <description>` |
| `THREAD-CLOSE` | Branch resolves | `<8-hex-id>` |

**Auto-fire-only** (do not invoke manually): `VOICE` and `PERSONA` will fire deterministically from a UserPromptSubmit hook in a future toolkit phase. Both types are valid in the journal regex but should only be written by the auto-detection path, not by Claude calling the CLI.

The `bridge_append.py` module docstring (`memory-mcp/bridge_append.py:1-16`)
has the full type list and exit code reference.

For setup details, see [SETUP-MEMORY.md](../SETUP-MEMORY.md) Step 6.
