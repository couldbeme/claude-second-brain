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
1. Review the current session for:
   - Commands that were discovered or corrected
   - Patterns that worked or failed
   - Gotchas encountered
   - Decisions made with reasoning
2. Extract learnings as structured entries.

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

## Self-Learning Triggers

These are automatic learning opportunities -- always capture them:
- A test failed for a non-obvious reason
- An import or dependency was missing that was not in requirements
- A command in CLAUDE.md was wrong or outdated
- A file path in CLAUDE.md no longer exists
- A teammate corrected an incorrect assumption
