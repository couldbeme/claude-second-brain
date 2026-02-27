---
description: Analyze project context and assemble an optimal agent team for a complex task
argument-hint: <task description> (e.g., "Add real-time notifications with WebSocket backend and toast UI")
---

# Dynamic Team Assembly

Analyze the project and assemble the optimal agent team for this task.

## Input

Task: $ARGUMENTS

## Phase 0: Project Intelligence (run ALL in parallel)

Gather project signals by running these simultaneously:

**Stack Detection:**
1. Use Glob to check for: `package.json`, `requirements.txt`, `pyproject.toml`, `Cargo.toml`, `go.mod`, `Dockerfile`, `docker-compose.yml`, `.github/workflows/*.yml`, `k8s/**`, `terraform/**/*.tf`, `*.ipynb`, `migrations/**`, `prisma/schema.prisma`
2. If package.json exists, read it and check dependencies for: react, vue, next, svelte, angular, nuxt, express, fastapi, django, flask
3. If requirements.txt or pyproject.toml exists, check for: torch, tensorflow, sklearn, transformers, pandas, numpy, celery, fastapi, django, flask
4. Count files by type: `*.py`, `*.ts`/`*.tsx`, `*.go`, `*.rs`, `*.java`

**Health Signals:**
1. Check for cached scan results: `.claude/last-scan-scores.json` or recent `/scan` output in session
2. Read `CLAUDE.md` and `.claude/CLAUDE.md` for architecture notes, known gaps, TODO/FIXME items
3. Read `README.md` for project description and tech stack declarations

**Git Signals:**
1. Run: `git log --format=format: --name-only --since=3.months | grep -v '^$' | sort | uniq -c | sort -nr | head -15` (churn hotspots)
2. Run: `git log --oneline --since=1.month | head -20` (recent activity for task type patterns)

## Phase 1: Signal Analysis

From Phase 0 data, determine:

### 1. Detected Domains

| Signal | Domain | Maps To |
|--------|--------|---------|
| package.json + React/Vue/Next/Svelte/Angular | frontend | `senior-frontend-dev` |
| Python/Go/Rust/Java backend files + API framework | backend | `senior-backend-dev` |
| Both frontend AND backend detected in same repo | fullstack | `senior-fullstack-dev` (replaces both) |
| torch/tensorflow/sklearn/transformers detected | ml/data | `senior-data-scientist` + `ml-engineer` |
| Dockerfile + k8s/ + terraform/ + CI workflows | infrastructure | `devops-engineer` |
| migrations/ + *.sql + ORM schemas + prisma | database | `database-engineer` |
| .claude/agents/ + MCP config + LLM SDK imports | ai_surface | `security-auditor` (AI-mode, non-negotiable) |

**Consolidation rules:**
- If both frontend and backend detected: use `senior-fullstack-dev` (NOT frontend + backend separately)
- If ML detected: always pair `senior-data-scientist` + `ml-engineer`
- If AI surface detected: `security-auditor` is mandatory regardless of task type

### 2. Task Type Classification

Parse $ARGUMENTS for task type keywords:

| Keywords | Task Type | Core Agents Added |
|----------|-----------|-------------------|
| "add", "implement", "build", "create" | Feature | `architect` + domain expert + `tdd-agent` |
| "fix", "bug", "broken", "regression", "error" | Bugfix | domain expert + `tdd-agent` |
| "refactor", "clean", "restructure", "simplify" | Refactor | `architect` + `code-reviewer` + `tdd-agent` |
| "migrate", "upgrade", "replace", "move" | Migration | `architect` + domain expert + `verification-agent` |
| "performance", "slow", "optimize", "latency" | Performance | `performance-engineer` |
| "security", "vulnerability", "audit", "harden" | Security | `security-auditor` |
| "document", "readme", "api docs" | Documentation | `documentation-agent` |
| "deploy", "pipeline", "CI", "release", "infra" | DevOps | `devops-engineer` |
| "incident", "outage", "alert", "down", "SLO" | Incident | `sre-agent` |
| "test", "coverage", "flaky", "test strategy" | QA | `qa-strategist` |

### 3. Complexity Estimation

| Complexity | Signals | Max Agents |
|------------|---------|------------|
| Trivial | Single domain, < 10 word description, clear fix | 2-3 (suggest `/tdd` instead) |
| Simple | Single domain, clear scope, < 3 files expected | 3-4 |
| Medium | Multi-file, single domain, new patterns needed | 4-6 |
| Complex | Multi-domain, architectural changes | 6-8 |
| Large | System-wide, migration-scale | 7-9 (cap; split if > 9) |

### 4. Health-Driven Additions

If scan scores are available:

| Condition | Agent Added |
|-----------|-------------|
| security_score < 6 OR any critical finding | `security-auditor` |
| test_score < 6 | `tdd-agent` + `qa-strategist` |
| docs_score < 5 | `documentation-agent` |
| quality_score < 6 | `code-reviewer` |

### 5. Universal Agents

These are added to every non-trivial team:
- `code-reviewer` — always (confidence-scored review gate)
- `verification-agent` — always, runs LAST (final quality gate)

## Phase 2: Team Proposal

**STOP and present the team to the user before any execution.**

Format:

```
TEAM ASSEMBLY
=============
Project: [name from directory or CLAUDE.md]
Stack detected: [languages, frameworks, infra]
Task type: [classification]
Complexity: [level]

PROPOSED TEAM ([N] agents)

LAYER 0 — Analysis (parallel):
  [x] architect             reason: [why needed]
  [x] research-agent        reason: [why needed, or omitted if not]

LAYER 1 — Implementation (parallel):
  [x] senior-[domain]-dev   reason: [stack signal that triggered selection]
  [x] tdd-agent             reason: [task type requires tests]
  [x] database-engineer     reason: [migrations/ detected + task touches data]

LAYER 2 — Review (parallel, after Layer 1):
  [x] security-auditor      reason: [AI surface detected / scan score low]
  [x] code-reviewer         reason: [standard review gate]
  [x] qa-strategist         reason: [test score < 6]

LAYER 3 — Documentation (parallel with Layer 2):
  [x] documentation-agent   reason: [new public API being added]

LAYER 4 — Verification (final gate):
  [x] verification-agent    reason: [always]

NOT INCLUDED (and why):
  - performance-engineer: not a performance task; add if needed
  - devops-engineer: no infra files in scope for this task
  - sre-agent: not an incident; available if needed
  - ml-engineer: no ML stack detected

Estimated scope: [N] parallel tracks, ~[X] minutes
```

**Wait for user confirmation.** Accept: "yes", modifications ("add performance-engineer", "remove docs agent"), or "explain" for more detail on any selection.

## Phase 3: Execution (layer-strict)

After user confirms, execute by layer. **NEVER start Layer N+1 before Layer N completes.**

### Layer 0 — Analysis (parallel)
Launch `architect` and/or `research-agent` simultaneously using the Task tool.
- Architect: analyze codebase, produce implementation blueprint
- Research: investigate any unknowns in the task

Wait for all Layer 0 agents to complete. Their output becomes context for Layer 1.

### Layer 1 — Implementation (parallel)
Launch all implementation agents simultaneously using the Task tool.
- Give each agent: the task, the architect's blueprint, their specific file scope
- Domain experts implement in their area
- `tdd-agent` writes tests for the implementation
- `database-engineer` handles schema/migration if applicable

Wait for all Layer 1 agents to complete. Check for file conflicts:
- Different functions/sections in same file → auto-merge
- Same lines in same file → escalate to user with both versions
- Security fixes always win over style changes
- Architect blueprint is the interface contract; implementations conform to it

### Layer 2 — Review (parallel)
Launch review agents simultaneously using the Task tool.
- `security-auditor`: review all Layer 1 output for vulnerabilities
- `code-reviewer`: review all Layer 1 output for bugs (>= 75% confidence only)
- `qa-strategist`: assess test strategy and coverage adequacy

Collect findings. Apply security patches. Flag review findings for user.

### Layer 3 — Documentation (parallel with Layer 2 if no conflicts expected)
Launch `documentation-agent` to update docs based on Layer 1 implementation.

### Layer 4 — Verification (always last, always sequential)
Launch `verification-agent` to run the full pipeline: deps → lint → tests → build.
- If PASS: proceed to report
- If FAIL: identify which agent's output caused the failure, report to user

## Phase 4: Report

```
TEAM EXECUTION COMPLETE
========================
Task: [description]
Team: [N] agents across [L] layers
Duration: [X] minutes

RESULTS BY LAYER
-----------------
Layer 0 (Analysis):
  architect:        [summary of blueprint decisions]

Layer 1 (Implementation):
  senior-[x]-dev:   [files modified, key changes]
  tdd-agent:        [tests written, all passing]
  database-engineer: [schema changes, migration strategy]

Layer 2 (Review):
  security-auditor: [N] findings ([critical/high/medium/low])
  code-reviewer:    [N] findings (confidence >= 75%)
  qa-strategist:    [test coverage assessment, recommendations]

Layer 3 (Documentation):
  documentation-agent: [docs updated]

Layer 4 (Verification):
  verification-agent: [GREEN/RED] — [details]

CONFLICTS RESOLVED: [N]
  [file]: [agents] → [resolution]

OPEN FINDINGS (require manual review):
  [SECURITY/HIGH] file.py:42 — [description]
  [REVIEW/85]     file.py:17 — [description]

LEARNINGS:
  [LEARNING] [any discoveries tagged for memory]

NEXT STEPS:
  1. [most important follow-on]
  2. [second if applicable]
```

## Rules

1. **Never skip the team proposal.** The user must approve before agents run.
2. **Layer-strict execution.** Never start Layer N+1 before Layer N completes. The 17x error trap: uncoordinated parallel agents amplify errors.
3. **9 agent hard cap.** If analysis suggests more, split the task first. "This task needs 12 agents" means the task needs decomposition, not a bigger team.
4. **Trivial task redirect.** If only 1-2 agents would be selected, suggest `/tdd`, `/audit`, or `/orchestrate` instead — team assembly overhead isn't worth it.
5. **verification-agent is never skipped.** Regardless of what else is trimmed.
6. **code-reviewer is on every non-trivial team.** It's the most practical quality gate.
7. **Fullstack consolidation.** If both frontend and backend detected, use `senior-fullstack-dev`. Don't deploy all three simultaneously.
8. **AI surface = mandatory security-auditor.** Non-negotiable.
9. **Save team patterns.** After successful execution, tag the team composition as a `[LEARNING]` for future reference.
