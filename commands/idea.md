---
description: Capture a side-idea instantly without breaking current task flow
argument-hint: The idea to capture (one-liner)
---

# Idea -- Instant Idea Capture

Capture a side-idea to the backlog in one second and return to work. No discussion, no pivot.

## Input

Idea: $ARGUMENTS

## Process

### 1. Validate input

If $ARGUMENTS is empty: reply "Usage: /idea <your idea>" and stop. Do not ask follow-up questions.

### 2. Generate ID

Generate a 4-character lowercase hex ID (e.g. `a3f2`). Use randomness — do not increment sequentially.

### 3. Resolve current task context

Summarize the task currently in focus in ≤8 words. This becomes `focus`. If no prior context exists in the conversation, use `unknown`.

### 4. Compose entry

```
- [open] <hex-id> | <YYYY-MM-DD HH:MM> | focus: <current-task-summary> | <idea>
```

No tags line unless the idea text itself contains an explicit tag signal (e.g. "ui:", "perf:", "research:"). If present, add:
```
  tags: <inferred tags>
```

### 5. Append to backlog

File: `~/.claude/projects/<slug>/memory/ideas-backlog.md`

If the file does not exist, create it with this header first:
```markdown
# Ideas Backlog
Append-only. Edit status field in-place. IDs are 4-char hex.
```

Then append the entry. Always append — never rewrite existing lines.

### 6. Acknowledge and stop

Reply with exactly one line:

```
Captured [<hex-id>]: <idea text>. Back to: <original focus>.
```

No elaboration. No questions. No alternatives. Return to the task that was in progress.

## Error Handling

- File write fails: Report the error on one line, then paste the formatted entry so the user can save it manually. Do not ask questions.
- ID collision (same hex already in file): Regenerate once. If collision persists, append a suffix (`a3f2b`).

## What NOT to do

- Do NOT open a discussion about the idea.
- Do NOT ask "would you like to expand on this?"
- Do NOT offer to implement the idea now.
- Do NOT switch the current task context.
- Do NOT produce more than one line of output on success.
