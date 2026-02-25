# Claude Code Team Toolkit

### 18 Slash Commands + 7 Agents for High-Quality Development

Slash commands are reusable workflow prompts for Claude Code. Type `/command-name` and Claude follows a structured process instead of ad-hoc prompting. Agents are specialized subprocesses that handle focused tasks autonomously.

This toolkit codifies engineering best practices into repeatable, quality-enforced workflows.

---

## Documentation Map

| Doc | What it covers |
|-----|----------------|
| **[QUICK-START.md](QUICK-START.md)** | Install guide + "Your First 5 Minutes" walkthrough + hands-on sandbox |
| **This file** | Why the toolkit matters -- 9 Before & After scenarios |
| **[PLAYBOOK.md](PLAYBOOK.md)** | Daily workflow recipes, prompt patterns, agent composition, AI/LLM security |
| **[docs/COMMANDS.md](docs/COMMANDS.md)** | Full reference for all 18 commands |
| **[docs/AGENTS.md](docs/AGENTS.md)** | Full reference for all 7 agents |
| **[docs/SELF-LEARNING.md](docs/SELF-LEARNING.md)** | CLAUDE.md workflow + 5-layer learning system |
| **[docs/ADVANCED-PATTERNS.md](docs/ADVANCED-PATTERNS.md)** | Skills crystallization, context recovery, post-audit remediation |
| **[SETUP-MEMORY.md](SETUP-MEMORY.md)** | Memory system installation -- LM Studio, MCP server, hybrid search |
| **[CLAUDE.md.template](CLAUDE.md.template)** | Global rules template -- TDD, security, self-learning protocol |
| **[docs/ROLLOUT-GUIDE.md](docs/ROLLOUT-GUIDE.md)** | Operational guide -- when to scan, how to interpret, team cadence |
| **[docs/ANNOUNCEMENT.md](docs/ANNOUNCEMENT.md)** | Internal rollout announcement template |

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
| `/audit` | Full 6-dimension codebase audit with scorecard |
| `/gap-analysis` | Find missing tests, docs, error handling, types |
| `/research` | Deep 3-track technical research with sources |
| `/orchestrate` | Decompose complex tasks into multi-agent workflows |
| `/metaprompt` | Generate optimized prompts from a task description |
| `/sync-memories` | Export/import knowledge between machines |
| `/guide` | Interactive toolkit assistant -- suggests commands and workflows |
| `/diagnose` | Interpret error screenshots, logs, or stack traces and fix |
| `/scan` | Full repository health scan -- security, quality, gaps, operational health |

For detailed usage, examples, and output formats, see **[docs/COMMANDS.md](docs/COMMANDS.md)**.

---

## Why This Changes Everything

9 real scenarios comparing vanilla Claude Code vs. the toolkit.

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

### 9. Error screenshot → manual debugging vs. visual diagnosis

**Without toolkit:**
```
[screenshot of a Python traceback in terminal]

You:    [squint at screenshot, manually copy the error message]
You:    [paste into Google: "TypeError cannot unpack non-iterable NoneType"]
You:    [read 4 Stack Overflow answers, none match your exact case]
You:    [manually search your codebase for the file mentioned in the trace]
You:    [spend 20 minutes tracing the call chain to find the actual bug]
You:    [fix it, forget to write a test, same bug returns 2 weeks later]
```

**With toolkit:**
```
/diagnose ~/Desktop/Screenshot 2026-02-25.png

Claude: [reads the screenshot visually]
        [extracts: TypeError at src/api/users.py:47, get_user() returns None]
        [greps codebase for get_user, reads the function]
        [searches memory for similar issues]
        [identifies root cause: missing null check]
        [offers to fix with TDD]

        "Want me to fix this now?"

You:    "yes"
Claude: [writes test_get_profile_returns_404_for_missing_user]
        [adds null check, test passes]
        [LEARNING] get_user() returns None for missing users -- always check
```

**The difference:** You screenshot the error and paste the path. Claude reads the image, traces the problem through your codebase, diagnoses the root cause, and offers to fix it with a test. What took 20 minutes of manual debugging becomes a 30-second conversation.

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

## Deep Dives

- **[docs/COMMANDS.md](docs/COMMANDS.md)** -- Full reference for every command with examples and output formats
- **[docs/AGENTS.md](docs/AGENTS.md)** -- What each agent produces and when they're dispatched
- **[docs/SELF-LEARNING.md](docs/SELF-LEARNING.md)** -- How the 5-layer learning system captures and uses knowledge
- **[docs/ADVANCED-PATTERNS.md](docs/ADVANCED-PATTERNS.md)** -- Skills crystallization, context recovery, post-audit remediation
- **[PLAYBOOK.md](PLAYBOOK.md)** -- Daily recipes and prompt patterns
