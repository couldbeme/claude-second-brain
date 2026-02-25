---
description: Identify gaps in code, tests, documentation, and error handling
argument-hint: Optional scope (e.g., "src/auth" or "tests")
---

# Gap Analysis

Systematically identify what is missing from the codebase. Scope: $ARGUMENTS (default: entire project)

## Execution

1. **Map what exists**: Use Glob to build a file inventory. Group by module/directory.

2. **Test gap analysis**: For each source file in scope:
   - Check if a corresponding test file exists
   - If tests exist, compare tested functions/methods vs actual public interface
   - Flag untested public functions, classes, and methods
   - Output as a table:

   | Source File | Test File | Tested | Untested | Coverage Gap |
   |-------------|-----------|--------|----------|--------------|

3. **Documentation gaps**: For each module:
   - Does it have a docstring/README?
   - Are public functions documented?
   - Are complex algorithms explained?
   - Is the module referenced in the top-level README/CLAUDE.md?

4. **Error handling gaps**: Scan for:
   - Bare `except:` or `except Exception:` without logging
   - Functions that can raise but callers do not handle
   - Missing input validation on public interfaces
   - Network calls without timeout or retry

5. **Type safety gaps** (Python): Scan for:
   - Public functions missing type hints
   - Functions using `Any` where a specific type is possible
   - Missing return type annotations

6. **Configuration gaps**:
   - Environment variables used but not in .env.example
   - Configuration values with no defaults
   - Missing validation of required config at startup

## Output

Present a prioritized gap report:
- **Critical gaps**: Missing tests for business logic, missing error handling on external calls
- **Important gaps**: Missing documentation, type hints on public API
- **Nice to have**: Internal function docs, additional edge case tests

For each gap, provide the specific file and line where action is needed.
