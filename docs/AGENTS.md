# Agent Reference

17 agents total: 7 role-based (dispatched automatically) + 10 domain experts (dispatched by `/team` and `/orchestrate`).

Most agents are dispatched automatically by commands. `/team` surfaces the proposed agent list for your review and modification before execution. `/orchestrate` lets you specify agents manually. Each agent has a focused role, specific tools, and a defined output format.

| Agent | Role | Specialization |
|-------|------|---------------|
| **architect** | Design | Analyzes codebase patterns, produces implementation blueprints with file paths and interfaces |
| **tdd-agent** | Implement | Strict TDD -- never writes code before a failing test |
| **security-auditor** | Security | OWASP checklist with severity ratings and specific fixes |
| **code-reviewer** | Review | Confidence-scored issue detection (only reports >= 75/100) |
| **documentation-agent** | Docs | Generates accurate, concise docs -- always as diffs |
| **research-agent** | Research | Multi-source investigation with citations and conflict detection |
| **verification-agent** | QA | Sequential test pipeline with traffic-light reporting |

### Domain Expert Agents (10)

| Agent | Seniority | Specialization |
|-------|-----------|---------------|
| **senior-frontend-dev** | 15+ years | React/Vue/Angular, CSS architecture, accessibility (WCAG 2.1 AA), Core Web Vitals, state management |
| **senior-backend-dev** | 15+ years | API design, databases, caching, queues, auth/authz, error handling, observability |
| **senior-fullstack-dev** | 15+ years | End-to-end features, API + UI integration, vertical slices, full-stack testing |
| **senior-data-scientist** | 12+ years | Statistical modeling, ML algorithms, experiment design, feature engineering, evaluation |
| **ml-engineer** | 12+ years | MLOps, model serving, pipelines, monitoring, reproducibility, Docker for ML |
| **devops-engineer** | 12+ years | CI/CD, Docker, Kubernetes, IaC (Terraform), monitoring, deployment strategy |
| **database-engineer** | 15+ years | Schema design, query optimization, zero-downtime migrations, indexing, PostgreSQL/MySQL |
| **performance-engineer** | 12+ years | Profiling, load testing, benchmarking, caching strategy, concurrency |
| **sre-agent** | 12+ years | Incident response, alert triage, log correlation, SLO breach analysis, postmortem facilitation |
| **qa-strategist** | 12+ years | Test strategy, contract testing, mutation testing, flaky test remediation, test architecture |

Domain experts are dispatched by `/team` (dynamic assembly) and `/orchestrate` (manual composition). They bring deep specialization and work alongside the 7 role-based agents.

---

## What Each Agent Actually Produces

### Role-Based Agents (7)

### architect

Dispatched first in most `/orchestrate` workflows. Reads the codebase to extract existing patterns, then produces a blueprint that downstream agents follow.

```
architect agent output:

  CODEBASE ANALYSIS
  Existing patterns found:
  - File structure: src/{module}/routes.py, schemas.py, service.py, models.py
  - Error handling: all routes use AppError(status, message, code)
  - DB pattern: Repository classes in models.py, no raw SQL
  - Tests: mirror structure in tests/{module}/test_*.py

  BLUEPRINT: Notifications Module
  Files to create:
    src/notifications/routes.py       -- POST /notifications, GET /notifications/{id}
    src/notifications/schemas.py      -- NotificationCreate, NotificationResponse
    src/notifications/service.py      -- NotificationService.send(), .get(), .mark_read()
    src/notifications/models.py       -- NotificationRepo

  Build sequence:
    1. models.py + schemas.py (no dependencies)
    2. service.py (depends on models)
    3. routes.py (depends on service + schemas)
    4. tests (after all implementation)
```

### tdd-agent

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
    Result: 3 PASSED

  REFACTOR — extracted Channel validation to schema layer
    Result: 3 PASSED (no behavior change)

  Summary:
  Files created: service.py, models.py, test_service.py, conftest.py
  Tests: 7 written, 7 passing
  Full suite: 84/84 passing (no regressions)
```

### security-auditor

Reviews code for OWASP top 10, LLM/AI-specific threats (prompt injection, tool safety, data poisoning), secret exposure, and unsafe patterns. Each finding has severity, evidence, and a specific fix.

```
security-auditor output:

  SECURITY AUDIT — src/notifications/ + src/ai/
  4 findings (0 critical, 2 high, 1 medium, 1 low)

  [SEVERITY: HIGH]
  File: src/notifications/routes.py:34
  Issue: User can request any notification by ID without ownership check
  Fix: Add ownership verification before returning data

  [SEVERITY: HIGH]
  File: src/ai/chat.py:23
  Issue: User message concatenated directly into system prompt via f-string.
         Prompt injection vector.
  Fix: Use structured message format with separate system/user roles

  No secrets found in source. .env is gitignored.
```

### code-reviewer

Reviews code changes (usually via git diff) and reports only issues with confidence >= 75/100. No nitpicks -- real bugs only.

```
code-reviewer output:

  Code Review — 4 files changed (+187, -23)

  Confidence: 95/100
  File: src/notifications/service.py:67
  Issue: Race condition in mark_read(). Two concurrent requests could both
         read status="unread", both attempt update.
  Suggestion: Use UPDATE ... WHERE status = 'unread' RETURNING id

  Confidence: 85/100
  File: src/notifications/routes.py:52
  Issue: POST returns 200 instead of 201 for resource creation.

  No issues below 75 threshold.
```

### documentation-agent

Generates documentation that matches the project's existing style. Always presents changes as diffs -- never overwrites silently. Prioritizes accuracy over completeness.

```
documentation-agent output:

  Documentation update for src/notifications/
  Assessed: 4 source files, 0 existing docs

  --- /dev/null
  +++ src/notifications/README.md
  +# Notifications Module
  +Handles multi-channel notifications (in-app, email, push).
  +## Endpoints
  +  POST /notifications    Create and send a notification
  +  GET  /notifications/:id  Retrieve (owner only)

  3 files updated. Apply changes? [yes / edit / skip]
```

### research-agent

Dispatched by `/orchestrate` or `/research` for technical investigation. Searches multiple sources, cross-references findings, and flags conflicting information.

```
research-agent output:

  Research: "async task queue options for our Python stack"

  Summary:
  Celery is the mature choice. Dramatiq is simpler and faster.
  For your stack (FastAPI + Redis already running), either works.

  Key Findings:
  - Celery 5.x supports async (source: docs.celeryq.dev)
  - Dramatiq: 2-3x faster throughput (source: GitHub benchmarks)
  - Your project already has Redis (src/core/cache.py:5)
  - Conflict: One source claims Celery doesn't support FastAPI async
    — INCORRECT, verified in official docs

  Recommendation: Celery — existing Redis + scheduled tasks + Flower dashboard
```

### verification-agent

The final gate. Runs a sequential pipeline: dependencies -> lint -> tests -> build -> smoke test. Outputs a traffic-light report. Any FAIL includes exact error output and suggested fix.

```
verification-agent output:

  VERIFICATION RESULTS
  ====================
  Dependencies:  PASS  All imports resolve
  Lint:          PASS  0 issues
  Unit tests:    PASS  84/84 passed
  Integration:   PASS  API endpoints respond correctly
  Build:         FAIL  Docker build fails — markupsafe version pin
                       Fix: Update Dockerfile line 23

  OVERALL: RED
  Action required: Fix markupsafe version, re-run build
```

---

## Domain Expert Agents (10)

### senior-frontend-dev

Brings 15+ years of frontend expertise. Thinks in component trees, data flow, and user experience. Enforces accessibility and performance budgets.

```
senior-frontend-dev output:

  COMPONENT DESIGN — ProductComparison
  ├── ProductGrid (responsive, lazy-loaded)
  │   ├── ProductCard (presentational, a11y: role="article")
  │   └── CompareCheckbox (keyboard accessible, aria-checked)
  ├── ComparisonDrawer (fixed position, focus trap)
  └── FilterBar (URL-synced state, debounced)

  Accessibility: All interactive elements keyboard-navigable.
    axe-core: 0 violations on new components.
  Performance: Bundle +12KB gzipped. No CLS impact (dimensions reserved).
  Tests: 8 component tests (Testing Library), 1 integration test.
```

### senior-backend-dev

Brings 15+ years of backend expertise. Designs APIs contract-first, thinks in failure modes, and prevents N+1 queries by default.

```
senior-backend-dev output:

  API CONTRACT — /api/v2/subscriptions
  POST   /subscriptions     → 201 {id, plan, status, created_at}
  GET    /subscriptions/:id → 200 {id, plan, status, usage, invoices[]}
  PATCH  /subscriptions/:id → 200 {updated fields}
  DELETE /subscriptions/:id → 204

  Error format: {error: {code, message, details[]}}
  Rate limit: 100/min per API key, 429 with Retry-After header

  Schema: subscriptions table with plan_id FK, status enum, Stripe refs
  Migration: add column (nullable) → backfill → add constraint
  Indexes: (user_id, status) partial index WHERE status = 'active'
  N+1 check: PASS — eager load invoices via subquery
```

### senior-fullstack-dev

Brings 15+ years of end-to-end expertise. Owns the full vertical slice from database to pixel.

```
senior-fullstack-dev output:

  USER STORY: "As a user, I can see real-time order status updates"

  Backend:  WebSocket endpoint /ws/orders/{id} with JWT auth
  Frontend: useOrderStatus() hook → OrderStatusBadge component
  Contract: {event: "status_changed", data: {order_id, status, timestamp}}

  E2E flow: place order → server processes → WS push → badge updates
  Fallback: polling every 30s if WS connection drops

  Tests: 3 API integration, 2 component, 1 E2E (Playwright)
```

### senior-data-scientist

Brings 12+ years of ML and statistical modeling expertise. Baseline-first, reproducibility-obsessed.

```
senior-data-scientist output:

  PROBLEM: Predict customer churn (binary classification)
  Metric: PR-AUC (imbalanced classes, 4% churn rate)
  Baseline: logistic regression on recency/frequency/monetary = 0.34 PR-AUC

  Model: gradient boosted trees (LightGBM)
  Features: 23 engineered, top 5 by importance:
    1. days_since_last_purchase (0.18)
    2. support_tickets_90d (0.14)
    3. purchase_frequency_trend (0.11)

  Results: 0.52 PR-AUC (+53% over baseline)
  Caveats: Model undertrained on enterprise tier (n=127). Recommend
           separate model or minimum sample threshold.
```

### ml-engineer

Brings 12+ years of MLOps expertise. Bridges notebooks to production systems.

```
ml-engineer output:

  SERVING ARCHITECTURE
  FastAPI endpoint → model loaded from MLflow registry → Redis cache (60s TTL)
  Latency budget: p50 < 50ms, p99 < 200ms (met: p50=23ms, p99=87ms)

  Pipeline: Dagster DAG → feature extraction → training → evaluation → registry
  Monitoring: PSI drift detection on top 10 features, daily check
  Rollback: model version pinned in config, 1-command rollback to previous

  Docker: python:3.11-slim + model artifact layer (430MB)
  Cost: 2x c5.xlarge ($0.17/hr), auto-scale 2-8 on CPU utilization
```

### devops-engineer

Brings 12+ years of infrastructure expertise. Automates everything, minimizes blast radius.

```
devops-engineer output:

  CI/CD PIPELINE (.github/workflows/deploy.yml)
  trigger: push to main
  stages: lint → test → build → scan → deploy-staging → smoke → deploy-prod

  Docker: multi-stage build, distroless runtime (87MB final image)
  Trivy scan: 0 critical, 0 high vulnerabilities

  Deployment: rolling update, 25% max surge, readiness probe on /health
  Rollback: automatic on failed health checks (3 consecutive failures)
  Secrets: GitHub Secrets → mounted as env vars, never baked into image
```

### database-engineer

Brings 15+ years of database expertise. Schema serves the query, not the other way around.

```
database-engineer output:

  MIGRATION: Add subscriptions table
  Strategy: backwards-compatible, zero-downtime

  Step 1: CREATE TABLE subscriptions (...)     -- no lock
  Step 2: CREATE INDEX CONCURRENTLY idx_...    -- no lock
  Step 3: Backfill from legacy table           -- batched, 1000/iteration
  Step 4: Add NOT NULL constraint              -- after backfill complete

  Estimated lock time: 0ms (all operations non-blocking)
  Rollback: DROP TABLE subscriptions (safe, no dependents yet)

  EXPLAIN ANALYZE on key queries:
    get_active_by_user: Index Scan, 0.08ms (was Seq Scan, 12ms)
```

### performance-engineer

Brings 12+ years of performance expertise. Profiles before optimizing, measures in percentiles.

```
performance-engineer output:

  PROFILING: /api/users/list endpoint
  Tool: py-spy (CPU) + tracemalloc (memory)

  Bottleneck: N+1 query in user_profiles loader (87% of request time)
    p50: 340ms → target: <100ms
    p99: 2.1s  → target: <500ms

  Fix: batch profile loading with DataLoader pattern
  Trade-off: +2MB memory for prefetch cache, -85% latency

  After: p50: 45ms, p99: 180ms
  Benchmark added: test_users_list_under_100ms (CI regression guard)
```

### sre-agent

Investigates production incidents. Containment first, blameless always.

```
sre-agent output:

  INCIDENT REPORT
  ===============
  Severity: P2
  Scope: /api/checkout returns 500 for 23% of requests
  Duration: 14:32 → 15:07 (35 minutes)

  TIMELINE
  14:32  Error rate spike: 5xx from 0.1% to 23%
  14:33  Alert fired: checkout_error_rate > 5%
  14:35  Correlated: deployment v2.4.1 at 14:30
  14:38  Root cause: new Stripe SDK requires TLS 1.3, ELB terminates at 1.2
  14:42  Mitigation: rollback to v2.4.0
  14:45  Error rate: 0.1% (nominal)

  PREVENTION: Pin Stripe SDK in requirements. Add TLS version check to CI.
```

### qa-strategist

Designs test strategy, not just tests. Decides WHAT to test and WHERE in the pyramid.

```
qa-strategist output:

  TEST STRATEGY ASSESSMENT
  ========================
  Current: 89% line coverage, but mutation score 41% (tests don't verify behavior)
  Pyramid: 95% unit / 3% integration / 2% E2E (inverted — too unit-heavy)

  PRIORITIES (by risk):
  1. [HIGH]  Add contract tests for /api/payments (external dependency, 0 contracts)
  2. [HIGH]  Add integration tests for auth flow (login → refresh → logout)
  3. [MED]   Mutation test src/billing/ (handles money, mutation score 28%)
  4. [LOW]   Fix 3 flaky tests in test_notifications (root cause: shared DB state)

  Flaky test fix: test_notification_send — shared fixture, needs transaction rollback
  Recommendation: Add pytest-randomly to CI (detect order-dependent tests)
```

---

## Team Compositions

The `/team` command dynamically assembles agent teams based on project context. These are the standard compositions (adjusted at runtime based on your project's stack, scan scores, and task type):

| Team | Core Agents | Size |
|------|------------|------|
| **frontend** | senior-frontend-dev, architect, tdd-agent, security-auditor, code-reviewer, documentation-agent, verification-agent | 7 |
| **backend** | senior-backend-dev, database-engineer, architect, tdd-agent, security-auditor, code-reviewer, documentation-agent, verification-agent | 8 |
| **fullstack** | senior-fullstack-dev, architect, database-engineer, tdd-agent, security-auditor, code-reviewer, verification-agent | 7 |
| **data** | senior-data-scientist, ml-engineer, architect, tdd-agent, security-auditor, code-reviewer, verification-agent | 7 |
| **platform** | devops-engineer, database-engineer, performance-engineer, sre-agent, security-auditor, code-reviewer, verification-agent | 7 |
