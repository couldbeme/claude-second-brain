# First 10 Minutes

You've installed the toolkit. Now use it.

This picks up where [QUICK-START.md](../QUICK-START.md) leaves off — you have
`install.sh` done, commands symlinked, and Claude Code open in a project.

---

## Minute 0–2: Install check

If you haven't installed yet, do that first: [QUICK-START.md](../QUICK-START.md).

Verify the install took:

```bash
ls ~/.claude/commands/ | head -5
# expect: audit.md  commit-push-pr.md  context-save.md  diagnose.md  document.md
```

```bash
ls ~/.claude/agents/ | head -5
# expect: architect.md  code-reviewer.md  database-engineer.md  ...
```

Both lists populated? You're good. Open Claude Code in any project you have
locally — real code, not a toy — and continue.

---

## Minute 2–5: Command tour

Three commands, three minutes, zero configuration required.

### `/guide tour`

```
/guide tour
```

Expected output (condensed):

```
Welcome to the Claude Second Brain! Here's what you have:

ORIENT — understand before you build
  /status          Where am I? What's in flight?
  /explain         How does this code work? (3-level breakdown)
  /recall          What do we already know about this?

BUILD — write code the right way
  /tdd             Test-first development (red → green → refactor)
  /diagnose        Got an error screenshot? Paste it, get a fix
  /verify          Full health check (tests, lint, build)
  /commit-push-pr  Quality-gated shipping

ANALYZE — find problems before they find you
  /scan            Full repo health scan -- one report, all dimensions
  /audit           6-dimension codebase audit with scorecard
  /gap-analysis    Find missing tests, docs, error handling

RESEARCH & LEARN
  /research        Deep 3-track investigation with sources
  /learn           Save discoveries for the team
  /sync-memories   Export/import knowledge between machines

POWER TOOLS
  /orchestrate     Multi-agent team for complex tasks
  /metaprompt      Generate agent-optimized prompts
  /document        Generate or update documentation
  /new-project     Scaffold a new project with standards

/guide [what you want to do]  — run this anytime for workflow advice
```

You now know what exists. `/guide [what you want to do]` works any time —
not just as a tour. Try `/guide I want to refactor something safely` after this.

### `/status`

```
/status
```

Expected output (in a real project):

```
Project Status
==============
Branch: main (2 commits ahead of origin)
Tests:  34 passed, 1 failed — test_user_serializer (users/tests.py:88)
Lint:   2 warnings (unused import, line too long)
Next:   Fix failing test, then push — origin is 2 commits behind
```

This is the orientation command. Run it at session start, before standups,
before touching unfamiliar code. It reads git state, runs tests and linter,
and synthesizes a "next step" recommendation in one screen.

### `/explain <file>`

```
/explain src/auth/middleware.py
```

Expected output structure:

```
## High Level
JWT middleware validates tokens on every protected route. Sits between
the router and controllers. Failures return 401 with error code.

## Medium Level
Request → extract_token() → verify_jwt() → attach_user_to_request()
                                 ↓ invalid
                            log_failure() → 401 {"error": "invalid_token"}

Key files: middleware.py:12, tokens.py:34, auth_errors.py:8

## Detail Level
- Token expiry check uses server time, not client time (middleware.py:45)
- Known quirk: refresh tokens bypass this middleware (handled in auth_router.py:89)
- The `attach_user_to_request` call modifies g.user — FastAPI uses request.state instead
  if you're porting this
```

Three levels. You pick the depth you need. The detail level surfaces gotchas
that aren't in the docstrings — edge cases the previous developer knew and
never wrote down.

---

## Minute 5–8: Metaprompt demo

This is where the toolkit compounds. Fuzzy ask in, structured execution plan out.

**The fuzzy ask:**

```
/metaprompt make sure the login endpoint is solid before we ship
```

Without `/metaprompt`, Claude starts editing code immediately. With it:

**The upskilled prompt (what `/metaprompt` generates):**

```markdown
# Mission

Security + quality review of the login endpoint. Output: ranked findings
with severity, file:line, and a concrete fix for each. Reader can act
without follow-up questions.

# Phases

## Phase 1 — Threat model (architect)
Map: who calls the endpoint, what it grants, what tokens it issues, what
happens on expiry, what happens on failed attempts. Output: threat-model.md.

## Phase 2 — SAST sweep (security-auditor)
Static paths: SQL injection in user lookup, weak password hashing,
plaintext secrets in env handling, missing rate limits, brute-force
surface, session fixation.

## Phase 3 — Token lifecycle (security-auditor)
TTL bounded? Refresh rotation on use? Revocation propagates? No token
in logs/URLs/error bodies?

## Phase 4 — Test coverage gap (tdd-agent)
What paths have zero test coverage? Every CRITICAL finding gets a failing
test before any fix lands.

## Phase 5 — Verification (verification-agent)
Run the full suite. Every finding has: severity (CRITICAL/HIGH/MEDIUM/LOW),
file:line, exploit-shape, fix-shape. No claim without evidence.

# Hard constraints
- No fix without measurement. Every "X is vulnerable" cites a reachable path.
- CRITICAL and HIGH findings must have a fix-PR or an explicit accept-risk decision.
- Done when: findings list exists + severity-sorted + full suite green.
```

**Why this matters:** the BEFORE ("make sure it's solid") produces a bulleted
list of concerns. The AFTER produces a phased security review with agent
assignments, severity definitions, evidence requirements, and a "done when"
gate. The fuzzy ask relied on Claude inferring all of that — and it usually
doesn't.

Run the upskilled prompt:

```
Use immediately? [yes]
```

You now have a structured, multi-agent security review of your login endpoint.
That's the `/metaprompt` loop: fuzzy → structured → reusable (save it as
`/login-review` if you'll run this again).

---

## Minute 8–10: Memory — the cross-session callback

The toolkit's memory system turns corrections and learnings into durable,
searchable knowledge that survives session boundaries.

**Session 1 — teaching Claude something:**

```
/learn The rate-limiter only applies to unauthenticated routes — authenticated
       users bypass it. This is intentional and documented in infra/rate-limit.md.
```

Claude tags it `[LEARNING]`, writes it to the memory database with a hybrid
embedding (vector + keyword), and indexes it.

**Same session or later — verifying it saved:**

Two retrieval paths, depending on what you need:

- **`/recall rate-limiter`** — quick file-grep synthesizer over CLAUDE.md, README, docs/, and code. Surfaces *project-knowledge* mentions of the topic. Doesn't query the memory MCP.
- **Ask Claude to "search memories for rate-limiter"** — calls the `memory_search` MCP tool against `memory.db`. Returns vector + BM25 ranked hits with importance + confidence:

```
Memory Search: "rate-limiter"
==============================
[importance: 8] Rate-limiter applies to unauthenticated routes only.
Authenticated users bypass it. Intentional — see infra/rate-limit.md.
Source: session learning  Tags: rate-limiter, auth, infra

[importance: 6] Redis used for distributed rate-limit counters (not in-memory).
Reason: service runs 4 replicas. In-memory counters would be per-replica.
Source: session learning  Tags: rate-limiter, redis, infra
```

**Session 2 — the callback fires:**

Fresh session. New context window. You ask Claude to add rate-limiting to a
new endpoint.

```
/tdd Add rate limiting to /api/payments
```

Claude reads project memory before acting. Without `/recall` from you, it
surfaces:

```
[Reading project context...]
Found: rate-limiter applies to unauthenticated routes only — authenticated
users bypass it by design (infra/rate-limit.md). Payments endpoint serves
authenticated users. Adding rate-limit would contradict this pattern.

Recommend: confirm whether /api/payments should be an exception before
proceeding.
```

That question — the one that would have cost you a code review cycle if
missed — came from a learning you made two sessions ago. The memory system
made Claude smarter about your codebase without you re-explaining it.

**The cycle:**

```
/learn → memory database → /recall at session start → Claude knows your patterns
```

The more sessions you feed it, the less context you have to re-provide.

---

## Now what — 3 things to try next

**1. Run `/audit` on something you think is solid.**

```
/audit
```

Security, test coverage, quality, docs, performance — all six dimensions,
scored, with the top 10 prioritized findings. Most projects have at least one
surprise. Find yours before a reviewer does.

**2. Turn a repeated workflow into a command with `/metaprompt`.**

If you've done the same multi-step task more than twice, it belongs in a
command. Give `/metaprompt` the fuzzy version and save the output. Next
time it's one line, not ten minutes.

**3. Open the sandbox.**

```bash
cd <your-toolkit-path>/examples/sandbox/
```

Then:

```
/scan
/tdd Fix the null return bug
/audit security
```

The sandbox has 5 intentional issues. Finding all of them — and watching
TDD enforce discipline on the fix — shows you how `/scan`, `/tdd`, and
`/audit` interact under real conditions.

---

By now you've hit three "this is real" moments: `/status` gave you
actual project state, `/metaprompt` turned a fuzzy ask into an execution
plan, and `/recall` brought back something you taught Claude last session.
That's the loop. The rest of the commands extend it.

See [TOOLKIT.md](../TOOLKIT.md) for 9 full Before/After scenarios.
See [docs/COMMANDS.md](COMMANDS.md) for the complete command reference.
