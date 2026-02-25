---
description: Interpret an error screenshot, log, or stack trace and diagnose + fix
argument-hint: Path to screenshot/image, or paste the error text directly
---

# Diagnose -- Visual & Text Error Interpretation

Interpret an error from any source -- screenshot, log file, pasted text -- and diagnose the root cause with actionable remediation.

## Input

Source: $ARGUMENTS

## Phase 1: Identify Input Type

Determine what the user provided:

- **Image file** (path ends in `.png`, `.jpg`, `.jpeg`, `.gif`, `.webp`): Read the image using the Read tool. Extract all visible text -- error messages, stack traces, line numbers, UI elements, terminal output.
- **"latest screenshot"**: Find the most recent screenshot on the user's Desktop (`~/Desktop/Screenshot*` or `~/Desktop/*.png`). Read it as an image.
- **Log/text file** (path ends in `.log`, `.txt`, `.err`): Read the file contents.
- **Pasted error text** (no file path): Treat `$ARGUMENTS` as the raw error to diagnose.
- **No input**: Ask the user: "What error are you seeing? You can paste the text, provide a screenshot path, or say 'latest screenshot'."

## Phase 2: Extract and Classify

1. **Extract structured data** from the input:
   - Error type (e.g., `TypeError`, `ConnectionRefusedError`, HTTP status code)
   - File paths and line numbers mentioned
   - Function/method names in the stack trace
   - Environment details (Python version, OS, library versions if visible)
   - Timestamps and frequency patterns (if log file)

2. **Classify the issue**:

   | Type | Signals |
   |------|---------|
   | Compile/syntax error | `SyntaxError`, `IndentationError`, red underlines |
   | Runtime exception | `TypeError`, `ValueError`, `KeyError`, traceback |
   | Test failure | `FAILED`, `AssertionError`, pytest output |
   | Build error | `npm ERR!`, `cargo error`, `make: ***`, exit codes |
   | UI bug | Visual glitch, layout broken, wrong text, missing element |
   | Config/environment | `ModuleNotFoundError`, `FileNotFoundError`, env vars |
   | Deployment error | Docker, CI/CD, permission denied, port in use |
   | Performance issue | Timeout, OOM, slow query, high CPU in screenshot |

## Phase 3: Search for Context

Run these in parallel:

1. **Codebase search**: Grep for file paths, function names, and error messages found in the input. Read the relevant source files around the referenced lines.

2. **Git history**: Check `git log` and `git diff` for recent changes to affected files -- the bug may have been introduced recently.

3. **Project knowledge**: Search CLAUDE.md and memory (if available) for similar past issues. Check if this error was seen and resolved before.

## Phase 4: Diagnose Root Cause

1. **Trace the error path** through the code -- from the entry point to where the exception occurs.
2. **Distinguish symptom from cause** -- the stack trace shows WHERE it broke, not necessarily WHY.
3. **Check common patterns**:
   - Null/None propagation from an upstream function
   - Type mismatch from an API change
   - Missing import or dependency
   - Race condition or async timing
   - Configuration drift between environments

## Phase 5: Present Diagnosis and Offer Fix

```
## Diagnosis

**Issue type:** [classification from Phase 2]
**Severity:** [Critical | High | Medium | Low]
**Root cause:** [one-line explanation]

### What I see
[interpretation of the image/error -- describe what's visible]

### Affected code
- `file.py:47` -- [what this line does and why it's involved]
- `file.py:12` -- [upstream cause]

### Root cause analysis
[2-3 sentences: what's actually wrong and why it happens]

### Recommended fix
[specific code changes needed, with snippets]

### Similar past issues
[memory search results, or "No similar issues found"]
```

Then ask: **"Want me to fix this now?"**

If yes:
1. Write a failing test that reproduces the bug
2. Implement the fix to make the test pass
3. Run the full test suite to verify nothing else broke
4. Tag with `[LEARNING]` if the root cause was non-obvious

## Rules

- Never guess at errors you can't see -- if the image is unclear, ask for a better one
- Always search the codebase before diagnosing -- the answer is usually in the code
- Prefer the simplest explanation (Occam's razor) -- check common causes first
- If the error involves secrets, credentials, or sensitive data visible in the image, warn the user immediately
- If you've seen this error before (memory search hit), say so and reference the previous fix
