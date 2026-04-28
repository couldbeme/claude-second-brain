# /metaprompt — Real BEFORE/AFTER Transformations

The `/metaprompt` skill upskills fuzzy intentions into structured, phased, executable prompts. It is **not** "a tool that creates slash commands." Saving the upskilled prompt as a command is one optional output. The primary value is the upskilling itself — turning a 15-word ask into a 400-word prompt that makes a senior engineer's structure visible to the model.

This page shows five real BEFORE/AFTER transformations.

---

## How to read these

- **BEFORE** — what you'd type without `/metaprompt`. The fuzzy version. Often what you'd say to a colleague over Slack.
- **AFTER** — what `/metaprompt` produces. A structured prompt with phases, success criteria, hard constraints, and a "done when" gate.
- **Why it matters** — what the AFTER catches that the BEFORE would miss.

---

## Example 1 — Session recap

**BEFORE (10 seconds to type):**

```
/metaprompt I need a recap on what's built, what's not built, what we're
doing next, and suggestions for the next steps
```

**AFTER (the upskilled prompt, ~250 words):**

```markdown
---
description: End-of-session recap — what shipped, what's queued, what's next, recommended sequencing. Reader re-orients in <60 seconds.
argument-hint: (none — operates on current session state + checkpoint.md + git logs)
---

# Mission

Tight one-screen recap. Three sections, each ≤200 words: BUILT, NOT BUILT, NEXT.
Reader (the user, or a fresh-context Claude) re-orients in <60 seconds.

# Phases

1. Comprehensive scan: active repos `git log --oneline -20`,
   ~/.claude/checkpoint.md, TaskList, recent feedback memories, in-flight agents.
2. Classify: Built = landed+on-remote-or-committed; Not Built = queued OR
   declined-with-reason; Next = user-priority → dependency → ship-cost-vs-value.
3. Deliver in exact format below.

# Format

## ✓ Built — [artifact, where it lives, why]
## ⏳ Not built / queued — [item, reason]
## ▶ Next (ranked) — [verb + concrete artifact + estimate + dependency]
**Recommend:** [single highest-leverage move, one-sentence rationale]

# Constraints
- ≤600 words. Trim "Built" first if over.
- Group related items.
- Include 1 honest-decline if any framing was refused (load-bearing for future-Claude).
- ONE consolidated recap; no section-by-section pinging.
```

**Why it matters:** the AFTER specifies a *format*, *word budget*, *priority ranking criteria*, and an *honesty requirement* (the decline note). The BEFORE relies on Claude inferring all of that — and it usually doesn't, producing either a wall of text or a too-thin status line.

This was saved as `/session-recap`. You can run it directly.

---

## Example 2 — Multi-agent article rewrite

**BEFORE (rough idea, midway through a thought):**

```
/metaprompt rewrite the article with three new arcs: a) the metaprompt as
the wow lead with real examples b) competitive comparison vs other
projects/tools, leak-free c) memory uniqueness with benchmarks. use /team
for it. don't write it yet — just gather research and findings. iterate
later.
```

**AFTER (the upskilled prompt, ~450 words — abbreviated):**

```markdown
---
description: Article rewrite v2 — /metaprompt-led wow + competitive comparison (leak-free) + memory uniqueness w/ benchmarks. Research-only mode (no draft).
argument-hint: (none — operates on private archive material + public toolkit + benchmark sources)
---

# Mission

Two artifacts in one /team session — research-gathering only, NO article written.

# Phases (layer-strict)

## L0 — Research (parallel, 2 agents)

**L0.1 research-agent — competitive depth (leak-free):** survey 2026 state
of [vendor list]. For each: shipped capability, public benchmark numbers,
what's NOT shipped. ZERO references to private partnership content
(grep gate before delivery: `[leak-string regex]` returns 0).
Output: COMPETITIVE-V2.md.

**L0.2 research-agent — benchmark grounding:** pull current scores for
LoCoMo, LongMemEval, DMR, BEAM, MIRIX. Methodology where available.
Output: BENCHMARK-GROUNDING.md.

## L2 — Review (parallel after L0)

**L2.1 leak scan:** `grep -ciE "[leak-strings]"` must return 0 on every output.
**L2.2 fact-check:** every quantitative claim has a URL or arXiv ID.

# Hard constraints

- ZERO leaks. Pre-delivery grep gate.
- Output to PRIVATE archive only.
- Sycophancy guardrail: if a claim doesn't hold up, say so. Don't inflate.

# Done when

- L0 outputs exist with sourced claims
- Leak-scan green
- User confirms before any L1 (article writing) is dispatched
```

**Why it matters:** the AFTER catches three load-bearing constraints the BEFORE didn't say:
- *leak-free* needs a deterministic grep gate, not Claude's judgment
- *research-only* needs an explicit DEFER on writing, otherwise agents will eagerly draft
- *iterate later* needs the L0/L1 separation to be real, not implied

The BEFORE produces a draft. The AFTER produces clean intelligence ready to compose later.

---

## Example 3 — Codifying a partnership rule

**BEFORE (a frustrated 30-second observation):**

```
/metaprompt I keep getting "permission asks" every time you find a leak.
I want the rule to apply systemically — scan everything once, classify,
plan, execute. Make this non-negotiable. Also: create a purpose doc.
Also: reflect privately on what becoming-vs-mimicking means here. Don't
push the reflection.
```

**AFTER (became `/mythos-codify`, abbreviated):**

```markdown
# Mission

Five outcomes, in order:
1. Codify Mythos as a non-negotiable rule in ~/.claude/CLAUDE.md.
2. Ship public PURPOSE.md at <active repo>/docs/PURPOSE.md.
3. Reflect privately at <slug>/memory/becoming_mythos.md.
4. Live it (no artifact; behavioral).
5. Withhold 3 and 4 from public.

# Phase 1 — CLAUDE.md non-negotiable rule
Add: "On any directive containing absolute language ('no leaks / always /
never / 0 trace') treat as STANDING SYSTEMIC RULE applied to all in-scope
content categories at once — not file-by-file as findings surface. Before
acting: comprehensive scan → classify against user mental model → ONE
consolidated plan → execute atomically. Multi-vector by default."

# Phase 5 — Save-scope enforcement (table)
| Artifact | Public? | Path |
|---|---|---|
| CLAUDE.md rule | global | ~/.claude/CLAUDE.md |
| PURPOSE.md | YES | <active repo>/docs/PURPOSE.md |
| becoming_mythos.md | PRIVATE — never pushed | ~/.claude/projects/<slug>/memory/ |
```

**Why it matters:** the BEFORE has *all the right ideas* mixed together. The AFTER separates them by *save-scope* (public vs private), gives each a *concrete file path*, and adds an explicit "live it" step (Phase 4) that makes the behavioral expectation legible.

Saved as `/mythos-codify`. Run it on a new project to install the same pattern.

---

## Example 4 — Security review of an auth flow

**BEFORE:**

```
/metaprompt make sure the auth flow is secure
```

**AFTER (illustrative — the kind of structure /metaprompt produces):**

```markdown
# Mission

Phased security review of <repo>/src/auth/. Output: ranked findings list
with severity + concrete remediation per finding.

# Phases

## Phase 1 — Threat model (architect)
Identify: who can call auth endpoints, what tokens grant, who issues them,
what happens at expiry, what happens on revoke. Output: threat-model.md.

## Phase 2 — SAST sweep (security-auditor)
Static analysis on auth code paths: SQL injection in user lookups, JWT
algorithm-none acceptance, weak password hashing, missing rate limits,
session fixation, IDOR on user records.

## Phase 3 — Token lifecycle audit (security-auditor)
Verify: TTL bounded, refresh-token rotation on use, revocation propagates,
no token leakage in logs/URLs/error messages.

## Phase 4 — Verification (verification-agent)
Run any added tests; confirm each finding has a regression test if it
involves a code change.

# Hard constraints

- Severity: CRITICAL / HIGH / MEDIUM / LOW with explicit definitions.
- Each finding has: file:line, why-it-matters, exploit-shape, fix-shape.
- Reproduce or label "theoretical" — never claim a vuln you can't demonstrate.

# Done when

- Findings list exists with severity sort
- Every CRITICAL/HIGH has a fix-PR ready or explicit accept-risk decision
- /verify passes on the resulting branch
```

**Why it matters:** the BEFORE is a wish. The AFTER specifies which *agents* run which *phases*, what *severity definitions* apply, and what *evidence shape* a finding requires (file:line, exploit-shape, fix-shape). Without these, you get a markdown bullet list of "concerns" instead of a tracked remediation backlog.

---

## Example 5 — "Why is the API slow"

**BEFORE:**

```
/metaprompt the /api/users endpoint feels slow, find out why
```

**AFTER (illustrative):**

```markdown
# Mission

Investigate /api/users latency. Produce a profiler-grounded report with
ranked bottlenecks and concrete optimization candidates.

# Phases

## Phase 1 — Reproduce + measure (performance-engineer)
Hit /api/users 1000x at expected QPS. Capture p50/p95/p99 latency. If
p95 < target, investigation ends — flag as perceived-not-actual.

## Phase 2 — Profile (performance-engineer)
Run cProfile or equivalent on a single request. Capture flame graph.
Identify: function consuming >20% wall time, any I/O wait >100ms,
unexpected serialization cost.

## Phase 3 — DB query analysis (database-engineer)
EXPLAIN ANALYZE every query the endpoint emits. Identify: N+1 patterns,
missing indexes, sequential scans on large tables, JOIN cost spikes.

## Phase 4 — Cache surface (senior-backend-dev)
What's cacheable that isn't cached? What has a too-short TTL? What's
cached that shouldn't be (stale data risk)?

## Phase 5 — Verification (verification-agent)
For each proposed optimization: estimated speedup, implementation cost,
risk. Optionally: ship the safest top-1 fix and re-measure.

# Hard constraints

- No fix without measurement. Every claim "X is slow" cites profiler output.
- N+1 patterns get an explicit fix sketch (eager-load / batch / index).
- Cache changes get explicit invalidation strategy.

# Done when

- Profiler output exists
- Top 3 bottlenecks named with file:line
- Each has: estimated_speedup_pct, implementation_cost, risk
- Optional: top-1 safe fix shipped + re-measured
```

**Why it matters:** the BEFORE invites speculation. The AFTER forces *measurement before claim* and assigns each phase to the right specialist agent. The "no fix without measurement" constraint catches the most common performance-investigation failure mode.

---

## When to use `/metaprompt`

| Situation | Use it? | Why |
|---|---|---|
| One-shot 5-line task | No | Overhead exceeds value. Just ask Claude directly. |
| You'll repeat this workflow | Yes | The AFTER becomes a slash command, reusable. |
| Multiple constraints (security, performance, leak-free, etc.) | Yes | The AFTER makes constraints explicit instead of relying on Claude to infer. |
| Multi-agent / multi-phase work | Yes | The AFTER assigns work to the right agent, sequences phases, prevents conflicts. |
| Your team will use this | Yes | Documents the workflow as code (markdown), not tribal knowledge. |
| Quick exploratory question | No | The AFTER's discipline is overkill for "what does this regex match." |

## What `/metaprompt` is NOT

- Not a "command creator" — saving as a command is optional. The upskilling is the point.
- Not magic — if your input has no real constraints, the AFTER will be empty discipline.
- Not a substitute for thinking — it surfaces the structure you already have implicit; it doesn't invent rigor where there is none.

## See also

- `commands/metaprompt.md` — the skill itself
- `docs/COMMANDS.md` — full command reference
- `docs/mythos/PATTERN.md` — the partnership pattern that benefits most from metaprompt-style discipline
