# Claude Second Brain
## Team Presentation

### How to use this deck

This is a markdown slide deck. Each `---` is a slide break. Use any markdown presentation tool (Marp, reveal.js, Slidev, Deckset) to render it, or present directly from the markdown.

Speaker notes are in `> SPEAKER NOTES:` blocks under each slide.

---

<!-- Slide 1: Title -->

# Claude Second Brain

**22 Slash Commands. 17 Specialized Agents. One Consistent Workflow.**

Structured AI-assisted development that enforces quality, learns from your project, and gets smarter over time.

> SPEAKER NOTES: This isn't "yet another AI tool." It's a workflow enforcement layer on top of Claude Code that turns ad-hoc AI prompting into repeatable, quality-gated processes. Today I'll show you what it does, why it's different, how to adopt it safely, and I'll be honest about the limitations.

---

<!-- Slide 2: The Problem -->

# The Problem We're Solving

**AI code generation without guardrails is producing more bugs, not fewer.**

| Finding | Source |
|---------|--------|
| AI-generated PRs contain **1.7x more issues** than human-written ones | CodeRabbit, 2025 |
| Static analysis warnings **increased 30%** after AI tool adoption | CMU, 2025 |
| **59%** of developers use AI-generated code they don't fully understand | Clutch.co, 2025 |
| Developer trust in AI dropped to **29%** (down from 40%) | Stack Overflow, 2025 |

The failure mode: confident, plausible-looking code with subtle logic bugs that pass shallow review.

> SPEAKER NOTES: I'm leading with the bad news intentionally. The data is clear: unstructured AI coding produces more defects. The code "looks right" in a way sloppy human code doesn't, which makes bugs harder to catch. We're not here to pretend AI is magic. We're here to talk about making it safe and productive.

---

<!-- Slide 3: The Core Idea -->

# The Core Idea

**Don't trust the AI. Structure the workflow.**

```
                 You (the developer)
                        |
                  Your decision
                        ^
              Orchestrator (escalates)
                        ^
              Agents (report findings)
```

- Tests prove correctness -- not the AI's confidence in its own output
- Commands enforce phases: analyze first, test first, verify after
- Every change goes through quality gates before it can be committed
- The human is always in the loop for decisions

> SPEAKER NOTES: The toolkit is NOT a code generator. It's a set of workflow constraints. The key insight: if you force TDD, the test is the proof of correctness -- not the AI's belief that it wrote correct code. If you force verification before commits, broken code physically cannot leave your machine. The AI is powerful, but the guardrails are what make it safe.

---

<!-- Slide 4: What's In the Box -->

# What's In the Box

| Category | Commands | What They Do |
|----------|----------|--------------|
| **Orient** | `/status`, `/explain`, `/recall`, `/guide` | Understand where you are and what you have |
| **Build** | `/tdd`, `/diagnose`, `/verify`, `/commit-push-pr` | Write quality code with enforced TDD |
| **Analyze** | `/audit`, `/gap-analysis`, `/scan`, `/research` | Find security, quality, and coverage gaps |
| **Sustain** | `/document`, `/new-project`, `/learn`, `/sync-memories` | Keep docs and knowledge current |
| **Meta** | `/orchestrate`, `/metaprompt` | Decompose complex tasks, create new commands |
| **Assemble** | `/team` | Dynamic agent team assembly based on project context |
| **Collaborate** | `/flag`, `/resolve-pr`, `/sync-skill-docs` | Work effectively with your team |

**7 Role-Based Agents:** architect, tdd-agent, security-auditor, code-reviewer, documentation-agent, research-agent, verification-agent

**10 Domain Expert Agents:** senior-frontend-dev, senior-backend-dev, senior-fullstack-dev, senior-data-scientist, ml-engineer, devops-engineer, database-engineer, performance-engineer, sre-agent, qa-strategist

> SPEAKER NOTES: 24 commands in 7 categories. You don't need to memorize them -- `/guide` tells you which command to use for any situation. `/team` auto-detects your stack and assembles the right specialists. The agents run behind commands like `/orchestrate`, `/team`, and `/audit`. Each agent has restricted tool access (least-privilege) and a focused role.

---

<!-- Slide 5: Before & After -- Onboarding -->

# Before & After: Understanding Unfamiliar Code

**Without toolkit (20 minutes):**
```
You:    "How does the payment system work?"
Claude: [reads 15 files, gives wall of text]
        [misses the webhook retry logic]
        ...20 minutes later you're still piecing it together
```

**With toolkit (3 minutes):**
```
/explain src/payments/

## High Level
Payment service: Stripe checkout -> webhook -> fulfillment

## Medium Level
POST /checkout -> create_session() -> Stripe redirect
                                        |
webhook /stripe/events -> verify_signature() -> process_event()
    |-- payment_intent.succeeded -> fulfill_order()
    |-- payment_intent.failed -> notify_user() + retry queue

## Detail Level
- Webhook retries: 3 attempts, exponential backoff (webhooks.py:67)
- Idempotency key in Redis (checkout.py:52) -- prevents double charges
- Known quirk: Stripe sends duplicate events ~2% of the time (webhooks.py:31)
```

> SPEAKER NOTES: The `/explain` command gives three depth levels. You choose how deep to go. It includes ASCII data flow diagrams, specific file:line references, and known quirks. This is what onboarding looks like: 3 minutes to full understanding vs. 20 minutes of file-by-file archaeology.

---

<!-- Slide 6: Before & After -- Shipping Safely -->

# Before & After: Shipping Code

**Without toolkit:**
```
You:    "Commit this"
Claude: [commits directly to main]
        [tests were actually failing]
        [CI breaks, team gets notified]
        [you spend an hour reverting]
```

**With toolkit:**
```
/commit-push-pr

Claude: Running tests first...
        BLOCKED: 2 tests failing in test_auth.py

        test_token_refresh: Expected 200, got 401
          -> token_refresh() doesn't extend expiry (auth.py:89)

        Fix these before committing? I can help.
```

**Broken code never leaves your machine.**

> SPEAKER NOTES: The `/commit-push-pr` command is the quality gate. It runs the full test suite before committing. If tests fail, it tells you exactly what's wrong with file and line references. It creates a branch (never commits to main), uses conventional commit messages, and opens a PR with a test plan. This is the "it works on my machine" killer.

---

<!-- Slide 7: Before & After -- The Audit -->

# Before & After: Finding Problems on Your Terms

```
/audit

Codebase Audit -- Scorecard
============================
| Dimension   | Score | Top Issue                                          |
|-------------|-------|----------------------------------------------------|
| Security    | 4/10  | SQL injection in search_users() -- f-string in query |
| Tests       | 6/10  | Payment webhook handler has 0 test coverage         |
| Quality     | 7/10  | 3 functions over 200 lines, should be split         |
| Docs        | 5/10  | README still references pip (project uses poetry)   |
| Performance | 8/10  | N+1 query in /api/users/list                        |

[CRITICAL] SQL Injection -- src/users/search.py:34
  query = f"SELECT * FROM users WHERE name LIKE '%{term}%'"
  Fix: Use parameterized query

[CRITICAL] No tests for payment webhook -- src/payments/webhooks.py
  This handles money. 0 tests = 0 confidence.
```

**You find problems at your desk, not during an incident at 2 AM.**

> SPEAKER NOTES: Run `/audit` on a codebase you think is solid. You might be surprised. The 5-dimension scorecard gives you a quantified health picture. Findings include file:line references and specific fixes. The `/scan` command is even broader -- it adds operational health and cross-dimension severity uplift.

---

<!-- Slide 8: The Learning Loop -->

# The Learning Loop: Claude Gets Smarter Over Time

**Session 1:**
```
You:    "Wrong approach -- we run 4 replicas, use Redis"
Claude: [LEARNING] In-memory caching doesn't work -- service runs
        multiple replicas with no shared state. Always use Redis.
        [saved to project memory]
```

**Session 2:**
```
You:    "Add caching to the orders endpoint"
Claude: [reads project memory, sees the Redis rule]
        "Using Redis for caching (consistent with our multi-replica setup)."
        [gets it right the first time]
```

**Session 47:**
```
Claude has accumulated 80+ learnings about your project.
It knows your patterns, your gotchas, your preferences.
It feels like working with a teammate who's been on the project for months.
```

> SPEAKER NOTES: This is the most powerful feature and the most unique. The 5-layer learning system captures corrections, detects patterns, builds a user model, and persists everything across sessions. Every correction makes every future session better. By session 47, Claude knows YOUR project deeply -- architecture, conventions, gotchas, your team's standards. The memory system uses local SQLite with optional semantic search via embeddings. Your data stays on your machine.

---

<!-- Slide 9: Complex Feature Orchestration -->

# Multi-Agent Orchestration

```
/orchestrate Add Stripe subscription billing with webhooks,
             usage metering, and upgrade/downgrade flows

Claude: Breaking this into 5 workstreams:

1. [architect]           Design billing module structure    (independent)
2. [tdd-agent]           Implement subscription CRUD       (depends on 1)
3. [tdd-agent]           Implement webhook handlers        (depends on 1)
4. [security-auditor]    Review for PCI compliance         (depends on 2, 3)
5. [documentation-agent] Update API docs                   (depends on 2, 3)

Agents 2+3 run in parallel after architect completes.
Approve this plan? [yes]

Results:
- 12 files created/modified
- 34 tests written (all passing)
- 1 security finding fixed (webhook signature not verified)
- API docs generated
- Total time: ~15 minutes of your attention
```

> SPEAKER NOTES: `/orchestrate` decomposes complex features into agent workstreams. It identifies dependencies, runs independent agents in parallel, and integrates results. You approve the plan before execution starts. Every agent follows its specialization -- tdd-agent won't write code without tests, security-auditor has no write access, etc. This is how you tackle features that would take days in one 15-minute session.

---

<!-- Slide 10: The Full Dev Suite -->

# 17 Agents: The Full Dev Suite

**7 Role-Based Agents** (workflow enforcement):

| Agent | Role | Trust Level |
|-------|------|-------------|
| architect | Design blueprints | Read-only |
| tdd-agent | Test-first implementation | Full write |
| security-auditor | Vulnerability scanning | Read-only |
| code-reviewer | Bug detection (>= 75% confidence) | Read-only |
| documentation-agent | Doc generation as diffs | Write (docs) |
| research-agent | Multi-source investigation | Read + web |
| verification-agent | Test/lint/build pipeline | Run commands |

**10 Domain Expert Agents** (senior-level specialization):

| Agent | Seniority | Expertise |
|-------|-----------|-----------|
| senior-frontend-dev | 15+ years | React/Vue/Angular, a11y, Core Web Vitals |
| senior-backend-dev | 15+ years | API design, databases, caching, auth |
| senior-fullstack-dev | 15+ years | End-to-end vertical slices |
| senior-data-scientist | 12+ years | ML, statistics, experiment design |
| ml-engineer | 12+ years | MLOps, model serving, pipelines |
| devops-engineer | 12+ years | CI/CD, Docker, K8s, Terraform |
| database-engineer | 15+ years | Schema, query optimization, migrations |
| performance-engineer | 12+ years | Profiling, load testing, benchmarking |
| sre-agent | 12+ years | Incident response, SLOs, postmortems |
| qa-strategist | 12+ years | Test strategy, contract & mutation testing |

> SPEAKER NOTES: Each domain expert brings deep, real-world expertise baked into their prompt. The senior-frontend-dev thinks in component trees and accessibility. The database-engineer thinks in EXPLAIN ANALYZE and zero-downtime migrations. The sre-agent thinks in timelines and blast radius. These aren't generic "write code" agents — they're senior specialists who know the patterns, gotchas, and best practices of their domain.

---

<!-- Slide 10b: Dynamic Team Assembly -->

# /team: Dynamic Agent Team Assembly

```
/team Add real-time notifications with WebSocket backend and toast UI

TEAM ASSEMBLY
=============
Stack detected: React (frontend), FastAPI (backend), PostgreSQL
Task type: Feature
Complexity: Complex (multi-domain)

PROPOSED TEAM (7 agents)

LAYER 0 — Analysis:
  [x] architect              React + FastAPI patterns detected

LAYER 1 — Implementation:
  [x] senior-fullstack-dev   Both frontend & backend in scope
  [x] tdd-agent              Feature task: tests required
  [x] database-engineer      migrations/ directory detected

LAYER 2 — Review:
  [x] security-auditor       WebSocket auth needs review
  [x] code-reviewer          Standard quality gate

LAYER 4 — Verification:
  [x] verification-agent     Always

NOT INCLUDED: ml-engineer (no ML stack), sre-agent (not incident),
              performance-engineer (add with --perf if needed)

Proceed? [yes]
```

**The command detects your stack, classifies your task, and assembles the right team automatically.**

> SPEAKER NOTES: This is the key innovation over static team templates. The /team command reads your project — package.json, requirements.txt, Dockerfiles, scan scores, git churn hotspots, CLAUDE.md — and dynamically selects agents. It shows you WHY each agent was included and WHY others were excluded. You approve before anything runs. Execution is layer-strict: analysis before implementation, implementation before review, verification always last. Hard cap at 9 agents — if the task needs more, it needs decomposition first.

---

<!-- Slide 10c: Creating Custom Agent Teams -->

# Build ANY Agent Team with /orchestrate

The toolkit doesn't limit you to predefined workflows. **You compose agent teams for any task.**

### The Pattern

```
/orchestrate [complex task description]
Constraints:
- [what to touch / not touch]
- [quality requirements]
- [patterns to follow]
```

### How It Works

1. **You describe the goal** -- plain English, with constraints
2. **Orchestrator decomposes** -- identifies subtasks, dependencies, agent assignments
3. **You approve the plan** -- adjust before any work starts
4. **Agents execute** -- parallel where independent, sequential where dependent
5. **Results integrate** -- conflicts resolved, verification runs, unified report

### Real Example: This Presentation

```
/orchestrate Create a team presentation about the toolkit

Decomposition:
1. [research-agent]       Extract value props from all docs        (parallel)
2. [research-agent]       Prepare skeptical developer Q&A          (parallel)
3. [Explore agent]        Audit codebase for real statistics        (parallel)
4. [documentation-agent]  Write slide deck + speaker notes          (depends on 1,2,3)

Agents 1-3 ran in parallel. Agent 4 waited for all three.
Result: This deck you're reading now.
```

> SPEAKER NOTES: This is a key point -- the agent team pattern is general-purpose. The 7 built-in agents cover the most common roles, but the orchestrator dynamically composes them based on YOUR task. The presentation you're looking at right now was built this way: 3 research agents ran in parallel, a 4th agent synthesized results. Any complex task can be decomposed this way. The constraints in your prompt shape what the agents do.

---

<!-- Slide 11: Agent Team Composition Cookbook -->

# Agent Team Cookbook: Proven Patterns

### Pattern 1: Feature Build (most common)
```
architect -> tdd-agent (parallel) -> security-auditor -> verification-agent
                                  -> documentation-agent
```

### Pattern 2: Codebase Health Check
```
security-auditor (parallel) -> verification-agent (final gate)
code-reviewer    (parallel)
research-agent   (parallel, for dependency analysis)
```

### Pattern 3: Investigation & Fix
```
research-agent -> architect (design fix) -> tdd-agent -> verification-agent
```

### Pattern 4: Pre-Release Gate
```
verification-agent (parallel) -> documentation-agent (update release notes)
security-auditor   (parallel)
code-reviewer      (parallel)
```

### Pattern 5: Knowledge Transfer
```
research-agent (analyze codebase) -> documentation-agent (write docs)
                                  -> architect (create diagrams)
```

### Key Principle: Match agent to need, not task to template

| Need | Agent | Why |
|------|-------|-----|
| "How should I build it?" | architect | Reads codebase patterns, produces blueprints |
| "Build it with tests" | tdd-agent | Red-green-refactor, full write access |
| "Is it secure?" | security-auditor | OWASP + AI threats, read-only access |
| "Find bugs" | code-reviewer | Confidence-scored, only reports >= 75% |
| "Write the docs" | documentation-agent | Diffs only, matches project style |
| "Research this" | research-agent | Web + code + comparative analysis |
| "Does it all work?" | verification-agent | Sequential test/lint/build pipeline |

> SPEAKER NOTES: These are the proven composition patterns we've used. The key insight is that agents have different trust levels -- security-auditor is read-only, tdd-agent has write access. The orchestrator respects these boundaries. You can invent new patterns by describing what you need. The orchestrator figures out the agent assignments and dependency graph. Think of it like composing a project team: you specify the roles and goals, the orchestrator manages execution.

---

<!-- Slide 12: Remediation Loop -->

# The Audit-to-Fix Loop: Quantified Improvement

```
/scan
-> Scorecard: Security 4/10, Tests 6/10
-> 14 findings (3 critical)

/tdd Fix SQL injection in search_users()
  RED:   test_search_users_sql_injection()
  GREEN: Replaced f-strings with parameterized queries (3 locations)

/tdd Add payment webhook tests
  RED:   4 failing tests (success, failure, duplicate, invalid signature)
  GREEN: All 4 passing

/scan
-> Before: 14 findings, 3 critical, overall 6/10
-> After:  8 findings, 0 critical, overall 8.2/10
```

**Every fix is TDD-gated. Progress is measurable.**

> SPEAKER NOTES: This is the remediation workflow. Scan to find problems, TDD to fix them, scan again to measure progress. The before/after scorecard is what you show in sprint reviews. Each fix has tests that prevent regression. The learning system captures what was fixed so it's never missed again in future scans.

---

<!-- Slide 13: The /metaprompt -- Command Factory -->

# The Command That Creates Commands

```
/metaprompt Add a new API endpoint with route, schema, handler, tests, and docs

Generated command:
  ---
  description: Scaffold a new API endpoint with full test coverage
  argument-hint: <resource-name> <methods>
  ---

  Phase 1: Create route in routes/$ARGUMENTS...
  Phase 2: Add Pydantic schema...
  Phase 3: Write handler...
  Phase 4: Add tests (happy path + 404 + validation)...
  Phase 5: Update API docs...

  Saved to: .claude/commands/new-endpoint.md
```

**Now anyone on the team can run:**
```
/new-endpoint products GET,POST,DELETE
```

Every team has 10-20 invisible workflows that take 15 minutes each. Crystallizing them into commands means **15 minutes becomes 15 seconds**.

> SPEAKER NOTES: `/metaprompt` is how the toolkit grows itself. You describe a workflow in plain English, it generates an optimized slash command with phases, constraints, and verification steps. This is how tribal knowledge becomes shared infrastructure. That thing you do every time you add a new endpoint? Turn it into a command. Every team member benefits.

---

<!-- Slide 14: Installation & Adoption -->

# Adoption: Start Small, Grow Incrementally

### Install (30 seconds)
```bash
cp -r commands/ ~/.claude/commands/
cp -r agents/ ~/.claude/agents/
cp CLAUDE.md.template ~/.claude/CLAUDE.md
```

### Your First 5 Minutes
```
/guide tour                          # see everything
/status                              # where am I?
/tdd Add input validation to signup  # build something
/verify                              # health check
/learn from session                  # save discoveries
```

### Rollout Phases (from the Rollout Guide)

| Phase | Duration | What Happens |
|-------|----------|-------------|
| **Pilot** | Weeks 1-4 | One team, advisory mode only. Review results, don't gate PRs. |
| **Harden** | Weeks 5-8 | Tune false positive rate. Document finding-to-fix workflow. |
| **Expand** | Weeks 9-16 | Roll out to all teams. Pilot team graduates to enforced gates. |
| **Enforce** | Month 5+ | Quality gates on all PRs. Findings tracked in sprint metrics. |

**You use what helps. Skip what doesn't. Nothing is mandatory.**

> SPEAKER NOTES: Installation is literally copying files. No dependencies, no config, no build step. The rollout is phased by design -- advisory first, enforcement only after tuning. False positive rate target is < 20% before enforcement starts. Teams keep autonomy over which commands they use. The `/guide` command helps people find the right command for any situation.

---

<!-- Slide 15: Technical Architecture -->

# How It Works Under the Hood

### Slash Commands = Markdown + YAML

```yaml
---
description: What shows in autocomplete
argument-hint: Placeholder text
---

# Workflow phases, instructions, output formats
# Written in natural language
# Claude follows the structure when you type /command-name
```

### Agents = Focused Subprocesses
- Each agent has an explicit **tools list** (least-privilege)
- Read-only agents (security-auditor, code-reviewer) **cannot write files**
- Write agents (tdd-agent) have **full access but structured workflow**
- Agents return structured results to the orchestrator

### Memory = Local SQLite + Optional Embeddings
- **CLAUDE.md**: Project knowledge loaded at session start (human-readable)
- **SQLite DB**: Persistent memory across sessions (searchable)
- **LM Studio** (optional): Local embeddings for semantic search
- **Hybrid search**: 70% semantic + 30% keyword relevance
- **All local**: Your data never leaves your machine (except what Claude Code sends to Anthropic for processing)

> SPEAKER NOTES: No magic. Commands are markdown files with phased instructions. Agents are markdown definitions with tool restrictions. Memory is SQLite on your machine. LM Studio is optional -- without it, search falls back to keyword-only. The architecture is deliberately simple and inspectable. You can read every command and agent definition, modify them, or create your own.

---

<!-- Slide 16: Honest Limitations -->

# What We're NOT Claiming

**Let's be honest about what the toolkit doesn't do:**

- **AI still generates bugs.** The toolkit catches them via TDD and verification -- it doesn't prevent them.
- **Files Claude reads are sent to Anthropic.** This is Claude Code's model, not something the toolkit changes. Evaluate this for your security requirements.
- **TDD adds upfront time.** Research shows 15-35% more development time for fewer defects and lower maintenance cost. The friction is load-bearing.
- **Memory takes time to compound.** Session 1 gets less value than session 50. The learning curve is real.
- **Vendor dependency.** The toolkit runs on Claude Code. If Anthropic changes pricing or features, we're affected. The commands are portable markdown, the memory is local SQLite.
- **No CI/CD integration out of the box.** The toolkit is developer-side tooling. CI integration requires additional work.
- **The memory-mcp module has no unit tests.** We practice what we preach -- this gap is known and documented.

**A presentation that hides weaknesses is less credible than one that names them.**

> SPEAKER NOTES: I'm putting this slide here intentionally. Every tool has limitations, and acknowledging them builds trust. The AI will generate bugs -- the toolkit's job is to catch them before they ship. The TDD overhead is real, but the alternative is shipping more defects. Vendor dependency is a legitimate concern -- our mitigation is that the workflows are portable even if the tool changes. I'd rather you adopt this with clear eyes than discover the limitations after committing.

---

<!-- Slide 17: Daily Workflow -->

# What Your Day Looks Like

### Morning
```
/status                              # where am I? what's in flight?
/recall what I was working on        # reload context from yesterday
```

### Building
```
/recall existing patterns            # check conventions before writing
/tdd Add [feature]                   # test-first implementation
/verify                              # everything green?
/commit-push-pr                      # quality-gated ship
```

### Investigating a Bug
```
/diagnose [screenshot or log]        # visual diagnosis from error image
/recall [error message]              # seen this before?
/tdd Fix [the bug]                   # test-first fix
/learn [what caused it]              # prevent recurrence
```

### End of Day
```
/learn from session                  # capture everything discovered
```

> SPEAKER NOTES: This is the practical daily workflow. Start with `/status` and `/recall` to orient. Use `/tdd` for everything you build. `/verify` before shipping, `/commit-push-pr` to ship. End with `/learn from session` to capture discoveries. The key habit is the `/learn` at end of day -- it scans the session for untagged corrections and saves them. Over weeks, this builds a rich project knowledge base.

---

<!-- Slide 18: Success Metrics -->

# How We'll Measure Success

| Metric | Target | How We Track |
|--------|--------|-------------|
| False positive rate | < 20% | Track flagged findings that were dismissed |
| Critical/High SLA compliance | > 80% within 2 quarters | Findings resolved within SLA |
| Time from finding to ticket | < 1 business day | Scan -> ticket workflow |
| Developer satisfaction | Positive trend QoQ | Quick survey each quarter |
| Findings triaged within 1 week | > 90% | Sprint tracking |
| Before/after scan scores | Improving trend | `/scan` scorecard deltas |

**Budget: 10-15% of sprint capacity for remediation (recommended by the Rollout Guide)**

> SPEAKER NOTES: These metrics come from the Rollout Guide. The false positive rate is critical -- if it's above 20%, developers lose trust in the tool and ignore findings. That's why we start in advisory mode and tune before enforcing. The 10-15% sprint capacity for remediation is real cost -- plan for it upfront rather than discovering it mid-sprint.

---

<!-- Slide 19: Getting Started -->

# Next Steps

1. **Today**: Install the toolkit (30 seconds: `cp -r commands/ ~/.claude/commands/`)
2. **This week**: Try `/guide tour`, then `/status` and `/explain` on your current project
3. **Next week**: Use `/tdd` for one feature. Use `/verify` before one PR.
4. **Month 1**: Run `/scan` on your repo. Discuss findings as a team.
5. **Month 2**: Evaluate which commands help. Drop what doesn't. Keep what does.

### Resources

| Resource | What It Covers |
|----------|---------------|
| `QUICK-START.md` | Install + 5-minute walkthrough |
| `TOOLKIT.md` | 9 before/after scenarios |
| `PLAYBOOK.md` | Daily recipes and prompt patterns |
| `docs/COMMANDS.md` | Full command reference |
| `docs/ROLLOUT-GUIDE.md` | Team rollout cadence |
| `examples/sandbox/` | Practice on intentionally buggy code |

**Try the sandbox**: `cd examples/sandbox/ && /scan` -- find all 5 planted bugs.

> SPEAKER NOTES: Low commitment start. Copy files, try `/guide tour`, pick one command that interests you. The sandbox is great for hands-on practice -- it has 5 intentional bugs (hardcoded API key, bare except, null return, no tests, auth bypass) designed to demonstrate different toolkit commands. No pressure to use everything. Start with what solves a problem you already have.

---

<!-- Slide 20: The Bottom Line -->

# The Bottom Line

**AI-assisted development is happening.** The question isn't whether to use it -- it's whether to use it with guardrails or without.

- **Without guardrails**: 1.7x more bugs, lost tribal knowledge, inconsistent quality
- **With the toolkit**: TDD enforcement, quality gates, persistent learning, structured workflows

The toolkit doesn't make the AI perfect. It makes AI-assisted development **safe, consistent, and improvable**.

Every correction becomes a permanent learning.
Every workflow becomes a reusable command.
Every session starts smarter than the last.

> SPEAKER NOTES: Close with this framing. It's not about whether AI is good or bad -- it's about whether we use it responsibly. The toolkit is the responsible way. Start small, measure results, expand what works. The goal: same speed benefits of AI, without the quality regression that the research is showing across the industry.

---

# Appendix A: Tricky Questions & Honest Answers

---

## "Is this just AI hype?"

**Q: Does AI-assisted development actually improve quality, or does it just produce slop faster?**

Current evidence is mixed. CodeRabbit found AI PRs have 1.7x more issues. CMU found 30% more static analysis warnings post-adoption. The toolkit doesn't pretend this isn't true -- it exists because it IS true.

The toolkit's response: **workflow constraints, not more AI.** TDD requires a failing test before implementation. `/commit-push-pr` blocks on failing tests. `/audit` catches what you missed. The test is the proof of correctness -- not the AI's confidence.

**Demo**: Run `/audit` on a codebase you trust. See what it finds.

---

## "How is this different from Copilot / Cursor / ChatGPT?"

**Different category of tool.** Copilot suggests code inline. The toolkit enforces development workflows.

- Copilot doesn't block your commit because tests fail
- ChatGPT doesn't remember that your team standardized on Redis for caching
- Cursor doesn't run a 7-step health check before your PR

The differentiation is the **workflow enforcement layer**, not the underlying model. You can use Copilot AND the toolkit -- they're complementary.

---

## "What are the actual failure modes?"

1. **Hallucinated packages** -- ~20% of AI-generated code recommends non-existent packages ("slopsquatting")
2. **Confident wrong code** -- looks correct, passes shallow review, has subtle logic bugs
3. **Session amnesia** -- without memory, Claude forgets everything each session
4. **Over-broad scope** -- Claude touches files you didn't intend without explicit constraints
5. **False confidence** -- Claude says "this should work" without running tests

**Toolkit defenses**: `/audit` checks dependencies, TDD catches logic errors, memory system prevents amnesia, scope constraints in `/orchestrate`, and the rule "verify before asserting -- prove it, don't claim it."

---

## "Will this slow me down?"

**Some commands are fast, some aren't. Honest breakdown:**

| Command | Time |
|---------|------|
| `/status` | Seconds |
| `/verify` | 1-3 minutes |
| `/scan` (small repo) | 2-5 minutes |
| `/scan` (large repo) | 15-30 minutes |
| `/tdd` (feature) | Depends on complexity |

TDD adds 15-35% upfront time. The question: does it reduce total time (including debugging, review rounds, incident response)?

**You don't have to use all commands.** Use what helps. `/guide` recommends the minimum set for your situation.

---

## "Do I HAVE to use all of this?"

**No.** The toolkit is a menu, not a checklist.

- Want just TDD? Use `/tdd`
- Want just a pre-PR gate? Use `/verify` + `/commit-push-pr`
- Want just visibility? Use `/scan`
- Want nothing? Don't type the commands. Nothing happens.

The CLAUDE.md rules are in YOUR file. You can edit them. The TDD rule says "push back once, then comply if insisted." You remain in control.

**Honest guidance**: the features with the most friction (TDD, blocked commits) have the most impact on defect rates. The friction is load-bearing. But partial adoption beats no adoption.

---

## "Is my code sent to Anthropic's servers?"

**Yes.** Files that Claude Code reads are sent to Anthropic for processing. This is not hidden -- it's Claude Code's architecture.

**What the toolkit adds for secrets:**
- Security-auditor scans for hardcoded API keys and credentials
- CLAUDE.md rule: "Never commit .env, credentials, or API keys"
- Memory database is local SQLite -- stays on your machine

**What the toolkit doesn't solve:** No automatic redaction before API calls. If your security policy prohibits sending code to third parties, evaluate whether Claude Code is appropriate for your use case. This is a real constraint to assess honestly.

**Mitigation**: Use `.claude/ignore` to exclude sensitive directories. Enterprise customers can negotiate Zero Data Retention agreements with Anthropic.

---

## "Does this replace developers?"

**The labor market data is troubling for entry-level positions specifically.** Entry-level tech hiring decreased 25% YoY in 2024. 72% of tech leaders plan to reduce junior hiring while increasing AI investment.

**What the toolkit doesn't change**: This trend is driven by AI model capabilities, not by any specific tooling layer.

**What experience suggests is protected**: System design, architectural judgment, security review, debugging production issues, understanding business context, and identifying when AI is wrong. These become the expected baseline.

**What the toolkit does for learning**: TDD forces engagement with problem specification. `/explain` teaches codebase understanding. `/learn` documents knowledge explicitly. But -- a developer who uses `/tdd` without engaging with the tests is gaming the system, not learning from it.

---

## "What if Claude hallucinates?"

**It will. Plan for it.**

Developer trust in AI: 29% (Stack Overflow 2025). 1 in 5 AI suggestions contain factual errors.

**Structural defenses in the toolkit:**
- "No invented errors" rule: verify with Glob/Read before claiming
- "Verify before asserting" rule: run tests, don't just claim it works
- TDD: hallucinated API = failing test = caught immediately
- `/research`: requires sources, creates verification trail

**Rule of thumb**: Treat AI suggestions as proposals from a smart colleague who reads everything but tests nothing. Verify package names. Run the tests. Read security-sensitive code.

---

## "What about code review with AI-generated code?"

**AI code requires MORE careful review, not less.** Current practice is the inverse: developers spend less time reviewing AI code because it "looks right."

**Toolkit support for review:**
- Code-reviewer agent: confidence-scored findings (>= 75% only, no noise)
- `/flag`: structured investigation of suspicious findings with evidence
- Security-auditor: AI-specific checks (prompt injection, memory PII)
- `/scan` before every PR as a developer-side quality gate

**The merge button is still yours.** No tooling substitutes for reading and understanding what you're merging.

---

## "What if Anthropic changes pricing?"

**Legitimate concern. Here's the honest exposure:**

- The toolkit runs on Claude Code (requires Anthropic subscription)
- No migration path to other providers baked in
- Industry pattern: introductory pricing gets adjusted at production scale

**What reduces lock-in:**
- Commands are readable markdown -- portable to any tool
- Memory is local SQLite -- yours to keep
- Workflow patterns documented in PLAYBOOK.md work with any AI
- The real value is the workflows, not just the Claude integration

---

## "What about team members who don't want to use it?"

**That's fine.** The toolkit is opt-in at the individual level.

- Commands only run when typed. No background enforcement.
- Team-level enforcement (scan gates on PRs) only happens at Phase 4 of rollout, after months of advisory mode
- The pilot phase explicitly measures developer satisfaction

**Don't force it.** Let results do the convincing. If `/tdd` catches a bug that would have shipped, that's more persuasive than any presentation.

---

# Appendix B: Creating Custom Agent Teams

## The /orchestrate Pattern

Any complex task can be decomposed into an agent team. You describe the goal; the orchestrator identifies subtasks, assigns agents, and manages execution.

### Step-by-Step: How to Compose a Team

```
/orchestrate [your complex task]
Constraints:
- Scope: only modify [these directories]
- Quality: must have [coverage target]% test coverage
- Patterns: follow existing patterns in [reference directory]
- Security: handles [sensitive data type] -- security review required
```

### The 7 Agent Roles and When to Cast Them

| Role | Cast When You Need | Trust Level | Tools |
|------|-------------------|-------------|-------|
| **architect** | Design before building | Read-only analysis | Glob, Grep, Read, git log, git blame |
| **tdd-agent** | Implementation with tests | Full write access | Glob, Grep, Read, Edit, Write, Bash |
| **security-auditor** | Security review | Read-only | Glob, Grep, Read, WebSearch, git log |
| **code-reviewer** | Bug detection | Read-only | Glob, Grep, Read, git diff, git log |
| **documentation-agent** | Doc generation | Write (docs only) | Glob, Grep, Read, Edit, Write |
| **research-agent** | Investigation | Read + web | Glob, Grep, Read, WebSearch, WebFetch |
| **verification-agent** | Final validation | Run commands | Bash, Read, Glob, Grep |

### Composition Rules

1. **Architect first** -- design before building (unless the task is well-defined)
2. **Independent agents in parallel** -- research + security can run simultaneously
3. **TDD agents after architect** -- they need the blueprint
4. **Security after implementation** -- review what was actually built
5. **Verification last** -- the final gate before delivery
6. **Documentation alongside or after** -- accurate docs require seeing the code

### This Presentation Was Built by an Agent Team

```
Agent Team:
  [research-agent #1]  Extract value props from 10 docs       (parallel)
  [research-agent #2]  Prepare 25+ skeptical Q&As with sources (parallel)
  [Explore agent]      Audit codebase: 24 commands, 17 agents, (parallel)
                       2533 lines docs, 22 commits, 1301 LOC
  [orchestrator]       Synthesize all results into slide deck   (sequential)

3 agents ran in parallel. Results integrated into this deck.
Elapsed: ~20 minutes total.
```

---

# Appendix C: Toolkit by the Numbers

| Metric | Value |
|--------|-------|
| Slash commands | 22 |
| Specialized agents | 17 (7 role-based + 10 domain expert) |
| Documentation lines | 2,533 |
| Command categories | 7 (Orient, Build, Analyze, Sustain, Meta, Collaborate, Assemble) |
| Before/After scenarios | 9 (documented in TOOLKIT.md) |
| Learning system layers | 5 (auto-tag, correction detection, user model, explicit capture, semantic search) |
| Sandbox practice issues | 5 (hardcoded key, bare except, null bug, no tests, auth bypass) |
| Install time | 30 seconds |
| Rollout phases | 4 (Pilot -> Harden -> Expand -> Enforce) |
| Memory search | Hybrid: 70% semantic + 30% keyword |
| Agent trust levels | 3 (read-only, write-docs, full-write) |
| Domain expert seniority | 12-15+ years per agent |
| Team compositions | 5 standard (frontend, backend, fullstack, data, platform) |
| Max team size | 9 agents (hard cap, research-backed) |

---

# End

**Questions?**

Try now: `cp -r commands/ ~/.claude/commands/ && cp -r agents/ ~/.claude/agents/`

Then: `/guide tour`
