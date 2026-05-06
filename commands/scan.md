---
description: Full repository health scan -- security, quality, gaps, architecture, and operational health in one report
argument-hint: Optional focus (e.g., "security only", "src/auth", "quick")
---

# Repository Health Scan

Perform a unified health scan of the current project and produce a single prioritized report.
Focus/scope (if specified): $ARGUMENTS

## Phase 0: Pre-flight

Run these in parallel:

- Current git state: !`git status --short 2>/dev/null || echo "[not a git repo]"`
- Branch: !`git branch --show-current 2>/dev/null || echo "N/A"`
- Recent commits: !`git log --oneline -10 2>/dev/null || echo "No commits"`

Then determine:

1. **Project language**: Detect from `pyproject.toml`, `package.json`, `Cargo.toml`, `go.mod`, `*.gemspec`, or majority file extension.
2. **Test runner**: Detect from config files (`pytest.ini`, `jest.config.*`, `Makefile` test targets, CLAUDE.md). If none found, mark test checks as SKIP.
3. **Linter**: Detect from `ruff.toml`, `.eslintrc.*`, `.flake8`, CLAUDE.md. If none, SKIP.
4. **Build system**: Detect from `Dockerfile`, `Makefile`, `package.json scripts.build`. If none, SKIP.
5. **AI/LLM surface**: Check for MCP config, `openai`/`anthropic`/`langchain` imports, `.claude/` directory, agent files. Set `has_llm_surface` flag.

If no source files found, STOP: "No source files found. Is this the right directory?"

If `$ARGUMENTS` contains "quick", run Track A only and produce an abbreviated report.

---

## Phase 1: Parallel Analysis

Launch all three tracks simultaneously.

### Track A: Security and AI/LLM

**A1 -- Secrets scan:**
- Grep for: `api_key`, `secret`, `password`, `token`, `Bearer `, `sk-`, `ghp_`, base64 blobs >40 chars
- Check `.env` files are in `.gitignore`
- Check git history for committed-then-removed secrets

**A2 -- Dependency vulnerabilities:**
- Python: check `requirements.txt` / `pyproject.toml` for known vulnerable versions
- Node: check `package.json` / `package-lock.json`
- Other: flag deps outdated by >2 major versions

**A3 -- Injection and auth:**
- User input concatenated into SQL, shell commands (`subprocess`, `exec`, `eval`), or LLM prompts
- Unprotected routes/endpoints, missing auth decorators

**A4 -- AI/LLM surface (skip if `has_llm_surface = false`):**
- `{user_input}` interpolated into system prompts without sanitization
- MCP server permission scopes (read-only vs write tools exposed to untrusted input)
- PII or credentials in vector stores / memory databases
- Jailbreak strings in stored data

### Track B: Code Quality and Coverage Gaps

**B1 -- Test coverage map:**
- Map source modules to test files. Build table: module -> has_tests -> untested public symbols -> risk level.

**B2 -- Error handling gaps:**
- Bare `except:` without log/raise
- Network calls without try/except
- File open without context manager
- Nullable returns used without null checks

**B3 -- Type safety (skip if no type system):**
- Public functions missing type annotations (Python)
- `any` types on public interfaces (TypeScript)

**B4 -- Code quality:**
- DRY violations (10+ line near-duplicate blocks)
- Dead code (defined but never imported/called)
- TODO/FIXME/HACK comments with age from git blame

**B5 -- Documentation gaps:**
- README: does it have Setup and Usage sections?
- Public functions missing docstrings
- CLAUDE.md accuracy vs actual project structure

### Track C: Operational Health

Run sequentially within this track:

**C1 -- Dependencies:** All imports resolve; manifest matches actual imports
**C2 -- Lint:** Run detected linter. Report top 10 issues.
**C3 -- Type check:** Run mypy/tsc if configured. Report errors.
**C4 -- Tests:** Run test suite. Report total/passed/failed/coverage.
**C5 -- Build:** Run build command if configured.
**C6 -- Git health:** Uncommitted changes, untracked source files, branch vs remote, merge conflicts.

Each step produces: `PASS | FAIL | SKIP` with detail.

---

## Phase 2: Synthesis

Collect all track results. Then:

**1. Deduplicate:** Same `file:line` found in multiple tracks -> merge, keep higher severity.

**2. Cross-dimension severity uplift:**
- Security finding in untested module -> upgrade severity one level
- Injection vector + missing type check on same parameter -> Critical
- Test failure in security-flagged module -> tag "SECURITY RISK UNVERIFIED"

**3. Score each dimension (0-10):**

| Score | Meaning |
|-------|---------|
| 10 | Zero findings |
| 7-9 | Only Low findings |
| 4-6 | Medium findings present |
| 1-3 | High findings present |
| 0 | Critical finding present |

**4. Generate prioritized action list** sorted by:
1. Severity (Critical first)
2. Effort (quick wins first at equal severity)

---

## Phase 3: Report

```
================================================================================
REPOSITORY HEALTH SCAN
Project: [name from config or directory]
Scanned: [timestamp]
Scope: [full project | $ARGUMENTS]
================================================================================

EXECUTIVE SUMMARY
-----------------
[3-5 sentences max. Most important finding, overall posture, top action.]

Overall: [HEALTHY | NEEDS ATTENTION | AT RISK | CRITICAL]

SCORECARD
---------
Dimension      Score   Status   Top Finding
-----------    -----   ------   -----------
Security       X/10    [s]      [one-line or "None"]
Tests          X/10    [s]      [one-line or "None"]
Code Quality   X/10    [s]      [one-line or "None"]
Documentation  X/10    [s]      [one-line or "None"]
Operational    X/10    [s]      [one-line or "None"]
AI/LLM         X/10    [s]      [one-line or SKIP reason]

[s] = PASS (>=8) | WARN (4-7) | FAIL (<=3)

================================================================================
SECTION 1: SECURITY FINDINGS
================================================================================

[SEVERITY] file.py:42
  Pattern: [what was detected]
  Risk: [why this matters]
  Fix: [specific action]
  Effort: [estimate]

================================================================================
SECTION 2: TEST COVERAGE GAPS
================================================================================

Module                 Has Tests   Untested Symbols   Risk
--------------------   ---------   ----------------   ----
[path]                 YES/NO      [count]            HIGH/MED/LOW

================================================================================
SECTION 3: CODE QUALITY
================================================================================

[Error handling, type gaps, DRY violations, dead code -- each with file:line]

================================================================================
SECTION 4: DOCUMENTATION
================================================================================

[README gaps, missing docstrings, CLAUDE.md accuracy]

================================================================================
SECTION 5: OPERATIONAL HEALTH
================================================================================

Dependencies:  [PASS/FAIL/SKIP]   [detail]
Lint:          [PASS/FAIL/SKIP]   [N issues]
Type check:    [PASS/FAIL/SKIP]   [detail]
Tests:         [PASS/FAIL/SKIP]   [X/Y passed, Z% coverage]
Build:         [PASS/FAIL/SKIP]   [detail]
Git health:    [PASS/WARN/SKIP]   [detail]

================================================================================
SECTION 6: AI/LLM SURFACE  [omit if skipped]
================================================================================

[Prompt injection, MCP permissions, memory store PII -- each with file:line]

================================================================================
PRIORITIZED ACTION LIST
================================================================================

1. [CRITICAL] [SEC] [5min]  file.py:12 -- Remove hardcoded API key
2. [HIGH]     [TEST][30min] payments.py -- Add tests for payment module
3. [MEDIUM]   [QUAL][2h]    utils.py -- Extract duplicate validation logic
...

================================================================================
LEARNINGS
================================================================================

[Tag non-obvious findings with [LEARNING]. One line each.]
```

After the report, ask: **"Want me to start on item 1, or pick a different priority?"**

## Rules

- Never skip Phase 0. If project structure cannot be determined, report that and stop.
- A failure in one track does not cancel other tracks.
- Max 30 findings in the action list. If more: "... and N more. Run `/gap-analysis` for the full list."
- Every finding must have a specific `file:line` reference. No vague claims.
- If `$ARGUMENTS` names a subdirectory, restrict all scans to that path.
- Skipped dimensions appear in the scorecard with the skip reason, not omitted silently.
