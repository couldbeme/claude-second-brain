---
description: Spawn a multi-agent team to tackle a complex task
argument-hint: Task description that requires multiple agents
---

# Agent Orchestration

Decompose a complex task into parallel workstreams executed by specialized agents.

## Input

Task: $ARGUMENTS

## Phase 1: Decomposition (you, the orchestrator)

1. Analyze the task. Identify:
   - Independent subtasks that can run in parallel
   - Sequential dependencies between subtasks
   - Required expertise per subtask (architecture, implementation, testing, security, docs)
2. Create a task list with dependencies.
3. Present the decomposition to the user and ask for approval before proceeding.

## Phase 2: Agent Dispatch

For each independent subtask group, launch the appropriate agent:

**Available agent roles:**

- **Architect agent**: Analyzes codebase patterns, designs component structure, defines interfaces. Returns: architecture blueprint with file paths and function signatures.
- **TDD agent**: Writes failing tests first, then implements to make them pass. Returns: test files and implementation files.
- **Security auditor agent**: Reviews changes for vulnerabilities, secret exposure, injection vectors. Returns: security findings with severity.
- **Code reviewer agent**: Reviews code for bugs, style violations, DRY violations, edge cases. Returns: issue list with confidence scores.
- **Documentation agent**: Writes or updates README, docstrings, CLAUDE.md, inline comments. Returns: documentation files.
- **Research agent**: Investigates APIs, libraries, patterns, or techniques. Returns: findings with code examples and trade-offs.
- **Verification agent**: Runs tests, linters, builds. Checks that everything works end-to-end. Returns: pass/fail report with details.

Rules for agent dispatch:
- Launch independent agents in parallel (use Task tool with multiple calls in one message)
- Wait for dependencies before launching dependent agents
- Give each agent: the subtask description, relevant file paths, success criteria
- Each agent must return: summary of what was done, files modified/created, and any concerns
- Every agent prompt must include: "Tag any non-obvious discovery with [LEARNING] in your response."

## Phase 3: Integration

1. Collect all agent results.
2. Check for conflicts (two agents modifying the same file).
3. Resolve conflicts by choosing the better version or merging.
4. Run verification: tests, lint, build.
5. Present unified result to user.

## Phase 4: Learning

Tag any discoveries with `[LEARNING]` for future CLAUDE.md updates.
