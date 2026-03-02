---
description: Checkpoint current task state to survive context compaction — run before long operations or when you sense the session is getting large
argument-hint: [optional: task summary] (e.g., "implementing rate limiter, middleware done, webhooks next")
---

# Context Checkpoint

Save current task state so it can be recovered after context compaction.

## Input

Context hint: $ARGUMENTS

## When to Use

- Before a long operation (large refactor, multi-file implementation)
- When the conversation feels long (60+ messages)
- Before spawning multiple agents that will generate lots of output
- Anytime you think "I'd hate to lose track of where I am"

## Phase 1: Gather Current State

Collect the following (read from context, do NOT re-read files unless needed):

1. **Task description** — what are we working on?
2. **Decisions made** — architectural choices, rejected alternatives, and WHY
3. **Progress** — what's done, what's in progress, what's next
4. **Key files** — files modified or being worked on (paths + line ranges)
5. **Gotchas discovered** — anything non-obvious learned during this session
6. **Blockers** — anything currently stuck or waiting on input

If $ARGUMENTS is provided, use it as the task summary. Otherwise, infer from conversation context.

## Phase 2: Save to Memory

Check if memory MCP tools are available (try `memory_save`).

### If memory MCP is available:

Save using `memory_save` with:
```
category: "context"
importance: 9
tags: ["checkpoint", "session-context", project-name]
content: [structured checkpoint from Phase 1]
summary: [one-line task summary]
project: [current project name from directory or CLAUDE.md]
```

### If memory MCP is NOT available:

Fall back to writing a checkpoint file:

1. Write to `.claude/checkpoint.md` in the current project directory:

```markdown
# Session Checkpoint — [timestamp]

## Task
[task description]

## Decisions
- [decision 1]: [reasoning]
- [decision 2]: [reasoning]

## Progress
- [x] [completed items]
- [ ] [in progress]  <-- CURRENT
- [ ] [remaining items]

## Key Files
- path/to/file.py:42-78 — [what was changed/being changed]
- path/to/other.py:10-25 — [what was changed/being changed]

## Gotchas
- [non-obvious thing discovered]

## Next Step
[exactly what to do next — specific enough to resume without re-reading context]
```

2. Also write a one-line summary to `.claude/last-checkpoint.txt`:
```
[timestamp] [task summary] — checkpoint at .claude/checkpoint.md
```

## Phase 3: Confirm

```
CONTEXT SAVED
=============
Task:     [one-line summary]
Progress: [X/Y steps complete]
Saved to: [memory / .claude/checkpoint.md]
Next:     [the immediate next step]

To recover after compaction:
  /recall [task topic]              — if memory is available
  Read .claude/checkpoint.md        — if using file fallback
```

## Rules

1. **Don't re-read files to gather state.** Use what's already in the conversation context. The whole point is to be token-efficient.
2. **Be specific about "next step."** Not "continue working" — instead "implement the webhook handler in src/webhooks.py, following the pattern from src/events.py:45."
3. **Include WHY for decisions.** After compaction, the reasoning is what's hardest to recover. The code diff shows WHAT changed; the checkpoint saves WHY.
4. **Overwrite previous checkpoints.** Only the latest matters. Don't accumulate stale checkpoints.
5. **Works without memory MCP.** The file fallback ensures every developer can checkpoint, even without the full memory system.
