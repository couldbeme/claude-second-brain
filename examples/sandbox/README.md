# Sandbox -- Hands-On Toolkit Practice

A small Python app with **5 intentional issues** for you to find and fix using the toolkit.

## The Issues

| # | Type | Severity | Hint |
|---|------|----------|------|
| 1 | Security | Critical | Look for hardcoded secrets |
| 2 | Code quality | High | Error handling that hides problems |
| 3 | Bug | High | What happens when data is missing? |
| 4 | Coverage | Medium | How many tests exist? |
| 5 | Security | Critical | Does login actually verify passwords? |

## Walkthrough

### Step 1: Scan for issues

```
cd examples/sandbox/
/scan
```

The scan finds all 4 issues and produces a prioritized report. You'll see the security issue flagged as critical and the missing tests as a coverage gap.

### Step 2: Fix the bug with TDD

```
/tdd Fix the null return bug in get_user_display
```

Watch the TDD cycle:
1. **RED** -- Claude writes a test that calls `get_user_display()` with a non-existent user ID. The test expects a clean error (like `None` or a 404), but gets a `TypeError` crash.
2. **GREEN** -- Claude adds a null check: if `get_user()` returns `None`, handle it gracefully.
3. **REFACTOR** -- Clean up if needed.

### Step 3: Verify the fix

```
/verify
```

Confirms tests pass, no regressions, project is healthy.

### Step 4: Audit security

```
/audit security
```

The hardcoded API key (`sk-prod-...`) gets flagged with a specific fix: move it to an environment variable.

### Step 5: Fix the remaining issues

```
/tdd Fix the bare except in search_users
/tdd Add authentication tests
```

### Step 6: Save what you learned

```
/learn from session
```

Claude captures the patterns you discovered and saves them to project memory.

### Step 7: Check your progress

```
/scan
```

Compare the before and after scorecards. You should see all critical issues resolved.

## Expected Results

After fixing all 4 issues:

| Metric | Before | After |
|--------|--------|-------|
| Security findings | 1 critical | 0 |
| Code quality issues | 1 high | 0 |
| Bugs | 1 high | 0 |
| Test coverage | 0% | >80% |

## Tips

- Run `/explain app.py` first if you want to understand the code before fixing it
- Use `/gap-analysis` for a detailed breakdown of what's missing
- Try `/diagnose TypeError: cannot unpack non-iterable NoneType` to see how diagnose works
