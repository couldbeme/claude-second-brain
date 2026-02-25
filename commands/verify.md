---
description: End-to-end verification of the current project or recent changes
argument-hint: Optional scope (e.g., "recent changes" or "full project")
---

# End-to-End Verification

Verify that the project is in a healthy, deployable state. Scope: $ARGUMENTS

## Execution

Run the following checks sequentially (each depends on the previous passing):

### 1. Dependency Check
- Verify all imports resolve (no missing packages)
- Check requirements.txt / pyproject.toml is consistent with actual imports
- Flag any pinned versions with known vulnerabilities (if web search available)

### 2. Lint Check
- Run the project's configured linter (Ruff, ESLint, etc.)
- Report and auto-fix any fixable issues
- List any remaining unfixable issues

### 3. Type Check (if applicable)
- Run type checker (mypy, pyright, tsc)
- Report type errors

### 4. Test Suite
- Run the full test suite
- Report: total tests, passed, failed, skipped, errors
- For any failures, show the failure output and identify the likely cause
- Report coverage if available

### 5. Build Check (if applicable)
- Run the build command (Docker build, package build)
- Verify the build completes without errors

### 6. Git Health
- Check for uncommitted changes
- Check for untracked files that should be committed or gitignored
- Verify branch is up to date with remote
- Check for merge conflicts

### 7. Configuration Consistency
- Verify .env.example matches required env vars in code
- Check that CLAUDE.md reflects actual project structure
- Verify CI config matches local commands

## Output

```
Verification Report
===================
Dependency check:  [PASS/FAIL] -- [details if fail]
Lint:              [PASS/FAIL] -- [N issues]
Type check:        [PASS/FAIL/SKIP] -- [details]
Tests:             [PASS/FAIL] -- [X/Y passed, coverage Z%]
Build:             [PASS/FAIL/SKIP] -- [details]
Git health:        [PASS/FAIL] -- [details]
Config consistency:[PASS/FAIL] -- [details]

Overall: [HEALTHY / NEEDS ATTENTION / BROKEN]
```

If any check fails, provide specific remediation steps.
