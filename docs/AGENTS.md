# Agent Reference

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

---

## What Each Agent Actually Produces

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
