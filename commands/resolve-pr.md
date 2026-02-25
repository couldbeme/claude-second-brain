---
description: Review and resolve PR comments — fetch feedback, fix code, reply politely
argument-hint: PR number (e.g., "188") or "latest"
---

# Resolve PR Review Comments

Fetch all pending review comments on a PR, address each one with code changes and polite replies, and push the fixes.

## Input

PR: $ARGUMENTS

## Phase 1: Fetch Comments

1. If `$ARGUMENTS` is "latest", find the most recent open PR on the current branch:
   ```bash
   gh pr list --head $(git branch --show-current) --state open --json number --jq '.[0].number'
   ```

2. Fetch all review comments and reviews:
   ```bash
   gh api repos/{owner}/{repo}/pulls/{pr}/comments
   gh pr view {pr} --json reviews
   ```

3. Filter to **unresolved** comments from reviewers (exclude your own replies).

4. Group by file — you'll fix file-by-file.

## Phase 2: Understand Each Comment

For each comment:
1. **Read the file + surrounding code** at the referenced line
2. **Classify the feedback**:
   - **Direct fix**: clear instruction ("use `with`", "remove this", "rename to X")
   - **Design concern**: reviewer questions the approach ("this is not secure", "move this logic out")
   - **Clarification request**: reviewer asks a question ("not true?", "why?")
   - **Style nit**: formatting, naming preference

3. **Check if the reviewer is right** — read the code, don't blindly agree. If the reviewer is wrong or there's important context, explain respectfully in the reply.

## Phase 3: Apply Fixes

For each comment that requires a code change:
1. Read the file
2. Make the change
3. Run the linter on the changed file
4. Note what you changed for the reply

**Batch changes by file** — don't make 5 separate edits to the same file.

**Rules for fixing:**
- When a reviewer says "remove this" — remove it fully. Don't half-measure (e.g., don't strip down an endpoint when they want it gone).
- When a reviewer suggests a pattern — use exactly that pattern, not a variation.
- When a reviewer says "try-catch-raise is not a real pattern" — they're teaching you. Learn and apply broadly.
- If a fix requires changes in other files (e.g., removing an endpoint requires updating the frontend), find and update ALL references.

## Phase 4: Run Tests

```bash
make test  # or the project's test command
make lint
```

All tests must pass before replying. If a fix breaks tests, fix the tests too (or reconsider the fix).

## Phase 5: Reply to Each Comment

For each comment, reply with:

**If you made a fix:**
> Done — [brief description of what changed]. [One sentence acknowledging why the reviewer was right or what you learned].

**If you pushed back:**
> [Respectful explanation of why you kept the original approach, with evidence]. Happy to change if you still disagree.

**If it was a clarification:**
> [Clear answer to their question, with evidence if possible].

**Tone guidelines:**
- Appreciative, not defensive ("Good catch", "You're right", "Fair point")
- Acknowledge when their feedback teaches you something
- Keep it concise — 2-3 sentences max
- Never say "I already fixed this" — say what the fix is

## Phase 6: Commit and Push

```bash
git add [changed files]
git commit -m "fix: address PR #{pr} review feedback (round N)

- [bullet per reviewer comment addressed]

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"

git push origin [branch]
```

## Phase 7: Save Learnings

For each comment that taught something non-obvious, save to memory:
- Team code style preferences
- Reviewer-specific patterns (e.g., "reviewer is strict on security endpoints")
- Anti-patterns identified (e.g., "try-catch-reraise is not a real pattern")

Tag with `[LEARNING]` in your response.

## Output

```
PR #{pr} — Round N Review Resolution
=====================================
Comments addressed: X/Y
  [reviewer] file.py:line — [action taken]
  [reviewer] file.py:line — [action taken]
  ...

Tests: [pass/fail]
Commit: [hash]
Pushed: [yes/no]

Learnings saved: N
```

## Rules

- **Read the code before replying** — never guess what a comment is about
- **Don't push before tests pass** — fix everything first
- **One commit per review round** — don't create a commit per comment
- **Reply to EVERY comment** — even if just "Done" or "Acknowledged"
- **Never be defensive** — the reviewer is investing their time to make the code better
- **Save learnings immediately** — don't wait for end of session
- **Check for upstream changes before pushing** — `git pull --rebase` first
