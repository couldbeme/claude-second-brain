---
description: Save a new learning to the project knowledge base
argument-hint: What was learned (or "from session" to extract from current session)
---

# Learn -- Save Knowledge

Capture a learning and persist it for future sessions.

## Input

Learning: $ARGUMENTS

## Process

### If $ARGUMENTS is "from session":
1. **Scan for tagged learnings:**
   - Find all `[LEARNING]` tags in the session
   - Extract any explicit learnings mentioned in conversation

2. **Scan for missed correction patterns** (Layer 2 detection):
   - Rhetorical questions that were actually corrections ("why did you...?", "why is there no...?")
   - Past-behavior references ("previously you...", "before you...")
   - Expectation violations ("I expected...", "that's not what I meant")
   - Repeated corrections (same issue raised twice = critical, missed learning)
   - Emphasis signals (ALL CAPS, repeated letters = importance escalation)
   - Preference signals ("always", "never", "from now on")

3. **Scan for user model observations** (Layer 3):
   - Communication style patterns (formality level, message length, structure preference)
   - Decision patterns (did user accept first option, or ask for alternatives?)
   - Frustration/satisfaction events (what triggered them, what resolved them?)
   - Cognitive style signals (big-picture vs detail-first, sequential vs parallel)

4. **Extract and categorize** all findings:
   - Technical learnings → standard learning flow
   - Missed corrections → save with importance boost (+1 for being missed)
   - User model observations → save with `category="user_model"`, `source="inferred"`

### If $ARGUMENTS is a specific learning:
1. Parse the learning into structured format.

### For each learning:

1. **Classify** the learning:
   - `project-specific` -- Goes in project `.claude/CLAUDE.md` under Gotchas or Domain Rules
   - `global` -- Goes in global `~/.claude/CLAUDE.md`
   - `tool-usage` -- Update the relevant slash command file
   - `pattern` -- Document in project patterns section

2. **Format** as a one-line entry:
   ```
   - [CONTEXT]: [LEARNING] -- [WHY IT MATTERS]
   ```

3. **Check for duplicates**: Search existing CLAUDE.md files for similar content. Do not add duplicates.

4. **Present as diffs**: Show proposed additions to CLAUDE.md files. Ask for approval before writing.

5. **Confirm** what was saved and where.

## Output Format

```
## Session Learning Report

### Technical Learnings (N found)
- [LEARNING] ...
- [LEARNING] ...

### Missed Corrections (N found)
- [MISSED] Rhetorical question at turn X was a correction: ...
- [MISSED] Past-behavior reference at turn Y: ...

### User Model Updates (N observations)
- [MODEL] Communication: ...
- [MODEL] Decision style: ...

### Summary
Saved: X technical, Y corrections, Z model updates
```

## Self-Learning Triggers

These are automatic learning opportunities -- always capture them:
- A test failed for a non-obvious reason
- An import or dependency was missing that was not in requirements
- A command in CLAUDE.md was wrong or outdated
- A file path in CLAUDE.md no longer exists
- A teammate corrected an incorrect assumption
- A rhetorical question was actually a correction (Layer 2)
- A repeated correction indicates a missed learning (Layer 2)
- A communication or decision pattern emerged across the session (Layer 3)
