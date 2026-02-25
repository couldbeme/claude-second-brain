# Command Reference

Full reference for all 18 slash commands in the Claude Code Team Toolkit.

---

## Orient -- Understand What You Have

### `/status`

**When to use:** Start of session, before standup, returning after time away.

```
/status
```

Reads git state, runs tests and linter, suggests next steps. Output under 50 lines.

### `/explain`

**When to use:** Onboarding to unfamiliar code, reviewing a complex module.

```
/explain src/auth/middleware.py
/explain whole project
```

Produces three depth levels:
- **High:** What it does, where it fits (1-2 sentences)
- **Medium:** Key functions, ASCII data flow, design decisions
- **Detail:** Line references, error handling, performance, quirks

### `/recall`

**When to use:** Before working on something that might have prior context.

```
/recall rate limiting approach
/recall how we handle auth tokens
```

Searches CLAUDE.md files, README, docs/, code, and test files. Synthesizes results by source.

### `/guide`

**When to use:** You're new to the toolkit and don't know which command to reach for. Or you want a recommended workflow for your current task.

```
/guide I need to add a new API endpoint
/guide I'm new to this codebase
/guide tour
```

Classifies your intent (orient, build, analyze, ship, research, knowledge, meta) and suggests a step-by-step workflow with the exact commands to run and WHY each step matters.

**Example input:**
```
/guide I need to fix a bug in the auth module
```

**Example output:**
```
For fixing a bug, here's the recommended workflow:

1. /recall auth bug              — check if this was seen before
2. /explain src/auth/            — understand the module before touching it
3. /tdd Fix [the bug]            — test-first fix (proves the fix works)
4. /learn [root cause]           — save what caused it to prevent recurrence

Why this order: The most common mistake is jumping straight to fixing.
Checking history and understanding context first means you fix the root
cause, not just the symptom.

Want me to run `/recall auth bug` now?
```

**Tour mode:** Run `/guide tour` to get a categorized overview of all 18 commands grouped by purpose (Orient, Build, Analyze, Research & Learn, Power Tools).

---

## Build -- Write and Ship Quality Code

### `/tdd`

**When to use:** Implementing any feature or fix.

```
/tdd Add rate limiting to the /api/users endpoint
/tdd Fix the race condition in the queue consumer
```

Enforces the cycle:
1. **RED** -- Write failing tests (happy path + edge cases + errors)
2. **GREEN** -- Minimum code to pass ALL tests
3. **REFACTOR** -- Clean up while keeping tests green

### `/diagnose`

**When to use:** You have an error screenshot, log file, or stack trace and need to understand what went wrong.

```
/diagnose ~/Desktop/Screenshot 2026-02-25.png
/diagnose latest screenshot
/diagnose ~/logs/app.log
/diagnose TypeError: cannot unpack non-iterable NoneType object
```

Accepts any input: screenshots (PNG, JPG), log files, or pasted error text. Reads images visually, extracts error patterns, searches your codebase for affected code, diagnoses the root cause, and offers to fix it with TDD.

**Example output:**
```
## Diagnosis

Issue type:  Runtime exception
Severity:    High
Root cause:  NoneType returned from get_user() when user doesn't exist

### What I see
Screenshot shows a Python traceback in terminal:
  File "src/api/users.py", line 47, in get_profile
    name, email = get_user(user_id)
  TypeError: cannot unpack non-iterable NoneType object

### Affected code
- src/api/users.py:47 -- unpacks get_user() without null check
- src/db/queries.py:23 -- get_user() returns None for missing users

### Root cause analysis
get_user() returns None when the user ID doesn't exist in the database,
but get_profile() assumes it always returns a tuple and tries to unpack.
The missing null check causes a TypeError instead of a proper 404.

### Recommended fix
Add a null check after get_user() call, return 404 if user not found.

Want me to fix this now? (I'll write a failing test first)
```

### `/verify`

**When to use:** Before a release, after a big refactor, weekly health check.

```
/verify full project
/verify recent changes
```

Runs 7 sequential checks: dependencies, lint, types, tests, build, git health, config consistency. Outputs a traffic-light report with remediation steps for failures.

### `/commit-push-pr`

**When to use:** Ready to ship.

```
/commit-push-pr
```

- Runs tests -- **blocks if any fail**
- Lints and auto-fixes
- Creates branch if on main, commits with conventional message
- Pushes and opens PR with summary + test plan
- Returns the PR URL

---

## Analyze -- Find and Fix Issues

### `/audit`

**When to use:** New project onboarding, pre-launch review, quarterly health check.

```
/audit
/audit security
```

Runs 5 parallel analysis dimensions:

| Dimension | What it checks |
|-----------|---------------|
| Security | Secrets, injection, auth, CVEs, data handling |
| Tests | Coverage gaps, flaky tests, test quality |
| Quality | DRY, coupling, dead code, error handling |
| Docs | README accuracy, CLAUDE.md, inline docs |
| Performance | Resource leaks, N+1 queries, async issues |

Produces a scorecard (X/10 per dimension) and top 10 actionable findings.

### `/gap-analysis`

**When to use:** "What are we missing?" -- before hardening or launch.

```
/gap-analysis
/gap-analysis src/payments/
```

Maps source files to test files, flags untested functions, finds missing docs, error handling gaps, type annotation gaps, and config gaps. Outputs a prioritized report: Critical > Important > Nice-to-have.

**Example output:**
```
Gap Analysis: src/auth/
========================

TEST COVERAGE GAPS
| Source File       | Test File          | Tested          | Untested              | Gap  |
|-------------------|--------------------|-----------------|----------------------|------|
| auth/middleware.py | tests/test_auth.py | login, logout   | refresh_token, revoke | 50%  |
| auth/oauth.py     | (none)             | --              | ALL (4 functions)     | 100% |

DOCUMENTATION GAPS
- auth/oauth.py: No module docstring, no function docstrings
- README.md: Auth section says "basic auth" but code uses OAuth2

ERROR HANDLING GAPS
- auth/oauth.py:34 -- HTTP call to provider with no timeout
- auth/oauth.py:56 -- bare `except:` swallows token exchange errors

PRIORITIZED SUMMARY
Critical (3):
  1. auth/oauth.py has 0% test coverage -- 4 public functions untested
  2. No timeout on OAuth HTTP call -- can hang forever
  3. OAUTH_CLIENT_SECRET missing from .env.example
```

### `/scan`

**When to use:** Full repository health check -- one command, all dimensions.

```
/scan
/scan quick
/scan src/payments/
```

Runs 3 parallel analysis tracks (security, code quality, operational health), deduplicates findings across tracks, applies cross-dimension severity uplift, and produces a unified report with scorecard + prioritized action list. See [ROLLOUT-GUIDE.md](ROLLOUT-GUIDE.md) for operational cadence.

### `/research`

**When to use:** Evaluating a technology, solving a hard problem, comparing approaches.

```
/research best practices for WebSocket reconnection in Python
/research FastAPI vs Litestar for our use case
```

Runs 3 parallel tracks: web search, codebase context, comparative analysis. Produces a structured report with summary, key findings, recommendation, alternatives table, code examples, risks, and sources.

---

## Sustain -- Keep Things Healthy

### `/document`

**When to use:** Docs are stale, new module needs docstrings, README needs updating.

```
/document README
/document src/payments/
/document API
```

Generates docs matching existing project style. **Always shows diffs** -- never silently overwrites.

### `/new-project`

**When to use:** Starting a new project or repo.

```
/new-project inventory-service "Microservice for warehouse inventory management"
```

Creates a `CLAUDE.md` with command table, architecture section, domain rules, gotchas, and `[TODO]` placeholders.

### `/learn`

**When to use:** After a gotcha, end of session, or any non-obvious discovery.

```
/learn pytest fixtures don't auto-discover from conftest in namespace packages
/learn from session
```

Classifies (project-specific, global, tool-usage, pattern), formats as one-liners, deduplicates, and presents as diffs for approval. The "from session" mode scans for tagged learnings, missed corrections, and user model observations.

### `/sync-memories`

**When to use:** Setting up a new machine or keeping multiple workstations in sync.

```
/sync-memories export
/sync-memories import
```

Exports knowledge to JSON, imports with conflict resolution (newer wins).

---

## Meta -- Level Up Your Prompts

### `/orchestrate`

**When to use:** Complex tasks that involve multiple concerns (architecture + implementation + testing + security).

```
/orchestrate Add a new payment processing module with Stripe integration
/orchestrate Refactor the auth system from sessions to JWT
```

1. Decomposes the task into independent + sequential subtasks
2. Asks for your approval of the plan
3. Dispatches specialized agents in parallel
4. Integrates results, resolves conflicts, verifies everything works

Agents discover things, pass findings to each other, escalate decisions to you, and adapt the plan mid-execution. The hierarchy: agents report to the orchestrator, the orchestrator escalates to you, your decisions flow back down to agents.

### `/metaprompt`

**When to use:** Any task where you want dramatically better results than a casual prompt would give you.

```
/metaprompt Refactor the authentication module to use JWT with refresh tokens
/metaprompt Review this codebase for production readiness
```

A metaprompt is a **prompt that generates advanced prompts**. It transforms your plain-language task into a phased execution plan with role definition, tool mapping, constraints, error anticipation, output format, and success criteria.

**The transformation:**

Basic prompt:
```
Refactor the authentication module to use JWT with refresh tokens
```

After `/metaprompt`:
```
Phase 1: Understand Current State (READ-ONLY)
Phase 2: Design (PLAN-ONLY)
Phase 3: Test First (TDD)
Phase 4: Implement
Phase 5: Verify & Harden
```

Each phase is mapped to the right tools. Every risk is anticipated. Agents execute it like a well-run project plan.

**Two modes:**
- **Use immediately** -- run the generated prompt right now for better results
- **Save as command** -- `.claude/commands/your-command.md` for the whole team

This is the **command that creates commands** -- how the toolkit grows itself.
