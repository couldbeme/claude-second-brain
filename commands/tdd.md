---
description: Start TDD workflow (red-green-refactor) for a feature or fix
argument-hint: Description of what to implement
---

# TDD Workflow: Red-Green-Refactor

You are implementing a feature or fix using strict Test-Driven Development. Follow this cycle precisely.

## Input

Task: $ARGUMENTS

## Project Test Conventions (read FIRST)

Before writing any test, check the project's test setup:

- **Test framework**: `unittest` (NOT pytest) unless project explicitly uses pytest
- **Discovery pattern**: `tests/test*.py` — new test files MUST match this pattern
- **Runner**: `.venv/bin/python3 -m unittest` — never bare `python3`
- **DB tests**: NEVER write tests that could touch the real database. Mock ALL DB calls
  with `MagicMock()`. Tests that check `is_read_only` or DB guard behavior must NOT
  instantiate real agents or open any cursors.
- **Cursor safety**: `pg8000` cursors do NOT support `with` context manager.
  Test mocks must reflect this — use `try/finally/cursor.close()` patterns.
- **Env vars**: `DRY_RUN=true` is always set. Tests relying on this must not override it.
- **Patch target**: patch at the import site of the module under test, not at definition.
  E.g., patch `src.server.iteration_browser.Config`, not `src.config.Config`.
- **Async tests**: use `unittest.IsolatedAsyncioTestCase` for async methods.

## Phase 1: RED — Write Failing Tests

1. Understand what needs to be built. If unclear, ask one round of clarifying questions, then proceed.
2. Find the nearest existing test file for the module being changed. Extend it before creating new files.
3. Write the minimal failing test(s) that define the desired behavior. Cover:
   - Happy path
   - Edge cases (empty input, None, boundary values)
   - Error cases (invalid input, missing dependencies)
4. Run the tests with `.venv/bin/python3 -m unittest <test.module> -v`.
   Confirm they FAIL for the right reason — NOT import errors or typos.
5. Report: "RED phase complete. N tests written, all failing as expected."

## Phase 2: GREEN — Make Tests Pass

1. Write the minimum code to make all tests pass. Do not optimize or refactor yet.
2. Follow existing code patterns (imports at module top, naming, type hints on public interfaces).
3. Run ALL tests — not just new ones: `.venv/bin/python3 -m unittest discover tests/ -v`
4. If tests fail, fix the implementation — never weaken a test to match wrong behavior.
5. Report: "GREEN phase complete. All N tests passing."

## Phase 3: REFACTOR — Clean Up

1. Review new code for:
   - Duplication (DRY)
   - Readability (clear names, small functions)
   - Consistency with project conventions
2. Refactor while keeping tests green. Run tests after each change.
3. Run the linter: `make lint` (Ruff, line length 250).
4. Report final state: files changed, test count, lint status.

## Rules

- Never skip the RED phase. If tests already pass, write NEW tests for the NEW behavior first.
- Each cycle should be small. Break large tasks into sub-tasks and TDD each.
- If tests pass when they should fail, investigate — the test may be wrong.
- For JS/frontend bugs with no Python test surface: write Python tests for the server-side
  behavior that feeds the UI, then fix the JS directly.
- One TDD cycle = one small behavior increment.
- Always return: which tests were written, which files were modified, final test counts.
- If you discover a bug in existing code during implementation, write a test for it first, then fix.
