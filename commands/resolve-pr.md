---
description: Review and resolve PR comments — fetch feedback, learn patterns, scan for similar issues, fix thoroughly, then await approval before replying or pushing
argument-hint: PR number (e.g., "188") or "latest"
---

# Resolve PR Review Comments

Fetch all pending review comments, understand the patterns behind them, scan the entire PR for similar issues, fix everything thoroughly, and **present a plan for approval before posting any replies or pushing any code**.

## Input

PR: $ARGUMENTS

## Phase 1: Fetch Comments

1. If `$ARGUMENTS` is "latest", find the most recent open PR on the current branch:
   ```bash
   gh pr list --head $(git branch --show-current) --state open --json number --jq '.[0].number'
   ```

2. Fetch all review comments, reviews, and the full PR diff:
   ```bash
   gh api repos/{owner}/{repo}/pulls/{pr}/comments
   gh pr view {pr} --json reviews,files
   gh pr diff {pr}
   ```

3. Filter to **unresolved** comments from reviewers (exclude your own replies).

4. Group by file — you'll fix file-by-file.

## Phase 2: Understand and Learn from Each Comment

For each comment:
1. **Read the file + surrounding code** at the referenced line
2. **Classify the feedback**:
   - **Direct fix**: clear instruction ("use `with`", "remove this", "rename to X")
   - **Design concern**: reviewer questions the approach ("this is not secure", "move this logic out")
   - **Clarification request**: reviewer asks a question ("not true?", "why?")
   - **Style nit**: formatting, naming preference
   - **Anti-pattern flag**: reviewer identifies a pattern that should never appear ("try-catch-reraise is not a real pattern", "don't mock logger")

3. **Check if the reviewer is right** — read the code, don't blindly agree. If the reviewer is wrong or there's important context, note it for the approval step.

4. **Extract the principle behind each comment** — not just "fix line 43" but "this team avoids mocking internals like logger; use assertLogs instead". This is what gets learned and scanned for.

**Save learnings immediately** using `/learn`:
- Reviewer-specific preferences (e.g., "reviewer-A: don't mock logger, use assertLogs")
- Team anti-patterns identified (e.g., "unused helper methods in test classes are flagged")
- Patterns that should propagate across the codebase

## Phase 3: Scan for Similar Issues Across the Entire PR

**This is not optional.** For every principle extracted in Phase 2, scan the full PR diff and all changed files for the same anti-pattern.

Examples:
- Reviewer flags unused helper method → scan all test files in the PR for other unused helpers
- Reviewer flags logger mocking → scan all tests in the PR for `patch(...logger...)` or `mock_logger`
- Reviewer flags `if __name__ == "__main__"` → scan all changed files for the same block
- Reviewer flags missing `try/finally` for a resource → scan all similar resource-handling code in the PR

**If similar issues are found:**
- List them explicitly in the output
- Include them in the fix plan
- If the scope is large or touches multiple subsystems, recommend spawning `/team` to handle the fix in parallel (see Phase 3b)

### Phase 3b: Complexity Check — When to Spawn `/team`

Spawn `/team` if ANY of the following:
- More than 3 files need non-trivial changes
- The reviewer's concern touches a design pattern used across multiple modules
- The fix requires writing new tests (not just modifying existing ones) for discovered issues
- The changes span both src/ and tests/ in a way that warrants TDD discipline

If `/team` is warranted, **stop here**, present the plan, and wait for user approval before spawning.

## Phase 4: Plan Fixes (TDD where applicable)

For each issue (both from comments and from the scan):
1. Classify: does this require a new test first? If the fix addresses a behaviour gap (not just style), use `/tdd`.
2. Plan the change at the file + line level before touching anything.
3. Note whether existing tests need updating.

**Rules for fixing:**
- Fix every instance of the anti-pattern in the PR — not just the commented line
- When a reviewer suggests a pattern — use exactly that pattern, not a variation
- If a fix requires changes in other files, find and update ALL references
- Never half-fix (e.g., don't remove just the flagged usage if 3 others remain in the same file)

## Phase 5: Apply Fixes

For each file with changes:
1. Read the full file
2. Apply all changes for that file in one edit
3. Run the linter on the changed file

## Phase 6: Run Full Test Suite

```bash
make test
make lint
```

All tests must pass before proceeding. If a fix breaks tests, fix the tests (or reconsider the fix). Do not proceed to Phase 7 until green.

## Phase 7: Present Plan for Approval — STOP HERE

**Do not post any GitHub replies. Do not push. Do not commit.**

Present a summary to the user:

```
PR #{pr} — Review Resolution Plan
===================================

## Comments addressed
  [reviewer] file.py:line — [what you changed and why]
  [reviewer] file.py:line — [what you changed and why]

## Additional issues found (same pattern, not commented)
  file.py:line — [issue] — [fix applied]

## Pushback (if any)
  [reviewer] file.py:line — [why you disagree, with evidence]
  → Proposed reply: "[draft reply text]"

## Proposed GitHub replies (pending approval)
  Comment #ID ([reviewer]): "[draft reply text]"
  Comment #ID ([reviewer]): "[draft reply text]"

## Tests
  [pass/fail — N tests, N assertions]

## Commit message (pending approval)
  fix: address PR #{pr} review feedback (round N)
  - [bullet per change]
  Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

## Learnings saved
  - [pattern] → [file saved to]

Awaiting approval to: commit → push → post replies
```

## Phase 8: After Approval Only

Once the user explicitly approves:

1. Commit:
   ```bash
   git add [changed files]
   git commit -m "..."
   ```

2. Push:
   ```bash
   git push origin [branch]
   ```

3. Post replies to each comment via:
   ```bash
   gh api repos/{owner}/{repo}/pulls/{pr}/comments/{comment_id}/replies -X POST -f body="..."
   ```

4. Reply to EVERY unresolved comment — even if just "Done" or a clarification.

**Tone for replies:**
- Appreciative, not defensive ("Good catch", "Fair point", "You're right")
- State what changed, not just "fixed"
- 2-3 sentences max
- Never say "I already fixed this" — describe the fix

## Rules

- **NEVER post GitHub comments without explicit user approval**
- **NEVER push without explicit user approval**
- **Read the code before classifying** — never guess what a comment is about
- **One commit per review round** — not one per comment
- **Scan broadly** — a comment about one line is often a signal about a pattern. Fix the pattern.
- **Save learnings before fixing** — understand first, then apply broadly
- **Tests must pass** before presenting the plan
