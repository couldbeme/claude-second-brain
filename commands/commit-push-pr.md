---
description: TDD-enforced commit, push, and PR workflow
---

## Pre-flight Context

- Current git status: !`git status --short 2>/dev/null`
- Current diff stats: !`git diff --stat HEAD 2>/dev/null`
- Current branch: !`git branch --show-current 2>/dev/null`
- Recent commits: !`git log --oneline -5 2>/dev/null`

## Your Task

Before committing, verify TDD discipline:

1. **Run tests**: Execute the project test suite (check CLAUDE.md for the test command). If ANY test fails, STOP and report the failure. Do not commit broken code.

2. **Run linter**: Execute the project linter. Fix any auto-fixable issues first.

3. **If all green**, proceed with:
   a. Create a new branch if on main/master (use descriptive name from changes)
   b. Stage changed files (never stage .env, credentials, or secrets)
   c. Create a commit with a conventional message matching repo style
   d. Push to origin with -u flag
   e. Create a PR using `gh pr create` with:
      - Short title (under 70 chars)
      - Body with ## Summary (bullet points) and ## Test plan
   f. Return the PR URL

4. **If tests or lint fail**: Report what failed and offer to fix it. Do NOT bypass with --no-verify.

## Rules

- Never commit without tests passing
- Never stage .env, credentials, or API key files
- Never force push to main/master
- Always use conventional commit messages
- One atomic commit per logical change
