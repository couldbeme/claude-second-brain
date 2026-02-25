# Claude Code Team Toolkit

### 15 Slash Commands + 7 Agents for High-Quality Development

Slash commands are reusable workflow prompts for Claude Code. Type `/command-name` and Claude follows a structured process instead of ad-hoc prompting. Agents are specialized subprocesses that handle focused tasks autonomously.

This toolkit codifies engineering best practices into repeatable, quality-enforced workflows.

---

## Quick Start (5 minutes)

### 1. Install the commands and agents

```bash
# Clone the toolkit
git clone <repo-url> claude-code-team-toolkit

# Copy commands (pick one)
cp -r claude-code-team-toolkit/commands/ ~/.claude/commands/        # global (all projects)
cp -r claude-code-team-toolkit/commands/ .claude/commands/          # project-only

# Copy agents
cp -r claude-code-team-toolkit/agents/ ~/.claude/agents/            # global
```

### 2. Set up your project's CLAUDE.md

```bash
# Open Claude Code in your project, then:
/new-project my-service "Brief description of what it does"
```

This creates a `.claude/CLAUDE.md` with a command table, architecture section, and placeholders. Fill it in as you go.

### 3. Optional: install the global CLAUDE.md

Copy `CLAUDE.md.template` to `~/.claude/CLAUDE.md` and customize it. This gives Claude Code consistent rules across all your projects (TDD, security, communication style).

### 4. Start using commands

```
/status                           # see where things stand
/explain src/auth/                # understand unfamiliar code
/tdd Add input validation         # build with tests first
/verify                           # check project health
/commit-push-pr                   # ship it
```

---

## Commands at a Glance

| Command | What it does |
|---------|-------------|
| `/status` | Instant progress report -- git state, tests, next steps |
| `/explain` | 3-level code explainer with ASCII diagrams |
| `/tdd` | Strict red-green-refactor TDD cycle |
| `/verify` | 7-step health check with traffic-light report |
| `/commit-push-pr` | Quality-gated commit, push, and PR |
| `/document` | Generate/update docs -- always shows diffs |
| `/new-project` | Scaffold project with CLAUDE.md template |
| `/learn` | Capture learnings into CLAUDE.md |
| `/recall` | Search project knowledge base |
| `/audit` | Full 5-dimension codebase audit with scorecard |
| `/gap-analysis` | Find missing tests, docs, error handling, types |
| `/research` | Deep 3-track technical research with sources |
| `/orchestrate` | Decompose complex tasks into multi-agent workflows |
| `/metaprompt` | Generate optimized slash commands from a task description |
| `/sync-memories` | Export/import knowledge between machines |

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

```
/gap-analysis src/auth/

Claude:
  Gap Analysis: src/auth/
  ========================

  TEST COVERAGE GAPS
  | Source File       | Test File          | Tested          | Untested              | Gap  |
  |-------------------|--------------------|-----------------|----------------------|------|
  | auth/middleware.py | tests/test_auth.py | login, logout   | refresh_token, revoke | 50%  |
  | auth/oauth.py     | (none)             | --              | ALL (4 functions)     | 100% |
  | auth/permissions.py| tests/test_perms.py| check_role      | check_resource_owner  | 50%  |

  DOCUMENTATION GAPS
  - auth/oauth.py: No module docstring, no function docstrings
  - auth/middleware.py: Missing docstring on refresh_token()
  - README.md: Auth section says "basic auth" but code uses OAuth2

  ERROR HANDLING GAPS
  - auth/oauth.py:34 -- HTTP call to provider with no timeout
  - auth/oauth.py:56 -- bare `except:` swallows token exchange errors
  - auth/middleware.py:78 -- token decode with no InvalidTokenError handling

  TYPE SAFETY GAPS
  - auth/permissions.py:12 -- check_resource_owner(user, resource) → no type hints
  - auth/oauth.py:23 -- returns `Any` where `OAuthToken` would be specific

  CONFIG GAPS
  - OAUTH_CLIENT_SECRET used in oauth.py:8 but not in .env.example
  - TOKEN_EXPIRY_SECONDS has no default (crashes if not set)

  PRIORITIZED SUMMARY
  Critical (3):
    1. auth/oauth.py has 0% test coverage -- 4 public functions untested
    2. No timeout on OAuth HTTP call (auth/oauth.py:34) -- can hang forever
    3. OAUTH_CLIENT_SECRET missing from .env.example -- breaks new dev setup

  Important (4):
    4. refresh_token() and revoke() untested in middleware
    5. Bare except swallowing token errors
    6. README auth section outdated
    7. Missing type hints on public interface

  Nice to have (2):
    8. Add module docstring to oauth.py
    9. Specific return types instead of Any
```

### `/research`

**When to use:** Evaluating a technology, solving a hard problem, comparing approaches.

```
/research best practices for WebSocket reconnection in Python
/research FastAPI vs Litestar for our use case
```

Runs 3 parallel tracks: web search, codebase context, comparative analysis. Produces a structured report with summary, key findings, recommendation, alternatives table, code examples, risks, and sources.

```
/research FastAPI vs Litestar for our use case

Claude: Launching 3 research tracks in parallel...

  [Track A: Web] Searching official docs, benchmarks, recent articles
  [Track B: Codebase] Checking existing framework usage and patterns
  [Track C: Comparison] Finding migration stories, performance data

  Research Report: FastAPI vs Litestar
  ====================================

  Summary:
  FastAPI is the safer choice for your team (existing FastAPI experience,
  large ecosystem). Litestar has better performance and a cleaner DI system
  but a smaller community. For a new microservice, either works. For your
  existing codebase, stay with FastAPI.

  Key Findings:
  - Litestar benchmarks show 15-20% faster response times (source: TechEmpower R22)
  - FastAPI has 10x more Stack Overflow answers and 5x more third-party plugins
  - Your codebase already uses FastAPI in 3 services (src/api/, src/gateway/, src/admin/)
  - Litestar's dependency injection is compile-time checked; FastAPI's is runtime
  - Both support OpenAPI 3.1, async, Pydantic v2

  Recommended Approach:
  Stay with FastAPI. The migration cost outweighs Litestar's performance gains
  for your use case (API gateway, not compute-heavy). If you start a new
  standalone service with no shared code, Litestar is worth evaluating.

  Alternatives Considered:
  | Framework | Pros                     | Cons                        |
  |-----------|--------------------------|-----------------------------|
  | FastAPI   | Ecosystem, team knows it | Slower DI, Starlette-bound  |
  | Litestar  | Faster, better DI        | Smaller community, migration|
  | Django RF | Batteries included       | Async is bolted on, heavy   |
  | Starlette | Minimal, fast            | No built-in validation/docs |

  Risks & Gotchas:
  - Litestar changed name from Starlite (v2.0) -- older articles use wrong name
  - FastAPI depends on Starlette; Starlette deprecations affect FastAPI
  - Mixing frameworks across services adds onboarding cost

  Sources:
  - https://litestar.dev/benchmarks -- official Litestar benchmarks
  - https://fastapi.tiangolo.com -- official docs
  - https://www.techempower.com/benchmarks -- TechEmpower Round 22
  - [your codebase] src/api/main.py, src/gateway/app.py -- existing FastAPI usage
```

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

```
/document src/payments/

Claude:
  Assessed current documentation state:
  - src/payments/processor.py: 6 public functions, 0 docstrings
  - src/payments/webhooks.py: 3 public functions, 1 outdated docstring
  - src/payments/models.py: has docstrings but missing usage examples
  - No module-level README

  Generating documentation...

  --- /dev/null
  +++ src/payments/README.md
  @@ -0,0 +1,18 @@
  +# Payments Module
  +
  +Handles Stripe checkout, webhook verification, and order fulfillment.
  +
  +## Flow
  +  POST /checkout → create_session() → Stripe redirect
  +  Webhook /stripe/events → verify_signature() → process_event()
  +
  +## Key files
  +  - processor.py -- checkout and refund logic
  +  - webhooks.py -- Stripe event handling with idempotency
  +  - models.py -- Payment, Refund, Subscription data models

  --- a/src/payments/processor.py
  +++ b/src/payments/processor.py
  @@ -12,0 +13,8 @@
  +def create_checkout_session(user_id: str, items: list[CartItem]) -> str:
  +    """Create a Stripe checkout session and return the redirect URL.
  +
  +    Args:
  +        user_id: The authenticated user's ID.
  +        items: Cart items to include in the session.
  +
  +    Returns:
  +        Stripe checkout URL for client redirect.
  +
  +    Raises:
  +        PaymentError: If Stripe API call fails.
  +    """

  --- a/src/payments/webhooks.py
  +++ b/src/payments/webhooks.py
  @@ -8,1 +8,1 @@
  -    """Handle webhook."""
  +    """Verify Stripe webhook signature and dispatch to event handlers.
  +
  +    Events: payment_intent.succeeded, payment_intent.failed,
  +    charge.refunded. Unknown events are logged and ignored.
  +    """

  Apply these changes? [yes / edit / skip]
```

### `/new-project`

**When to use:** Starting a new project or repo.

```
/new-project inventory-service "Microservice for warehouse inventory management"
```

Creates a `CLAUDE.md` with command table, architecture section, domain rules, gotchas, and `[TODO]` placeholders.

```
/new-project inventory-service "Microservice for warehouse inventory management"

Claude: Created .claude/CLAUDE.md:

  # inventory-service

  Microservice for warehouse inventory management.

  ## Commands
  | Command | Description |
  |---------|-------------|
  | `[TODO]` | Add project-specific commands as they emerge |

  ## Architecture
  - **Stack**: [TODO: e.g., Python/FastAPI, Node/Express]
  - **Database**: [TODO: e.g., PostgreSQL, MongoDB]
  - **Entry point**: [TODO: e.g., src/main.py]
  - **Test runner**: [TODO: e.g., pytest, jest]

  ## Domain Rules
  - [TODO: Business logic constraints, e.g., "inventory can never go negative"]

  ## Gotchas
  - [TODO: Non-obvious things about this project]

  ## Patterns
  - [TODO: Team conventions, e.g., "all endpoints return {data, error, meta}"]

  Fill in the [TODO] sections as you build. Claude reads this at every
  session start -- the more you add, the less context you need to provide.
```

### `/learn`

**When to use:** After a gotcha, end of session, or any non-obvious discovery.

```
/learn pytest fixtures don't auto-discover from conftest in namespace packages
/learn from session
```

Classifies (project-specific, global, tool-usage, pattern), formats as one-liners, deduplicates, and presents as diffs for approval.

### `/sync-memories`

**When to use:** Setting up a new machine or keeping multiple workstations in sync.

```
/sync-memories export
/sync-memories import
```

Exports knowledge to JSON, imports with conflict resolution (newer wins).

```
/sync-memories export

Claude: Exporting project knowledge...

  Sources collected:
  - CLAUDE.md: 42 lines (architecture, gotchas, patterns)
  - .claude/memory/: 3 topic files (debugging.md, patterns.md, api-notes.md)
  - Memory DB: 23 memories (filtered to this project)

  Exported to: .claude/knowledge-export-2024-11-15.json
  Total entries: 31 (deduplicated)
  Size: 18KB

  Transfer this file to your other machine, then run:
  /sync-memories import .claude/knowledge-export-2024-11-15.json

--- on the other machine ---

/sync-memories import .claude/knowledge-export-2024-11-15.json

Claude: Importing 31 entries...

  New:        24 entries added
  Conflicts:   4 entries (newer version wins)
  Duplicates:  3 entries skipped (already exist)

  Conflict resolution:
  - "Redis caching pattern" -- local: Nov 10, import: Nov 14 → kept import (newer)
  - "DB migration workflow" -- local: Nov 12, import: Nov 8 → kept local (newer)
  - ...

  Import complete. Your knowledge base is now in sync.
```

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

#### How agents coordinate: the full communication flow

The real power of `/orchestrate` isn't just parallel execution -- it's that agents **discover things, pass findings to each other, escalate decisions, and adapt the plan mid-execution**. Here's what actually happens inside:

```
/orchestrate Add real-time notifications with WebSocket support,
             email fallback, and user preference management

═══════════════════════════════════════════════════════════
PHASE 1: DECOMPOSITION — Orchestrator analyzes the task
═══════════════════════════════════════════════════════════

Orchestrator: I see 4 workstreams with dependencies:

  ┌─────────────┐
  │  architect   │ ← designs the whole thing first
  └──────┬──────┘
         │ blueprint
    ┌────┴────┐
    ▼         ▼
┌────────┐ ┌────────┐
│tdd-agent│ │tdd-agent│  ← implement in parallel
│WebSocket│ │  Email  │
└────┬───┘ └────┬───┘
     │          │
     ▼          ▼
  ┌──────────────┐
  │security-audit│  ← review AFTER implementation
  └──────┬───────┘
         │
         ▼
  ┌──────────────┐
  │ verification │  ← final check
  └──────────────┘

Approve? [yes]

═══════════════════════════════════════════════════════════
PHASE 2: DISPATCH — Agents execute with real-time feedback
═══════════════════════════════════════════════════════════

[architect agent starts]

  architect → orchestrator:
    "Blueprint complete. Found an existing notification service at
     src/notifications/sms.py that uses the same event bus pattern.
     RECOMMENDATION: Reuse EventBus (src/events/bus.py) rather than
     creating a new pub/sub system. This keeps the architecture
     consistent and avoids a second message broker.

     Blueprint: 6 files, 3 interfaces defined.
     Passing to implementation agents."

  orchestrator: Good. Adjusting tdd-agent instructions to use
    existing EventBus instead of new pub/sub.

  ┌─ tdd-agent (WebSocket) starts ─────────────────────────
  │
  │  tdd-agent-ws → orchestrator:
  │    "Writing tests first. Found a problem: the existing
  │     EventBus (bus.py:34) is synchronous. WebSocket handlers
  │     need async. Two options:
  │     (a) Make EventBus async (breaking change, 12 call sites)
  │     (b) Create AsyncEventBus adapter that wraps the sync one
  │
  │     ESCALATING TO USER — this affects existing code."
  │
  │  orchestrator → user:
  │    "The WebSocket agent found that your EventBus is sync but
  │     WebSockets need async. Options:
  │     (a) Rewrite EventBus to async — cleaner but touches 12 files
  │     (b) Async adapter — no breaking changes, slight complexity
  │     Recommendation: (b) adapter, lower risk."
  │
  │  user: "Go with the adapter."
  │
  │  orchestrator → tdd-agent-ws:
  │    "User chose async adapter. Proceed with option (b).
  │     Do NOT modify the existing EventBus."
  │
  │  tdd-agent-ws → orchestrator:
  │    "Done. AsyncEventBus adapter created. 14 tests, all passing.
  │     Files: src/events/async_bus.py, src/ws/handler.py,
  │     src/ws/connection_manager.py, tests/test_ws.py"
  │
  └────────────────────────────────────────────────────────

  ┌─ tdd-agent (Email) runs in parallel ───────────────────
  │
  │  tdd-agent-email → orchestrator:
  │    "Tests written. Implementation complete. Used existing
  │     EventBus (sync is fine for email — it's queued anyway).
  │     CONCERN: No rate limiting on email sends. Should I add it?
  │     Currently out of scope but it's a production risk."
  │
  │  orchestrator: Rate limiting is a new concern. Logging it
  │    but not blocking — will include in final report.
  │
  │  tdd-agent-email → orchestrator:
  │    "Done. 11 tests, all passing.
  │     Files: src/notifications/email.py, src/notifications/
  │     templates/, tests/test_email_notifications.py"
  │
  └────────────────────────────────────────────────────────

═══════════════════════════════════════════════════════════
PHASE 2b: SECURITY REVIEW — Findings feed back into plan
═══════════════════════════════════════════════════════════

  [security-auditor reviews ALL changes from both agents]

  security-auditor → orchestrator:
    "3 findings:

     CRITICAL: WebSocket handler accepts connections without
     authentication check (handler.py:23). Any client can
     connect and receive all notifications.
     → FIX: Add JWT verification in connection upgrade.

     HIGH: Email templates use string concatenation for user
     data (templates/notify.html:15). XSS vector if email
     client renders HTML.
     → FIX: Use Jinja2 autoescaping.

     LOW: AsyncEventBus adapter logs full message payloads
     at DEBUG level (async_bus.py:45). Could leak PII in logs.
     → FIX: Redact or hash sensitive fields."

  orchestrator: CRITICAL finding. Dispatching fix agents
    before proceeding to verification.

  orchestrator → tdd-agent-ws:
    "Security found: no auth on WebSocket connections.
     Add JWT verification to the connection upgrade handler.
     Write a failing test first:
     - test_unauthenticated_ws_rejected
     - test_expired_token_ws_rejected
     - test_valid_token_ws_accepted"

  orchestrator → tdd-agent-email:
    "Security found: XSS in email templates.
     Switch to Jinja2 autoescaping. Add test:
     - test_html_injection_escaped_in_email"

  [both agents fix in parallel]

  tdd-agent-ws → orchestrator:
    "Fixed. 3 new tests + middleware added. All 17 tests pass."

  tdd-agent-email → orchestrator:
    "Fixed. Jinja2 autoescaping enabled. 1 new test. All 12 pass."

═══════════════════════════════════════════════════════════
PHASE 3: INTEGRATION — Merge, verify, resolve conflicts
═══════════════════════════════════════════════════════════

  orchestrator: Checking for conflicts between agents...
    - Both agents created __init__.py in src/notifications/
      → Merging: combined exports from both
    - No other file conflicts.

  [verification-agent runs]

  verification-agent → orchestrator:
    "Full pipeline:
     Lint:       PASS
     Type check: PASS
     Tests:      PASS — 29 new tests, 76 total, all green
     Build:      PASS

     Integration test: Started WebSocket server, connected
     with valid JWT, triggered email event, verified both
     WS message received AND email queued. PASS."

═══════════════════════════════════════════════════════════
PHASE 4: REPORT TO USER
═══════════════════════════════════════════════════════════

  Done. Here's what happened:

  | Agent | Task | Output |
  |-------|------|--------|
  | architect | System design | Blueprint, identified EventBus reuse |
  | tdd-agent | WebSocket impl | 5 files, 17 tests |
  | tdd-agent | Email impl | 4 files, 12 tests |
  | security-auditor | Security review | 3 findings (all fixed) |
  | verification-agent | Final check | All green |

  Key decisions made:
  - Used async adapter (your choice) instead of rewriting EventBus
  - Fixed auth-less WebSocket (security-auditor caught it)
  - Fixed XSS in email templates (security-auditor caught it)

  Flagged for future:
  - Email rate limiting not implemented (out of scope, but recommended)
  - DEBUG logging may leak PII (LOW severity, async_bus.py:45)

  Total: 9 files, 29 tests, 2 security fixes, 0 regressions.

  [LEARNING] EventBus is sync — use AsyncEventBus adapter for
  async consumers. Don't rewrite the sync bus.
  [LEARNING] WebSocket handlers need auth middleware — added to
  project patterns.
```

**What just happened:**

1. **Architect discovered** an existing pattern (EventBus) and recommended reuse — saving an entire pub/sub implementation
2. **TDD agent found a blocker** (sync EventBus) and **escalated to the user** through the orchestrator with options and a recommendation
3. **Security agent reviewed ALL code** from both implementation agents and found 3 issues including a critical auth bypass
4. **Orchestrator dispatched fix agents** before allowing verification — critical findings block the pipeline
5. **Fix agents wrote tests first** for the security fixes, proving they work
6. **Verification agent ran the full pipeline** including an integration test across both subsystems
7. **Report included** decisions made, findings caught, and items flagged for future work
8. **Learnings saved** so next session already knows about the async adapter pattern

The hierarchy: **agents report to the orchestrator, the orchestrator escalates to you, your decisions flow back down to agents.** Nothing ships without your approval. Nothing ships without verification. And everything learned gets saved.

### `/metaprompt`

**When to use:** Any task where you want dramatically better results than a casual prompt would give you.

```
/metaprompt Refactor the authentication module to use JWT with refresh tokens
/metaprompt Review this codebase for production readiness
/metaprompt I always do the same 5 steps when adding a new API endpoint -- make a command for it
```

#### What is a metaprompt and why does it matter?

A metaprompt is a **prompt that generates advanced prompts**. It's the difference between telling Claude "fix the auth" and giving Claude a structured, phased execution plan with constraints, tool assignments, error handling, and verification steps -- the kind of prompt that a senior prompt engineer would spend 20 minutes crafting by hand.

**The problem it solves:** Claude Code is powerful, but it's only as good as the instructions it receives. A vague prompt produces vague results. A well-engineered prompt produces precise, reliable, high-quality results. But most developers aren't prompt engineers -- they shouldn't have to be.

`/metaprompt` bridges that gap. You describe your task in plain language. It transforms your input into an advanced, agent-optimized prompt by applying:

- **Role definition** — Gives Claude a clear identity and expertise level for the task
- **Phased execution plan** — Breaks work into ordered steps with dependencies, so agents execute in the right sequence
- **Tool mapping** — Assigns the right Claude Code tools to each phase (Glob for discovery, Read for analysis, Edit for changes, Bash for verification, subagents for parallelization)
- **Constraints and guardrails** — Defines what NOT to do, preventing common mistakes before they happen
- **Error anticipation** — Pre-identifies what could go wrong and builds in recovery paths
- **Output format** — Specifies exactly how results should be structured, so you get actionable output instead of walls of text
- **Success criteria** — Defines what "done" looks like, so Claude doesn't stop early or over-engineer

The result is a prompt that Claude's agents and tools execute at maximum effectiveness -- structured for how the system actually works internally.

#### The transformation: basic prompt vs. metaprompt

Watch what happens to the same task:

**Basic prompt (what most people type):**
```
Refactor the authentication module to use JWT with refresh tokens
```

Claude will try its best, but it's guessing at scope, order of operations, safety constraints, and what "done" means. It might start coding before understanding the existing auth flow. It might miss edge cases. It might not test.

**After `/metaprompt` transforms it:**
```
/metaprompt Refactor the authentication module to use JWT with refresh tokens

Claude analyzes your task and generates:
```

```markdown
# JWT Authentication Refactor

Refactor existing session-based auth to JWT with refresh token rotation.

## Phase 1: Understand Current State (READ-ONLY)

- Use Glob to map all auth-related files: middleware, routes, models, tests
- Read each file. Document: current session mechanism, token storage,
  protected routes, existing test coverage
- Identify all integration points (what breaks when auth changes)
- Output: dependency map showing what touches auth
- DO NOT modify any files in this phase

## Phase 2: Design (PLAN-ONLY)

- Propose JWT structure: access token (short-lived), refresh token (long-lived)
- Map migration path: session → JWT without breaking existing clients
- Identify security requirements: token rotation, blacklisting, CSRF protection
- Present design to user for approval before proceeding
- STOP if the existing auth has patterns you don't understand -- ASK

## Phase 3: Test First (TDD)

Write failing tests BEFORE any implementation:
- test_jwt_generation: valid token contains expected claims
- test_jwt_expiration: expired access token returns 401
- test_refresh_rotation: refresh token is single-use, issues new pair
- test_refresh_expiration: expired refresh token requires re-login
- test_blacklist: revoked token is rejected
- test_concurrent_sessions: multiple devices work independently
- Verify: all tests FAIL (they should -- nothing is implemented yet)

## Phase 4: Implement

- Implement JWT generation, validation, refresh rotation
- Update middleware to check JWT instead of session
- Add token blacklist for logout/revocation
- Each implementation step: run tests, verify the newly-targeted test passes
- DO NOT change any test to make it pass -- fix the implementation

## Phase 5: Verify & Harden

- Run full test suite (not just auth tests) -- catch regressions
- Run security-auditor agent: check for token leakage, timing attacks,
  missing HTTPS enforcement
- Verify: all tests pass, no security findings >= medium severity
- Output: summary of changes, files modified, test results, security scan
```

**The difference is night and day.** The basic prompt hopes Claude figures it out. The metaprompt-engineered version tells Claude exactly how to think about the problem -- phased execution, read-before-write, test-before-code, security verification, human checkpoints. Every phase is mapped to the right tools. Every risk is anticipated. Agents pick this up and execute it like a well-run project plan.

#### Practical walkthrough: one-time task vs. reusable command

`/metaprompt` works for both:

**One-time use — run it right now:**
```
/metaprompt Review this PR for security vulnerabilities, focusing on
auth bypass and injection attacks

Claude: [generates an advanced security review prompt]
        [applies it immediately to the current codebase]
        [structured output: severity-ranked findings with remediation]
```

You get expert-level prompt engineering applied to your task in seconds. No saving, no command file -- just better results right now.

**Reusable command — save it for the team:**
```
/metaprompt Every time we add a new microservice we do the same 5 things:
repo structure, Dockerfile, CI pipeline, health check, service mesh registration.
Make a command for it.

Claude: [generates /new-service command with 5 phases, validation,
         verification, and output format]

        Options:
        1. Use immediately -- execute this for the current task
        2. Save as slash command -- .claude/commands/new-service.md
        3. Iterate -- "add a database migration step"

You: "Save it"

Now anyone on the team:
/new-service payments --port 8042 --template python
[follows every phase perfectly, every time]
```

The command-saving flow is how the toolkit grows: `/metaprompt` generates a command, you review it, save it, and PR it to the team repo. What took one person 30 minutes of prompt crafting becomes a one-liner for everyone.

#### Why this is the most important command in the toolkit

Every other command in this toolkit -- `/tdd`, `/audit`, `/verify`, `/explain` -- was built using the same prompt engineering principles that `/metaprompt` applies automatically. It's the **command that creates commands**.

But more importantly: even if you never save a single command, `/metaprompt` makes you better at using Claude Code immediately. The quality gap between a basic prompt and a metaprompt-engineered prompt is the gap between "Claude is a nice helper" and "Claude is a senior engineer who follows a rigorous process."

Three levels of impact:

1. **Individual** — Your prompts produce better results right now, without prompt engineering expertise
2. **Team** — Crystallize your best workflows into reusable commands anyone can run
3. **Organization** — The toolkit grows itself. 15 commands become 30, then 50. Every recurring workflow becomes a one-liner

---

## Agents

Agents are specialized subprocesses that commands dispatch for focused tasks. You don't call agents directly -- commands like `/orchestrate` and `/audit` use them automatically. Each agent has a focused role, specific tools, and a defined output format.

| Agent | Role | Specialization |
|-------|------|---------------|
| **architect** | Design | Analyzes codebase patterns, produces implementation blueprints with file paths and interfaces |
| **tdd-agent** | Implement | Strict TDD -- never writes code before a failing test |
| **security-auditor** | Security | OWASP checklist with severity ratings and specific fixes |
| **code-reviewer** | Review | Confidence-scored issue detection (only reports >= 75/100) |
| **documentation-agent** | Docs | Generates accurate, concise docs -- always as diffs |
| **research-agent** | Research | Multi-source investigation with citations and conflict detection |
| **verification-agent** | QA | Sequential test pipeline with traffic-light reporting |

### What each agent actually produces

#### architect

Dispatched first in most `/orchestrate` workflows. Reads the codebase to extract existing patterns, then produces a blueprint that downstream agents follow.

```
architect agent output:

  CODEBASE ANALYSIS
  Existing patterns found:
  - File structure: src/{module}/routes.py, schemas.py, service.py, models.py
  - Error handling: all routes use AppError(status, message, code) (see src/core/errors.py:12)
  - DB pattern: Repository classes in models.py, no raw SQL (see src/users/models.py:23)
  - Tests: mirror structure in tests/{module}/test_*.py, uses conftest.py fixtures

  BLUEPRINT: Notifications Module
  Files to create:
    src/notifications/routes.py       -- POST /notifications, GET /notifications/{id}
    src/notifications/schemas.py      -- NotificationCreate, NotificationResponse (Pydantic)
    src/notifications/service.py      -- NotificationService.send(), .get(), .mark_read()
    src/notifications/models.py       -- NotificationRepo (follows existing Repository pattern)
    tests/notifications/test_routes.py
    tests/notifications/conftest.py

  Interfaces:
    class NotificationService:
        async def send(self, user_id: str, channel: Channel, payload: dict) -> Notification
        async def get(self, notification_id: str) -> Notification | None
        async def mark_read(self, notification_id: str) -> None

  Data flow:
    POST /notifications → validate(NotificationCreate) → NotificationService.send()
      → NotificationRepo.create() → EventBus.emit("notification.sent") → return 201

  Build sequence:
    1. models.py + schemas.py (no dependencies)
    2. service.py (depends on models)
    3. routes.py (depends on service + schemas)
    4. tests (after all implementation)

  Context files for downstream agents:
    src/core/errors.py, src/users/models.py, src/events/bus.py,
    tests/users/conftest.py (for fixture patterns)
```

#### tdd-agent

The implementation workhorse. Receives blueprints from architect and implements using strict red-green-refactor. Never writes a line of production code without a failing test first.

```
tdd-agent output:

  TDD Cycle 1: NotificationService.send()
  ────────────────────────────────────────

  RED — wrote failing test:
    tests/notifications/test_service.py:
      test_send_creates_notification_in_db()
      test_send_emits_event_on_bus()
      test_send_raises_on_invalid_channel()
    Result: 3 FAILED (expected -- no implementation yet)

  GREEN — minimal implementation:
    src/notifications/service.py: NotificationService.send()
    src/notifications/models.py: NotificationRepo.create()
    Result: 3 PASSED ✓

  REFACTOR — extracted Channel validation to schema layer
    Result: 3 PASSED ✓ (no behavior change)

  TDD Cycle 2: NotificationService.get()
  ────────────────────────────────────────

  RED — test_get_returns_notification, test_get_returns_none_for_missing
    Result: 2 FAILED ✓

  GREEN — implemented get() with repo lookup
    Result: 2 PASSED ✓ (total: 5/5)

  TDD Cycle 3: NotificationService.mark_read()
  ──────────────────────────────────────────────

  RED — test_mark_read_updates_status, test_mark_read_raises_on_missing
    Result: 2 FAILED ✓

  GREEN — implemented mark_read()
    Result: 2 PASSED ✓ (total: 7/7)

  Summary:
  Files created: service.py, models.py, test_service.py, conftest.py
  Tests: 7 written, 7 passing
  Full suite: 84/84 passing (no regressions)
```

#### security-auditor

Reviews code for OWASP top 10, secret exposure, and unsafe patterns. Each finding has severity, evidence, and a specific fix.

```
security-auditor output:

  SECURITY AUDIT — src/notifications/
  3 findings (0 critical, 1 high, 1 medium, 1 low)

  [SEVERITY: HIGH]
  File: src/notifications/routes.py:34
  Issue: User can request any notification by ID without ownership check
  Evidence:
    @router.get("/notifications/{id}")
    async def get_notification(id: str):
        return await service.get(id)  # no user_id check
  Fix: Add ownership verification:
    notification = await service.get(id)
    if notification.user_id != current_user.id:
        raise AppError(403, "Not your notification")

  [SEVERITY: MEDIUM]
  File: src/notifications/service.py:45
  Issue: Email channel sends notification payload as-is — if payload contains
         user-controlled HTML, downstream email renderer may be vulnerable to XSS
  Evidence:
    await email_client.send(user.email, payload["body"])  # unescaped
  Fix: Sanitize payload before passing to email renderer:
    from markupsafe import escape
    await email_client.send(user.email, escape(payload["body"]))

  [SEVERITY: LOW]
  File: src/notifications/models.py:12
  Issue: notification_id uses sequential integers — allows enumeration
  Fix: Switch to UUID4 for notification IDs

  No secrets found in source. .env is gitignored. ✓
```

#### code-reviewer

Reviews code changes (usually via git diff) and reports only issues with confidence >= 75/100. No nitpicks — real bugs only.

```
code-reviewer output:

  Code Review — 4 files changed (+187, -23)

  Confidence: 95/100
  File: src/notifications/service.py:67
  Issue: Race condition in mark_read(). Two concurrent requests could both
         read status="unread", both attempt update, second silently succeeds
         on already-read notification.
  Suggestion: Use UPDATE ... WHERE status = 'unread' RETURNING id; if no rows
              returned, the notification was already marked read.

  Confidence: 85/100
  File: src/notifications/routes.py:52
  Issue: POST /notifications returns 200 instead of 201 for resource creation.
  Suggestion: Change `return notification` to `return Response(notification, status_code=201)`

  Confidence: 80/100
  File: tests/notifications/test_service.py:23
  Issue: test_send_creates_notification_in_db() doesn't verify the notification
         content — only checks that a row was created. Could pass even if data
         is wrong.
  Suggestion: Assert notification.channel == expected_channel and
              notification.payload == expected_payload.

  No issues below 75 threshold. 4 other observations logged but below confidence cutoff.
```

#### documentation-agent

Generates documentation that matches the project's existing style. Always presents changes as diffs — never overwrites silently. Prioritizes accuracy over completeness.

```
documentation-agent output:

  Documentation update for src/notifications/
  Assessed: 4 source files, 0 existing docs

  --- /dev/null
  +++ src/notifications/README.md
  @@ -0,0 +1,22 @@
  +# Notifications Module
  +
  +Handles multi-channel notifications (in-app, email, push).
  +
  +## Architecture
  +  routes.py → service.py → models.py (DB) + EventBus
  +
  +## Endpoints
  +  POST /notifications    Create and send a notification
  +  GET  /notifications/:id  Retrieve a notification (owner only)
  +  PATCH /notifications/:id/read  Mark as read
  +
  +## Adding a new channel
  +  1. Add to Channel enum in schemas.py
  +  2. Add handler in service.py:_dispatch_by_channel()
  +  3. Add tests for the new channel in test_service.py

  --- a/src/notifications/service.py
  +++ b/src/notifications/service.py
  @@ -1,0 +1,4 @@
  +"""Notification delivery service.
  +
  +Dispatches notifications via channel (email, push, in-app) and persists
  +delivery status. All operations emit events to the EventBus.
  +"""

  3 files updated. Apply changes? [yes / edit / skip]
```

#### research-agent

Dispatched by `/orchestrate` or `/research` for technical investigation. Searches multiple sources, cross-references findings, and flags conflicting information.

```
research-agent output:

  Research: "async task queue options for our Python stack"

  Summary:
  Celery is the mature choice with the largest ecosystem. Dramatiq is simpler
  and faster but has fewer integrations. For your stack (FastAPI + Redis already
  running), either works — Celery if you need complex workflows, Dramatiq if
  you want simplicity.

  Key Findings:
  - Celery 5.x supports async (source: docs.celeryq.dev, Jan 2025)
  - Dramatiq benchmarks: 2-3x faster task throughput vs Celery (source: GitHub/Bogdanp/dramatiq)
  - Your project already has Redis (src/core/cache.py:5) — both can use it as broker
  - Celery has 2.1M monthly PyPI downloads vs Dramatiq's 180K
  - Conflict: One source claims Celery doesn't support FastAPI async — INCORRECT,
    Celery 5.3+ works with async via asyncio.run() in tasks (verified in official docs)

  Recommendation:
  Celery — your team's existing Redis + need for scheduled tasks + retries with
  visibility dashboard (Flower) makes it the better fit despite extra complexity.

  Risks & Gotchas:
  - Celery's config is complex — use celery.conf module not flat settings
  - If using Pydantic models as task args, serialize with .model_dump() not pickle
  - Dramatiq's simpler API means faster onboarding if team is small

  Sources:
  - docs.celeryq.dev/en/stable/whatsnew-5.3.html
  - github.com/Bogdanp/dramatiq#benchmarks
  - [codebase] src/core/cache.py — existing Redis connection
```

#### verification-agent

The final gate. Runs a sequential pipeline: dependencies → lint → tests → build → smoke test. Outputs a traffic-light report. Any FAIL includes exact error output and suggested fix.

```
verification-agent output:

  VERIFICATION RESULTS
  ====================
  Dependencies:  PASS  All imports resolve, requirements.txt in sync
  Lint:          PASS  0 issues (ruff checked 47 files)
  Unit tests:    PASS  84/84 passed (12.3s)
  Integration:   PASS  API endpoints return expected responses
  Build:         FAIL  Docker build fails at step 8/10
                       ERROR: pip install fails — notifications requires
                       markupsafe>=2.1 but Dockerfile pins markupsafe==2.0.1
                       → Fix: Update Dockerfile: markupsafe==2.0.1 → markupsafe>=2.1.0
  Smoke test:    SKIP  (blocked by build failure)

  OVERALL: RED

  Action required:
  1. Fix markupsafe version pin in Dockerfile (line 23)
  2. Re-run build
  3. Once green, smoke test will run automatically
```

---

## The CLAUDE.md Workflow

`CLAUDE.md` is how your project remembers things between sessions. Claude Code reads it automatically -- think of it as onboarding docs that the AI actually uses.

**The cycle:**

```
/new-project  ──►  Work normally  ──►  /learn  ──►  /recall
     │                   │                │             │
     │         Claude reads CLAUDE.md     │    Search everything
     │          at session start          │    (docs + code + knowledge)
     │                                    │
     └──────── Creates initial file       └── Captures gotchas & patterns
```

**What goes in CLAUDE.md:**
- **Commands** (test, lint, build) -- so Claude never has to guess
- **Architecture** -- so Claude understands the system before changing it
- **Domain rules** -- conventions that aren't obvious from code alone
- **Gotchas** -- non-obvious things that waste time if you don't know them

**What stays out:**
- Sprint-specific work (use issues/tickets)
- Secrets (use .env)
- Verbose documentation (use docs/, keep CLAUDE.md concise)

A `CLAUDE.md.template` is included in this repo as a starting point for your global rules.

---

## How Self-Learning Works

The toolkit includes a self-learning system that captures knowledge automatically as you work -- not just when you explicitly call `/learn`.

### Three layers of learning

**Layer 1: Automatic tagging (during work)**

When Claude discovers something non-obvious -- a gotcha, a failed approach, a working pattern -- it tags it with `[LEARNING]` inline in its response. You'll see these appear naturally:

```
[LEARNING] pytest fixtures don't auto-discover from conftest in namespace packages
[LEARNING] The /api/users endpoint returns 500 if the rate limiter Redis is down -- needs fallback
```

These tags are saved immediately to your project's auto-memory directory so they persist across sessions. Claude creates topic files as needed (e.g., `debugging.md`, `patterns.md`).

**Layer 2: Explicit capture (`/learn`)**

Run `/learn` to capture a specific learning or scan the whole session:

```
/learn The migration system requires DB_URL even in test mode
/learn from session
```

This classifies the learning (project-specific, global, tool-usage, pattern), deduplicates against existing knowledge, and proposes additions as diffs to your CLAUDE.md files. If the memory MCP server is configured, it also persists to the searchable knowledge base.

**Layer 3: Searchable memory (memory MCP server)**

If you set up the memory system (see [SETUP-MEMORY.md](SETUP-MEMORY.md)), learnings get embedded as 768-dimensional vectors and stored in a local SQLite database. This powers `/recall` with semantic search -- you can find relevant context even when you don't remember the exact words.

### What triggers automatic learning

The `CLAUDE.md.template` instructs Claude to capture these automatically:

- **You correct Claude's approach** ("that's wrong", "don't do it that way", "use X instead")
- An approach was tried and found to be a bad fit
- A test failed for a non-obvious reason
- A dependency was missing that wasn't in requirements
- A command or path in CLAUDE.md was wrong or outdated
- A pattern worked well and should be reused

### Example: learning from a correction

```
You:    "Implement caching for the user profile endpoint"
Claude: [implements in-memory cache using a dict]

You:    "Wrong approach -- we run 4 replicas, in-memory won't share state. Use Redis."
Claude: "You're right. Updating to Redis."
        [LEARNING] In-memory caching doesn't work for user profiles -- service runs
        multiple replicas. Use Redis for shared state.
        [writes to project memory immediately]

        [implements Redis-based cache]

--- next session ---

You:    "Add caching to the orders endpoint"
Claude: [uses Redis from the start, because it remembers the previous correction]
```

This is the key behavior: **Claude doesn't just fix the immediate problem -- it remembers the lesson so it never makes the same mistake again.** The correction gets crystallized into project knowledge and influences all future sessions.

### The knowledge grows over time

```
Session 1:  /new-project → empty CLAUDE.md
Session 5:  CLAUDE.md has commands, architecture, 3 gotchas
Session 20: CLAUDE.md is a rich project guide, memory DB has 50+ learnings
            Claude starts each session already knowing the project deeply
```

The more you work with the toolkit, the less context you need to provide. Claude remembers what worked, what didn't, and why.

---

## Before & After: Why This Changes Everything

### 1. Onboarding to unfamiliar code

**Without toolkit:**
```
You:    "How does the payment system work?"
Claude: "Let me look at the codebase..."
        [reads 15 files, gives a wall of text]
        [misses the critical webhook retry logic]
        [you still don't know where to start]
You:    "No, I mean the actual flow when a user pays"
Claude: [reads 10 more files, still vague]
        ...20 minutes later you're still piecing it together
```

**With toolkit:**
```
/explain src/payments/

Claude:
## High Level
Payment service handles Stripe checkout → webhook confirmation → order fulfillment.

## Medium Level
[ASCII data flow diagram]
POST /checkout → create_session() → Stripe redirect
                                        ↓
webhook /stripe/events → verify_signature() → process_event()
    ├── payment_intent.succeeded → fulfill_order()
    └── payment_intent.failed → notify_user() + retry queue

Key files: checkout.py:45, webhooks.py:23, fulfillment.py:89

## Detail Level
- Webhook retries: 3 attempts, exponential backoff (webhooks.py:67)
- Idempotency key stored in Redis (checkout.py:52) -- prevents double charges
- Known quirk: Stripe sends duplicate events ~2% of the time (webhooks.py:31 handles dedup)

Want me to go deeper into any part?
```

**The difference:** 3 minutes vs 20 minutes. Structured levels mean you get exactly the depth you need.

---

### 2. "It works on my machine"

**Without toolkit:**
```
You:    "Ready to merge, all tests pass"
        [opens PR]
Reviewer: "This breaks the Docker build"
You:     "Works for me locally..."
Reviewer: "You have a stale .env.example, missing 2 env vars"
You:     "Oh..."
        [another round of review, half a day lost]
```

**With toolkit:**
```
/verify full project

Verification Report
===================
Dependency check:  PASS
Lint:              PASS -- 0 issues
Type check:        PASS
Tests:             PASS -- 47/47 passed, 89% coverage
Build:             FAIL -- Docker build fails at step 7
                   Missing env var REDIS_URL in .env.example
                   (used in src/cache.py:12 but not documented)
Git health:        PASS
Config consistency:FAIL -- .env.example missing REDIS_URL, WEBHOOK_SECRET

Overall: NEEDS ATTENTION

Remediation:
1. Add REDIS_URL and WEBHOOK_SECRET to .env.example
2. Rebuild Docker image to verify
```

**The difference:** You catch it in 30 seconds before the PR, not after a reviewer wastes time finding it.

---

### 3. Shipping with confidence vs. shipping with anxiety

**Without toolkit:**
```
You:    "Commit this"
Claude: [commits directly to main]
        [tests were actually failing]
        [CI breaks, team gets notified]
        [you spend an hour reverting and fixing]
```

**With toolkit:**
```
/commit-push-pr

Claude: Running tests first...
        BLOCKED: 2 tests failing in test_auth.py

        test_token_refresh: Expected 200, got 401
          → token_refresh() doesn't extend expiry (auth.py:89)
        test_expired_session: Assertion error on line 34
          → Session cleanup runs before the assertion

        Fix these before committing? I can help.
```

**The difference:** Broken code never leaves your machine. The command physically won't let you commit without green tests.

---

### 4. "We've solved this before... somewhere"

**Without toolkit:**
```
You:    "We need to add retry logic to the email service"
Claude: [implements from scratch]
        [misses the backoff strategy your team standardized on 3 months ago]
        [reviewer says "We have a retry utility, use that"]
        [you rewrite it]
```

**With toolkit:**
```
/recall retry logic

## From Project CLAUDE.md
- Retry pattern: use tenacity with exponential backoff, max 3 attempts (standardized Q3)

## From Code
- src/utils/retry.py -- team retry decorator with circuit breaker
- src/notifications/sms.py:45 -- example usage with Twilio
- tests/test_retry.py -- 12 tests covering backoff behavior

## Related Files
- src/utils/retry.py -- the reusable decorator (use this, don't roll your own)
```

```
/tdd Add retry logic to email service using our standard retry decorator
```

**The difference:** Claude already knows your team's patterns. No reinventing, no review ping-pong.

---

### 5. The audit that humbles you

**Without toolkit:**
```
You:    [confident the codebase is solid]
        [ships to production]
        [security scan in CI finds 3 critical vulns]
        [scramble to fix in prod]
```

**With toolkit:**
```
/audit

Codebase Audit -- Scorecard
============================
| Dimension   | Score | Top Issue |
|-------------|-------|-----------|
| Security    | 4/10  | SQL injection in search_users() -- f-string in query |
| Tests       | 6/10  | Payment webhook handler has 0 test coverage |
| Quality     | 7/10  | 3 functions over 200 lines, should be split |
| Docs        | 5/10  | README install steps are outdated (still references pip) |
| Performance | 8/10  | N+1 query in /api/users/list (loads profiles individually) |

Top 3 Critical Findings:

[CRITICAL] SQL Injection -- src/users/search.py:34
  query = f"SELECT * FROM users WHERE name LIKE '%{term}%'"
  Fix: Use parameterized query with ? placeholder

[CRITICAL] No tests for payment webhook -- src/payments/webhooks.py
  This handles money. 0 tests = 0 confidence.
  Fix: /tdd Add webhook handler tests for success, failure, duplicate events

[HIGH] Outdated README -- README.md:15-22
  Says "pip install -r requirements.txt" but project uses poetry
  Fix: /document README
```

**The difference:** You find the problems on your terms, not during an incident at 2 AM.

---

### 6. Learning from mistakes (and never repeating them)

**Without toolkit:**
```
Session 1:  Claude uses in-memory cache → you correct it → uses Redis
Session 2:  Claude uses in-memory cache again → you correct it again
Session 3:  Claude uses in-memory cache AGAIN → you lose patience
            (Claude has no memory between sessions)
```

**With toolkit:**
```
Session 1:
You:    "Wrong approach -- we run 4 replicas, use Redis"
Claude: [LEARNING] In-memory caching doesn't work -- service runs multiple
        replicas with no shared state. Always use Redis for caching.
        [saved to project memory]

Session 2:
You:    "Add caching to the orders endpoint"
Claude: [reads project memory, sees the Redis rule]
        "Using Redis for caching (consistent with our multi-replica setup)."
        [gets it right the first time]

Session 47:
        Claude has accumulated 80+ learnings about your project.
        It knows your patterns, your gotchas, your preferences.
        It feels like working with a teammate who's been on the project for months.
```

**The difference:** Claude gets smarter about YOUR codebase over time. Every correction makes every future session better.

---

### 7. Complex features without the chaos

**Without toolkit:**
```
You:    "Add Stripe subscription billing"
Claude: [writes 800 lines in one go]
        [no tests]
        [hardcoded API keys in the code]
        [doesn't match your existing payment patterns]
        [you spend 2 days cleaning it up]
```

**With toolkit:**
```
/orchestrate Add Stripe subscription billing with webhooks,
             usage metering, and upgrade/downgrade flows

Claude: Breaking this into 5 workstreams:

1. [architect] Design billing module structure (depends on: nothing)
2. [tdd-agent] Implement subscription CRUD (depends on: 1)
3. [tdd-agent] Implement webhook handlers (depends on: 1)
4. [security-auditor] Review for PCI compliance (depends on: 2, 3)
5. [documentation-agent] Update API docs (depends on: 2, 3)

Agents 2+3 run in parallel after architect completes.
Security review runs after implementation.
Docs generated last.

Approve this plan? [yes]

[5 agents work in parallel where possible]
[each agent follows TDD -- tests first]
[security auditor catches the webhook signature verification gap]
[documentation agent generates accurate API docs from the actual code]

Results:
- 12 files created/modified
- 34 tests written (all passing)
- 1 security finding fixed (webhook signature wasn't verified)
- API docs generated
- Total time: ~15 minutes of your attention
```

**The difference:** You describe what you want. The system decomposes, implements, tests, secures, and documents it -- all coordinated.

---

### 8. Basic prompts vs. engineered prompts

**Without toolkit:**
```
You:    "Refactor the user service to be more maintainable"
Claude: [starts editing files immediately]
        [no analysis of what's actually wrong]
        [renames a few things, splits one file]
        [breaks 3 tests it didn't know about]
        [you spend an hour fixing the fallout]

You:    "Review this PR for security issues"
Claude: "Looks good overall. I don't see any major issues."
        [misses the SQL injection on line 47]
        [misses the hardcoded secret on line 112]
        [you merge it. Vulnerability ships to production.]
```

**With toolkit:**
```
/metaprompt Refactor the user service to be more maintainable

Claude: [transforms your casual prompt into an advanced execution plan]

        Generated prompt:
        Phase 1: READ-ONLY -- map all files, dependencies, test coverage
        Phase 2: PLAN -- identify specific maintainability issues, propose fixes
        Phase 3: TEST FIRST -- write tests for any untested code before touching it
        Phase 4: REFACTOR -- one change at a time, run tests after each
        Phase 5: VERIFY -- full suite, no regressions, output before/after metrics

        Use immediately? [yes]

Claude: [follows the engineered prompt]
        [reads everything first, understands the dependency graph]
        [identifies 4 specific issues: god function, circular import,
         duplicated validation, missing error handling]
        [writes tests for untested paths BEFORE refactoring]
        [refactors methodically, tests green after every change]
        [final report: 4 issues fixed, 0 regressions, +8 tests]
```

**The difference:** The basic prompt produces basic work. `/metaprompt` transforms it into a structured execution plan with phases, tool assignments, safety constraints, and verification -- the kind of prompt a senior engineer would write. You get expert-level prompt engineering without being a prompt engineer.

---

## Tips for Getting the Most Out of It

1. **Start every session with `/status`** -- it takes seconds and prevents working on stale state.
2. **Use `/explain` before modifying unfamiliar code** -- understanding first, changes second.
3. **Let `/tdd` enforce discipline** -- it's easy to skip tests "just this once." The command won't let you.
4. **Run `/verify` before every PR** -- catch issues before reviewers do.
5. **Feed `/learn` regularly** -- the more your CLAUDE.md knows, the less context you need to provide.
6. **Use `/metaprompt` when you repeat yourself** -- if you've done the same workflow 3 times, turn it into a command.
7. **Try `/audit` on a project you think is solid** -- you might be surprised.

---

## Coming Next

These features are in active development. They represent where the toolkit is headed.

---

### Skills Crystallization: From Repetition to Reusable Commands

**The problem:** You find yourself doing the same multi-step workflow over and over. Maybe every time you add an API endpoint, you do the same 5 things. Or every time you onboard to a new service, you run the same sequence. These workflows live in your head -- invisible, undocumented, and lost when you switch teams.

**The vision:** Claude detects repeated patterns and suggests turning them into slash commands.

```
Session 12:
You:    "Add a GET /api/orders endpoint"
Claude: [writes route, handler, schema, test, docs -- same pattern as last 3 endpoints]

        I've noticed you follow the same workflow every time you add an endpoint:
        1. Create route in routes/
        2. Add Pydantic schema in schemas/
        3. Write handler with DB query
        4. Add tests (happy path + 404 + validation)
        5. Update API docs

        Want me to crystallize this into a /new-endpoint command?
        It would take the resource name and method as arguments.

You:    "Yes"
Claude: /metaprompt Create a slash command called /new-endpoint that...

        Generated: commands/new-endpoint.md
        [shows the command for review]

You:    "Save it"
        [command saved to .claude/commands/new-endpoint.md]

Session 13:
You:    /new-endpoint products GET,POST,DELETE
Claude: [follows the crystallized workflow perfectly, in seconds]
```

**How it works:**
1. **Detection** — The self-learning system tracks workflow patterns across sessions via memory
2. **Suggestion** — After 3+ repetitions, Claude proposes crystallization
3. **Generation** — `/metaprompt` creates an optimized slash command with phases, constraints, and output format
4. **Review** — You refine it before saving (human in the loop)
5. **Propagation** — PR the new command to the team toolkit repo so everyone benefits

**Why it matters:** Every team has 10-20 invisible workflows that take 15 minutes each. Crystallizing them into commands means 15 minutes becomes 15 seconds. Multiply by the team size and frequency -- that's weeks of productivity per year.

---

### Conversation Compacting Recovery: Never Lose Context

**The problem:** Long Claude Code sessions hit the context window limit. When this happens, Claude compresses earlier messages to make room. Suddenly, Claude forgets what you were working on, what you tried, and what you decided. You waste time re-explaining.

**How the toolkit solves it:**

```
Long session, 2 hours in:
[context compaction happens -- earlier messages compressed]

Without toolkit:
Claude: "I seem to have lost context. What were we working on?"
You:    [spends 10 minutes re-explaining everything]

With toolkit:
Claude: [detects context loss]
        [calls memory_context("current task context")]
        [reloads: task description, decisions made, approaches tried, learnings]

        "Context recovered from memory. We were implementing the rate limiter.
         We decided on Redis (not in-memory) because of multi-replica setup.
         Last completed: the middleware. Next: webhook integration.
         Continuing from where we left off."
```

**Three recovery layers:**

1. **Proactive saving** — Before long operations, Claude saves task context to memory (category="context", importance=8). This happens automatically per the `CLAUDE.md` instructions.

2. **Automatic recovery** — When Claude detects context loss, it calls `memory_context` to reload relevant knowledge: rules, recent decisions, project patterns, and current task state.

3. **Manual fallback** — If auto-recovery misses something, use `/recall` to search for specific context, or check the project's auto-memory directory for topic files.

**Why it matters:** The average complex development session is 2-4 hours. Without recovery, you hit a wall at ~90 minutes and waste time re-contextualizing. With memory, sessions can run indefinitely with no context degradation.

---

### Post-Audit Remediation: `/audit --fix`

**The problem:** `/audit` tells you what's wrong. But knowing isn't fixing. The scorecard sits there, findings accumulate, and the team either ignores them (too many to tackle) or fixes them one by one over weeks.

**The vision:** After the audit scorecard, `--fix` spawns a coordinated team of dev agents that actually address the findings -- safely, with tests, and without breaking anything.

```
/audit --fix

Phase 1: AUDIT
══════════════
| Dimension   | Score | Top Issue |
|-------------|-------|-----------|
| Security    | 4/10  | SQL injection in search_users() |
| Tests       | 6/10  | Payment webhook: 0 test coverage |
| Quality     | 7/10  | 3 functions over 200 lines |
| Docs        | 5/10  | README install steps outdated |
| Performance | 8/10  | N+1 query in /api/users/list |

14 findings total. 3 critical, 4 high, 5 medium, 2 low.

Phase 2: TRIAGE
═══════════════
Before fixing, I need to understand your codebase constraints.

Questions:
1. search_users() uses f-strings for the query. Is this intentional
   (e.g., dynamic table names) or a bug?                        → Bug
2. The bare `except:` in payment_handler.py:89 -- is this a
   deliberate catch-all for resilience?                          → Intentional, but should log
3. The 250-line process_order() function -- is there a reason
   it's monolithic? (transaction boundary? atomicity?)           → No, just grew over time
4. Any areas of the codebase I should NOT touch?                 → Don't modify the ETL pipeline

Claude: Got it. Planning fixes for 12 findings (excluding ETL pipeline).
        The bare except stays but gets logging added.

Phase 3: PLAN & EXECUTE
════════════════════════
Dispatching 4 agent teams in parallel:

[security-auditor + tdd-agent] → Fix SQL injection (3 locations)
  - Replace f-strings with parameterized queries
  - Add SQL injection test cases
  - Verify existing queries still return correct results

[tdd-agent] → Add payment webhook tests
  - Test: successful payment → order fulfilled
  - Test: failed payment → user notified
  - Test: duplicate event → idempotent handling
  - Test: invalid signature → rejected

[tdd-agent] → Refactor oversized functions
  - Split process_order() into 4 focused functions
  - Maintain same external behavior (test first!)
  - Add logging to bare except in payment_handler

[documentation-agent] → Fix README + update CLAUDE.md
  - Update install steps (pip → poetry)
  - Add rate limiter docs
  - Update CLAUDE.md architecture section

Phase 4: VERIFY
═══════════════
[verification-agent] → Full test suite + re-audit

Before: 47 tests, 3 critical findings, overall 6/10
After:  68 tests (+21), 0 critical findings, overall 8.2/10

| Dimension   | Before | After | Delta |
|-------------|--------|-------|-------|
| Security    | 4/10   | 9/10  | +5    |
| Tests       | 6/10   | 8/10  | +2    |
| Quality     | 7/10   | 8/10  | +1    |
| Docs        | 5/10   | 8/10  | +3    |
| Performance | 8/10   | 8/10  |  0    |

All tests passing. No regressions in core functionality.

Phase 5: LEARN
══════════════
Crystallized 4 learnings:

[LEARNING] search_users had SQL injection via f-string -- always use parameterized queries
[LEARNING] Payment webhooks were untested -- always add tests when handling money
[LEARNING] process_order() grew to 250 lines -- set a 50-line soft limit, refactor proactively
[LEARNING] README referenced pip but project uses poetry -- verify README on every tooling change

These are now in project memory. Future sessions will flag
these patterns before they become audit findings.
```

**The five phases:**

| Phase | What happens | Who's involved |
|-------|-------------|---------------|
| **Audit** | Full 5-dimension scan | security, code-reviewer, verification agents |
| **Triage** | Ask about intentional patterns, identify no-touch zones | Human (you) |
| **Plan & Execute** | TDD-first fixes, parallel where possible | tdd-agent, security-auditor, documentation-agent |
| **Verify** | Re-run full suite + re-audit, show before/after | verification-agent |
| **Learn** | Save findings to memory, update CLAUDE.md | self-learning protocol |

**Safety rails:**
- **Always asks first** — Patterns that look wrong might be intentional. The triage phase catches these before any code changes.
- **Never touches what you protect** — You declare off-limits areas. Agents respect the boundary.
- **TDD for every fix** — No fix goes in without a failing test first. This proves the fix works AND prevents regressions.
- **Before/after scorecard** — Quantified improvement. You see exactly what changed and by how much.
- **Human approval at every phase** — Not a black box. You see the plan, approve it, review the results.

**The three goals:**

1. **Help developers learn from mistakes.** Each finding comes with an explanation of WHY it matters -- not just "fix this" but "here's what could go wrong in production." The team learns secure coding patterns, testing discipline, and architecture principles through real examples from their own code.

2. **Make them understand the rationale.** The before/after scorecard makes improvement tangible. When a developer sees "Security: 4/10 → 9/10" with specific fixes they can read, they internalize the lessons. It's not abstract best practices -- it's their code, made better, with explanations.

3. **Make the Second Brain smarter.** Every fix becomes a learning. Every learning prevents the same mistake in future code. The system gets better at catching issues earlier -- eventually, it flags problematic patterns while you're writing them, not after an audit. The goal is a codebase that improves itself.
