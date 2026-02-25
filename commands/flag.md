---
description: Flag findings for team review instead of fixing them unilaterally
argument-hint: description of what you found, or "scan" to review recent work
---

# Flag for Team Review

When you find something that looks wrong, inconsistent, or suspicious — but fixing it unilaterally would be premature — use this workflow to document it and get team input.

## When to Use This

- Pre-existing issues found while working on something else
- Config mismatches where you're not sure if they're intentional
- Code patterns that look wrong but might have context you're missing
- Security concerns that need team awareness before action
- Naming inconsistencies, dead code, or technical debt you didn't introduce

## Input

Finding: $ARGUMENTS

## Process

### Phase 1: Investigate Before Flagging

Before raising anything, verify it's actually an issue:

1. **Check git blame** — who wrote it and when? Recent and deliberate, or old and possibly forgotten?
2. **Search for context** — grep for related comments, TODOs, or documentation that might explain the decision
3. **Check if it's used** — is the "wrong" thing actually consumed somewhere that makes it right?
4. **Assess impact** — is this causing real problems, or is it cosmetic?

Classify each finding:
- **CONFIRMED**: Verified issue with evidence (e.g., field name doesn't match, config not loaded)
- **SUSPICIOUS**: Looks wrong but might be intentional (e.g., unusual naming, disabled feature)
- **COSMETIC**: Technically incorrect but zero functional impact (e.g., typo in comment)

### Phase 2: Determine the Right Channel

Based on context, choose where to flag:

| Context | Channel | Format |
|---------|---------|--------|
| Found during PR review work | PR comment | Inline finding |
| Found during general work | GitHub Issue | Structured issue |
| Security concern | Direct message / urgent PR comment | Marked as security |
| Blocking your current work | PR comment + tag reviewers | Request for input |

### Phase 3: Write the Flag

Use this template for each finding:

```markdown
## [CONFIRMED/SUSPICIOUS/COSMETIC] Brief title

**Where**: `file.py:line` (or config file, etc.)
**What**: [Describe what you observed]
**Expected**: [What you'd expect instead, if applicable]
**Impact**: [Real breakage / silent misconfiguration / cosmetic only]
**Evidence**: [git blame, grep results, test output — show your work]

**Not fixing because**: [It's pre-existing / I'm not sure it's wrong / needs team context / out of scope for current PR]

@[relevant team members] — is this intentional or should I fix in a follow-up?
```

### Phase 4: Post and Track

1. Post the finding to the chosen channel
2. If multiple findings, group them in a single comment/issue with a summary at top
3. Add a brief note in your PR description: "Also flagged N pre-existing issues for team review (see comment)"
4. Do NOT block your current work waiting for answers

## Rules

- **Never fix pre-existing issues in an unrelated PR** without team buy-in — it inflates the diff and muddles review
- **Always show evidence** — don't say "this looks wrong", say "Config expects MCP_ but .env has MPC_ (git blame shows it was added in abc123 by @user, 3 months ago)"
- **Be specific about impact** — "no actual breakage because defaults match" is very different from "production will use wrong DB"
- **Tag the right people** — check git blame to find who owns the code
- **Tone**: curious, not accusatory. "Is this intentional?" not "This is broken."
- **One flag per concern** — don't bundle unrelated issues unless they share a root cause

## Output

After posting, summarize what was flagged:

```
Flagged N findings for team review:
1. [CONFIRMED] Brief title — posted to [PR #X / Issue #Y]
2. [SUSPICIOUS] Brief title — posted to [PR #X / Issue #Y]

None of these block current work. Awaiting team input before any fixes.
```
