# Top 10 Commands — Cheat Sheet

The 10 commands you'll use most, ranked by daily frequency. Each shows real input and output.

---

## 1. `/status` — Where am I?

**When:** Start of every session. Before standup. Returning after lunch.

```
/status
```

```
Project Status
==============
Branch: feature/auth-refresh (3 commits ahead of origin/main)
Tests:  47 passed, 2 failed (test_auth.py)
Lint:   Clean
Deps:   1 outdated (fastapi 0.109 → 0.115)
Next:   Fix failing tests in test_auth.py, then push
```

One command, 5 seconds, full picture.

---

## 2. `/tdd` — Fix or build with tests

**When:** Every bug fix. Every new feature. The bread and butter.

```
/tdd Fix the token expiry validation bug
```

```
TDD Cycle Complete
==================
RED:      2 failing tests identified (test_login_expired_token, test_refresh_token)
GREEN:    Fixed token expiry check in src/auth/tokens.py:34
REFACTOR: Extracted validate_expiry() helper
Tests:    49 passed, 0 failed
```

Writes the failing test first, then the fix, then runs the full suite. Never ships untested code.

---

## 3. `/verify` — Safe to ship?

**When:** Before opening a PR. Before merging. Before deploying.

```
/verify
```

```
Verification Report
===================
Dependency check:  PASS
Lint:              PASS -- 0 issues
Type check:        PASS
Tests:             PASS -- 49/49 passed, 89% coverage
Build:             PASS
Git health:        PASS -- clean, 4 commits ahead
Config consistency:PASS

Overall: HEALTHY
```

Catches what you'd miss: stale .env.example, Docker build failures, missing deps.

**If it fails:** Fix the reported issue, then run `/verify` again. Don't push until green.

---

## 4. `/explain` — What does this code do?

**When:** Onboarding to new code. Before modifying unfamiliar modules.

```
/explain src/payments/
```

```
## High Level
Payment service: Stripe checkout -> webhook confirmation -> order fulfillment.

## Medium Level
POST /checkout -> create_session() -> Stripe redirect
                                        |
webhook /stripe/events -> verify_signature() -> process_event()
    +-- payment_intent.succeeded -> fulfill_order()
    +-- payment_intent.failed -> notify_user() + retry queue

Key files: checkout.py:45, webhooks.py:23, fulfillment.py:89

## Detail Level
- Webhook retries: 3 attempts, exponential backoff (webhooks.py:67)
- Idempotency key in Redis (checkout.py:52) -- prevents double charges
- Known quirk: Stripe sends duplicate events ~2% of the time (webhooks.py:31)
```

Three depth levels in one response. Ask for more detail on any part.

---

## 5. `/recall` — Has this been solved before?

**When:** Before starting work. Before making architectural decisions. "I feel like we've done this..."

```
/recall how we handle rate limiting
```

```
Found 3 relevant sources:

CLAUDE.md: "Rate limiting uses token bucket algorithm (src/middleware/rate_limit.py).
  Per-user: 100 req/min. Per-IP: 1000 req/min. Redis-backed."

Session 12 learning: "Discovered rate limiter doesn't apply to health check
  endpoints -- intentional, documented in middleware.py:23."

docs/API.md: "Rate limit headers: X-RateLimit-Remaining, X-RateLimit-Reset"
```

Searches CLAUDE.md, project docs, code, and session memory. Prevents solving the same problem twice.

---

## 6. `/commit-push-pr` — Ship it

**When:** Feature complete, tests passing, ready for review.

```
/commit-push-pr
```

```
Pre-flight checks:
  Tests:    PASS (49/49)
  Lint:     PASS

Created branch: feature/auth-refresh
Committed: "fix: validate token expiry before refresh"
Pushed to: origin/feature/auth-refresh
PR opened: https://github.com/org/repo/pull/142
  Title: "Fix token expiry validation"
  Reviewers: auto-assigned based on CODEOWNERS
```

**Won't push if tests fail.** That's the point — quality gate built in.

---

## 7. `/learn` — Remember this for next time

**When:** End of session. After discovering a gotcha. After a non-obvious fix.

```
/learn from session
```

```
Captured 3 learnings:

1. [AUTH] Token expiry check was comparing timestamps in different timezones.
   Fix: always normalize to UTC before comparison (tokens.py:34).

2. [TESTING] test_auth.py fixtures use freezegun for time mocking.
   Don't use datetime.now() directly in auth code.

3. [PATTERN] validate_expiry() helper extracted -- reuse for
   session tokens, API keys, and refresh tokens.

Saved to project memory. Available via /recall.
```

Next time anyone works on auth, `/recall auth tokens` finds these learnings.

---

## 8. `/diagnose` — WTF is this error?

**When:** Cryptic error message. Stack trace screenshot. "It just broke."

```
/diagnose [paste screenshot or error]
```

```
Diagnosis
=========
Error: ConnectionRefusedError at src/cache.py:12
Cause: Redis not running (expected on localhost:6379)

Root cause: Docker compose doesn't start Redis before the app.
  docker-compose.yml:15 missing depends_on for redis service.

Fix applied:
  docker-compose.yml:15 -- added depends_on: [redis]
  Tests: 49/49 passed
```

Accepts screenshots, stack traces, or plain text. Finds the root cause, not just the symptom.

---

## 9. `/team` — I need a squad on this

**When:** Complex task spanning multiple domains. You don't know which specialists to pick.

```
/team Add real-time notifications with WebSocket backend and toast UI
```

```
TEAM ASSEMBLY
=============
Stack detected: TypeScript, React, FastAPI, PostgreSQL, Docker
Task type: Feature
Complexity: Complex (multi-domain)

PROPOSED TEAM (7 agents)

LAYER 0 -- Analysis:
  [x] architect           reason: multi-domain feature needs blueprint
  [x] research-agent      reason: WebSocket library selection

LAYER 1 -- Implementation:
  [x] senior-fullstack-dev reason: React + FastAPI detected
  [x] tdd-agent           reason: new feature needs tests
  [x] database-engineer   reason: notification storage schema

LAYER 2 -- Review:
  [x] security-auditor    reason: WebSocket auth needed
  [x] code-reviewer       reason: standard review gate

Proceed? [yes/modify]
```

Auto-detects your stack, assembles the right team, executes layer by layer. You approve before anything runs.

---

## 10. `/orchestrate` — I know what needs to happen

**When:** You know the agents you want. Complex task with clear decomposition.

```
/orchestrate Refactor the auth module: extract token validation,
add refresh token rotation, update all tests
```

```
Decomposed into 4 workstreams:

1. architect     -- analyze current auth structure, produce refactoring blueprint
2. tdd-agent     -- write tests for new token rotation flow
3. senior-backend-dev -- implement extraction + rotation logic
4. security-auditor  -- review for token leakage, timing attacks

Executing Layer 0 (architect)...
```

Unlike `/team`, you control the decomposition. Use when you have a clear plan.

---

## Decision Tree: Which Command?

```
What do you need?
|
+-- "Understand something"
|   +-- Specific code/module? .............. /explain
|   +-- Prior decisions/context? ........... /recall
|   +-- "What commands should I use?" ...... /guide
|
+-- "Fix or build something"
|   +-- Single bug or feature? ............. /tdd
|   +-- Complex, multi-domain task?
|   |   +-- I know which agents ............ /orchestrate
|   |   +-- Auto-detect what's needed ...... /team
|   +-- Cryptic error/screenshot? .......... /diagnose
|
+-- "Ship something"
|   +-- Is it safe to ship? ................ /verify
|   +-- Yes, ship it ...................... /commit-push-pr
|
+-- "Remember something"
|   +-- Save learnings .................... /learn
|   +-- Search past learnings ............. /recall
```

---

## Daily Workflow Chain

```
Morning:
  /status                          -- where did I leave off?
  /recall [today's task topic]     -- any prior context?

Build:
  /explain [unfamiliar module]     -- understand before changing
  /tdd [feature or fix]            -- red-green-refactor
  /verify                          -- all green?

Ship:
  /commit-push-pr                  -- quality-gated push + PR

End of day:
  /learn from session              -- capture discoveries
```

---

## `/team` vs `/orchestrate` — When to Use Which

| | `/team` | `/orchestrate` |
|---|---------|----------------|
| **You know the stack?** | No -- it auto-detects | Yes -- you specify |
| **You know which agents?** | No -- it selects them | Yes -- you control |
| **Task complexity** | Any (redirects to `/tdd` if trivial) | Medium to complex |
| **Approval step** | Shows proposed team, waits for OK | Shows decomposition, waits for OK |
| **Layer execution** | Strict (0 -> 1 -> 2 -> 3 -> 4) | Strict (same layers) |
| **Best for** | "I need help and don't know where to start" | "I have a plan, execute it with specialists" |

**Rule of thumb:** Use `/team` when exploring. Use `/orchestrate` when you have a blueprint.
