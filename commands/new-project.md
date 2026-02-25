---
description: Initialize a new project with CLAUDE.md from the standard template
argument-hint: Project name and brief description
---

# New Project Setup

Initialize a new project directory with the standard CLAUDE.md template.

## Input

Project: $ARGUMENTS

## Process

1. Parse the project name and description from arguments.
2. Create `.claude/CLAUDE.md` in the project root using the template below.
3. Fill in what you can infer, leave `[TODO]` placeholders for the rest.
4. Present the generated file for review before writing.

## Template

```markdown
# CLAUDE.md -- [PROJECT_NAME]

## Quick Reference

| Action | Command |
|--------|---------|
| Install deps | `[TODO]` |
| Run tests | `[TODO]` |
| Run single test | `[TODO]` |
| Lint | `[TODO]` |
| Auto-fix | `[TODO]` |
| Start dev | `[TODO]` |
| Build | `[TODO]` |

## Architecture

[TODO: 2-5 sentence description of what this project does and its core pattern.]

### Core Flow

```
[TODO: ASCII diagram of the main request/data flow]
```

### Key Directories

- **src/** -- [TODO]
- **tests/** -- [TODO: testing approach]

### Entry Points

- `[TODO]` -- [description]

## Domain Rules

- [TODO: Project-specific conventions]

## External Dependencies

- **Database:** [TODO or N/A]
- **APIs:** [TODO or N/A]
- **Infrastructure:** [TODO or N/A]

## Gotchas

- [TODO: Non-obvious things discovered during development]

## Current Focus

- [TODO: What is currently being worked on]
```
