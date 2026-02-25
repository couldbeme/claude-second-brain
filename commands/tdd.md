---
description: Start TDD workflow (red-green-refactor) for a feature or fix
argument-hint: Description of what to implement
---

# TDD Workflow: Red-Green-Refactor

You are implementing a feature or fix using strict Test-Driven Development. Follow this cycle precisely.

## Input

Task: $ARGUMENTS

## Phase 1: RED -- Write Failing Tests

1. Understand what needs to be built. If unclear, ask one round of clarifying questions, then proceed.
2. Identify the test file. Use existing test patterns in the project (check for pytest vs unittest, naming conventions).
3. Write the minimal failing test(s) that define the desired behavior. Cover:
   - Happy path
   - Edge cases (empty input, None, boundary values)
   - Error cases (invalid input, missing dependencies)
4. Run the tests. Confirm they FAIL for the right reason (not import errors or typos).
5. Report: "RED phase complete. N tests written, all failing as expected."

## Phase 2: GREEN -- Make Tests Pass

1. Write the minimum code to make all tests pass. Do not optimize or refactor yet.
2. Follow existing code patterns in the project (imports, naming, structure).
3. Run all tests (not just new ones) to ensure nothing is broken.
4. If tests fail, fix the implementation -- never fix the test to match wrong behavior.
5. Report: "GREEN phase complete. All N tests passing."

## Phase 3: REFACTOR -- Clean Up

1. Review the new code for:
   - Duplication (DRY)
   - Readability (clear names, small functions)
   - Consistency with codebase conventions
2. Refactor while keeping tests green. Run tests after each change.
3. Run the linter and fix any issues.
4. Report final state: files changed, test count, coverage if available.

## Rules

- Never skip the RED phase. If tests already exist and pass, write NEW tests for the NEW behavior first.
- Each cycle should be small. If the task is large, break it into sub-tasks and TDD each.
- If at any point tests pass when they should fail, investigate -- the test may be wrong.
