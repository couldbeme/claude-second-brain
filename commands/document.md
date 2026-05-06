---
description: Generate or update documentation for the project
argument-hint: What to document (module, API, README, all)
---

# Documentation Generator

Generate or update documentation for the specified scope.

## Input

Scope: $ARGUMENTS

## Process

1. **Assess current documentation state**:
   - Find existing docs: README.md, CLAUDE.md, docstrings, inline comments
   - Identify what is documented vs undocumented
   - Check doc accuracy against current code

2. **Generate documentation** based on scope:

   **If "README" or "all"**:
   - Project title, description
   - Quick start (install, configure, run)
   - Architecture overview with diagram
   - API reference (if applicable)
   - Configuration reference
   - Contributing guide

   **If a specific module**:
   - Module docstring with purpose and usage example
   - Public class/function docstrings (Google style for Python)
   - Type annotations on public interfaces
   - Usage examples for non-obvious APIs

   **If "API"**:
   - Endpoint documentation (method, path, request/response schema)
   - Authentication requirements
   - Error codes and meanings
   - Example requests and responses

3. **Present documentation** as diffs against existing files.

4. **Ask for approval** before applying changes.

## Rules

- Match existing documentation style in the project.
- Keep docstrings concise. One line for simple functions. Multi-line for complex ones.
- Include examples for any function that takes non-obvious parameters.
- Never document implementation details that will change -- document behavior.
