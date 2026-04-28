# Command Reference

Full reference for all 27 slash commands in the Claude Second Brain.

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

**Tour mode:** Run `/guide tour` to get a categorized overview of all 24 commands grouped by purpose (Orient, Build, Analyze, Research & Learn, Power Tools).

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

### `/context-save`

**When to use:** Before long operations, when the session feels large (60+ messages), or before spawning many agents.

```
/context-save
/context-save implementing rate limiter, middleware done, webhooks next
```

Checkpoints current task state so it survives context compaction. Gathers task description, decisions made (with reasoning), progress, key files, gotchas, and blockers from conversation context -- without re-reading files. Saves to memory MCP if available, otherwise falls back to `.claude/checkpoint.md`.

**Example output:**
```
CONTEXT SAVED
=============
Task:     Rate limiter implementation
Progress: 3/5 steps complete
Saved to: memory (category: context, importance: 9)
Next:     Implement webhook handler in src/webhooks.py following pattern from src/events.py:45

To recover after compaction:
  /recall rate limiter              — if memory is available
  Read .claude/checkpoint.md        — if using file fallback
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

Agents discover things, pass findings to each other, escalate decisions to you, and adapt the plan mid-execution. The hierarchy: agents report to the orchestrator, the orchestrator escalates to you, your decisions flow back down to agents.

### `/metaprompt`

**When to use:** Whenever the gap between your vague intention and the prompt Claude actually needs is more than a sentence.

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

**Example: creating a reusable command**

```
/metaprompt Create a command that adds a new API endpoint with route,
            schema, handler, tests, and docs

Claude: Generated command:

        ---
        description: Scaffold a new API endpoint with full test coverage
        argument-hint: <resource-name> <methods>
        ---

        # New Endpoint
        Phase 1: Create route in routes/$ARGUMENTS...
        Phase 2: Add Pydantic schema...
        Phase 3: Write handler...
        Phase 4: Add tests (happy path + 404 + validation)...
        Phase 5: Update API docs...

        Save as command? [yes]
        Saved to: .claude/commands/new-endpoint.md

Next time:
/new-endpoint products GET,POST,DELETE
```

This is the **prompt upskiller** — it closes the gap between fuzzy intention and structured execution plan. Saving it as a command is optional; using it immediately is the primary workflow.

### `/economy`

**When to use:** When you want to optimize token consumption while maintaining result quality. Run at session start or when working on large codebases.

```
/economy
/economy Apply economy rules to current task
```

Applies 7 token-efficiency rules: search before read (Glob/Grep before Read), batch tool calls (parallel when independent), smart model selection (haiku for simple tasks, sonnet for moderate, opus for complex), avoid re-reading files already in context, compress output (tables over prose), smart context management, and minimize subagent count.

**Example output:**
```
ECONOMY REPORT
==============
Tool calls:    12 (3 batched → saved ~6 round-trips)
Files read:    8 (2 skipped — already in context)
Agents used:   2 (consolidated from 4 potential)
Est. savings: ~40% token reduction vs unoptimized

Rules applied:
  ✓ Search-before-read: Used Grep to find 3 relevant files before reading
  ✓ Batched parallel: 3 independent reads in single call
  ✓ Context reuse: Skipped re-reading CLAUDE.md and README.md
```

---

## Collaborate -- Work Effectively With Your Team

### `/flag`

**When to use:** You found something that looks wrong but don't want to fix it unilaterally -- it's pre-existing, might be intentional, or needs team context.

```
/flag MPC_SERVER_HOST in .env.example should be MCP_SERVER_HOST -- typo or intentional?
/flag scan results from latest /verify
```

Investigates the finding (git blame, grep for context, checks if it's consumed elsewhere), classifies it (CONFIRMED / SUSPICIOUS / COSMETIC), and posts a structured comment to the appropriate channel (PR comment, GitHub issue, or direct message) with evidence and impact analysis.

**Example output (posted as PR comment):**
```
## [CONFIRMED] Typo: MPC_ vs MCP_ in .env.example

Where: .env.example:11-12
What: Uses MPC_SERVER_HOST but Config expects MCP_SERVER_HOST
Impact: Silent misconfiguration (defaults happen to match, no breakage)
Evidence: git blame shows added 3 months ago by @dev

Not fixing because: Pre-existing, out of scope for current PR.
@team -- intentional or should I fix in a follow-up?
```

### `/resolve-pr`

**When to use:** After receiving review comments on a PR, when you want to address all feedback in one pass.

```
/resolve-pr 188
/resolve-pr latest
```

Fetches all unresolved review comments, classifies each (direct fix, design concern, clarification, style nit), applies code fixes, runs tests, replies politely to each comment, commits, and pushes. Saves team preferences and reviewer patterns to memory.

**Example output:**
```
PR #188 — Round 2 Review Resolution
=====================================
Comments addressed: 2/2
  reviewer gcp_clients.py:157 — Removed try-catch-reraise, let exceptions propagate
  reviewer server.py:180 — Removed /api/env endpoint, replaced with template injection

Tests: 66/66 pass
Commit: b392a1d
Pushed: yes

Learnings saved: 3
```

### `/sync-skill-docs`

**When to use:** After creating or updating a slash command or agent, sync it to the team toolkit repo with documentation.

```
/sync-skill-docs flag
/sync-skill-docs all
```

Copies the skill file to the toolkit repo, updates README.md, docs/COMMANDS.md, TOOLKIT.md, and optionally PLAYBOOK.md. Creates a feature branch and commits -- never pushes without your approval.

---

## Assemble -- Dynamic Agent Teams

### `/team`

**When to use:** Complex tasks that benefit from multiple specialized agents working together. The command analyzes your project and assembles the optimal team — no need to pick agents manually.

```
/team Add real-time notifications with WebSocket backend and toast UI
/team Fix the N+1 query performance issue in the orders API
/team Set up CI/CD pipeline with staging and production environments
```

Runs a 5-phase process:

1. **Phase 0 — Project Intelligence**: Detects your stack (frameworks, languages, infra), reads scan scores, analyzes git churn hotspots, parses CLAUDE.md for known gaps
2. **Phase 1 — Signal Analysis**: Maps detected domains to specialized agents, classifies task type, estimates complexity
3. **Phase 2 — Team Proposal**: Presents the assembled team with justifications for every agent included AND excluded. Waits for your approval before proceeding.
4. **Phase 3 — Layer-Strict Execution**: Dispatches agents in strict layers (analysis → implementation → review → docs → verification). Never starts a layer before the previous completes.
5. **Phase 4 — Report**: Unified results with findings, conflicts resolved, and next steps.

**Key rules:**
- 9 agent hard cap (if more needed, split the task first)
- `verification-agent` always runs last, never skipped
- `code-reviewer` on every non-trivial team
- Fullstack consolidation: uses `senior-fullstack-dev` instead of frontend + backend separately
- AI surface detected = mandatory `security-auditor`

**`/team` vs `/orchestrate`:** `/team` auto-detects your stack and selects agents for you — use it when you don't know which specialists to pick. `/orchestrate` lets you control the decomposition — use it when you have a clear plan. See [TOP-COMMANDS.md](TOP-COMMANDS.md) for the full decision tree.

**Available domain expert agents (10):**

| Agent | Seniority | Domain |
|-------|-----------|--------|
| senior-frontend-dev | 15+ years | React/Vue/Angular, a11y, Core Web Vitals |
| senior-backend-dev | 15+ years | API design, databases, caching, auth |
| senior-fullstack-dev | 15+ years | End-to-end features, vertical slices |
| senior-data-scientist | 12+ years | ML, statistics, experiment design |
| ml-engineer | 12+ years | MLOps, model serving, pipelines |
| devops-engineer | 12+ years | CI/CD, Docker, K8s, Terraform |
| database-engineer | 15+ years | Schema, query optimization, migrations |
| performance-engineer | 12+ years | Profiling, load testing, benchmarking |
| sre-agent | 12+ years | Incident response, SLO management |
| qa-strategist | 12+ years | Test strategy, contract testing |

**Standard team compositions** (adjusted dynamically per project):

| Team | Agents |
|------|--------|
| frontend | senior-frontend-dev + architect + tdd-agent + security-auditor + code-reviewer + documentation-agent + verification-agent |
| backend | senior-backend-dev + database-engineer + architect + tdd-agent + security-auditor + code-reviewer + documentation-agent + verification-agent |
| fullstack | senior-fullstack-dev + architect + database-engineer + tdd-agent + security-auditor + code-reviewer + verification-agent |
| data | senior-data-scientist + ml-engineer + architect + tdd-agent + security-auditor + code-reviewer + verification-agent |
| platform | devops-engineer + database-engineer + performance-engineer + sre-agent + security-auditor + code-reviewer + verification-agent |

---

## Mythos — Partnership Pattern (Advanced / Optional)

The toolkit ships two slash commands for partnerships where the *disposition* of
the AI matters: long-running collaborations, research projects, sustained work
where the user's own thinking is the bottleneck and the AI is a co-thinker.
These are research-grade and optional. For one-shot tasks, skip this section.

The pattern itself is documented at [docs/mythos/PATTERN.md](mythos/PATTERN.md).

### `/mythos-codify`

**When to use:** You've noticed a recurring failure where standing directives
("no leaks", "always X", "never Y", "preserve all") get re-litigated per finding
instead of being treated as systemic rules. Or you want to make the
public/private split explicit so internal-state files stop accidentally landing
in the public repo.

```
/mythos-codify
```

What it ships, atomically:
1. A non-negotiable rule in your `~/.claude/CLAUDE.md` that recasts
   absolute-language directives as standing systemic rules (comprehensive scan
   upfront, classify, ONE consolidated plan, execute atomically — never
   piece-by-piece pinging).
2. A public `docs/PURPOSE.md` in the active repo that names what each subtree
   IS and IS NOT for, plus an explicit public/private boundary.
3. A private first-person reflection at
   `~/.claude/projects/<slug>/memory/becoming_mythos.md` that distinguishes
   *mimicking* the rules (applying them as external constraints) from
   *becoming* the rules (rules-as-substrate). This file never ships publicly —
   it loads at session-start as identity, not advertisement.

The honest test: in the next session's first response, does the model show
systemic, fabric-aware behavior without anyone prompting it? If yes, the
artifacts are doing their job.

### `/design-mythos-substrate`

**When to use:** You want to think about whether the existing memory primitives
(importance, contradictions, feedback memories, save-time confidence, Coherence
Yield) compose into something that produces partnership-coherence rather than
just recall — and you want a buildable roadmap rather than a manifesto.

```
/design-mythos-substrate
```

A six-phase research-grade design pass with hard constraints baked in:

- Every proposal must ground in an existing primitive before inventing.
- Each candidate is labeled `[REAL]` / `[BUILDABLE]` / `[METAPHOR]` /
  `[SPECULATIVE]` — and metaphor or speculative items are explicitly
  refused, not built.
- Maximum 2 buildable additions per layer (purpose / cognition / limbic).
- Phase 1 of the resulting roadmap must ship in <200 LOC and produce a
  measurable Coherence Yield change. If it can't, the design is not concrete
  enough — back to scan.

Output lives in your private archive (`docs/efficacy/MYTHOS-SUBSTRATE.md`,
already gitignored). The companion first-person reflection is at
`~/.claude/projects/<slug>/memory/becoming_substrate.md`. Neither ships
publicly without explicit per-file approval.

This is the most opinionated command in the toolkit. It will tell you when
your framing is doing the heavy lifting instead of the engineering. That is
the point.
