---
description: View, prioritize, and manage the captured ideas backlog
argument-hint: "pop | done <id> | (blank for list)"
---

# Ideas -- Manage the Ideas Backlog

Surface and manage the ideas backlog without disrupting work.

## Input

Subcommand: $ARGUMENTS

Valid forms:
- `/ideas` — list all entries, most recent first
- `/ideas pop` — surface highest-priority open idea
- `/ideas done <id>` — mark one idea complete by hex ID

## Backlog File

`~/.claude/projects/<slug>/memory/ideas-backlog.md`

If the file does not exist: reply "No ideas captured yet. Use /idea <text> to start." and stop.

---

## Subcommand: `/ideas` (list)

### Process

1. Read the backlog file.
2. Parse all entries. Each entry spans 1–2 lines:
   ```
   - [<status>] <hex-id> | <timestamp> | focus: <focus> | <idea>
     tags: <tags>          ← optional second line
   ```
3. Sort by timestamp descending (most recent first).
4. Render as a compact table:

```
## Ideas Backlog

ID     Status  Date        Idea
------ ------- ----------- ------------------------------------------------
a3f2   open    2026-04-27  faster onboarding flow for new devs
c91e   picked  2026-04-26  hex map approach for Spellpact combat
7b0d   done    2026-04-25  add tqdm to the GCP cost audit loop
```

5. Below the table, print a one-line count:
   ```
   N open · M picked · K done
   ```

No elaboration. Do not ask what to do next.

---

## Subcommand: `/ideas pop`

Surface the single highest-priority open idea and mark it `picked`.

### Priority score

```
priority = recency_score × tag_weight
```

- `recency_score`: 1.0 for today, decay by 0.1 per day (floor 0.1)
- `tag_weight`: default 1.0. Apply boosts:
  - `perf` → 1.3
  - `security` → 1.4
  - `research` → 1.1
  - `ui` → 1.0
  - `fix` → 1.2
  - no tags → 1.0

### Process

1. Parse all entries with status `open`.
2. Compute priority score for each.
3. Select the highest. On tie, pick the most recent.
4. Edit that line in-place: change `[open]` → `[picked]`.
5. Reply:

```
## Popped idea [<hex-id>]

<idea text>
Captured: <timestamp> | Originally while: <focus>
Tags: <tags or none>

Status set to picked. Use /ideas done <id> when complete.
```

If no open ideas exist: "Backlog is clear. Use /idea <text> to add one."

---

## Subcommand: `/ideas done <id>`

Mark an idea complete by hex ID.

### Process

1. Find the line(s) matching `<hex-id>` in the backlog file.
2. If not found: "ID <id> not found in backlog. Check /ideas for valid IDs."
3. Edit the status field in-place: `[open]` or `[picked]` → `[done]`.
4. Reply with one line:
   ```
   Marked [<hex-id>] done: <idea text>.
   ```

Do not delete the line. Append-only file — status edits are the only mutations.

---

## Recall Integration

When the user runs `/recall ideas`, treat it as an alias for `/ideas` (list view).

When the user runs `/recall <topic>`, also scan `ideas-backlog.md` for lines where the idea text or tags match `<topic>` and include matching entries under a "From Ideas Backlog" section in the recall output.

---

## Auto-Detect Mode (passive capture)

Claude monitors every user message for trigger phrases and topic shifts. This runs silently — no command needed.

### Trigger phrases

Any of the following anywhere in a message:
- "oh and another thing"
- "i just realized"
- "btw" / "by the way"
- "while we're at it"
- "speaking of which"
- "what about [topic unrelated to current task]"
- "also" as the opening word of a message, when it follows a completed sub-task

### Topic-shift detection

If the current message references a domain not mentioned in the prior 3+ messages AND no subcommand was issued, treat it as a possible side-idea. Apply auto-capture only when the message does not contain an explicit action request directed at the current task (i.e., the message reads more like a side-thought than a redirect).

### Auto-capture response pattern

When triggered:

1. Silently compose and append the backlog entry (same format as `/idea`).
2. Reply with exactly one sentence acknowledging capture, then continue the original task response:

   ```
   Captured to ideas-backlog: [<hex-id>] <idea text>. Continuing on <original focus>.
   ```

3. Complete the original task response in full beneath that line.

**Never break flow.** Auto-capture is an interrupt-free sidecar. If the user clearly wants to switch focus, they will say so explicitly — do not auto-capture in that case, just follow their lead.

### What NOT to do in auto-detect

- Do NOT ask "should I capture this?"
- Do NOT stop mid-task to discuss the idea.
- Do NOT pivot task focus based on the trigger.
- Do NOT add the capture notice as a footer — it goes before the task response, in one sentence, so it is visible but not intrusive.
