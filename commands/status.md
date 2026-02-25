---
description: Progress report on current work and project health
---

# Status Report

## Pre-computed Context

- Current git status: !`git status --short 2>/dev/null || echo "Not a git repo"`
- Current branch: !`git branch --show-current 2>/dev/null || echo "N/A"`
- Recent commits: !`git log --oneline -5 2>/dev/null || echo "No commits"`

## Report

Generate a concise status report covering:

### 1. Current Session Work
- What has been accomplished this session
- What is currently in progress
- What is blocked or needs input

### 2. Git State
- Uncommitted changes (list modified files)
- Branch status relative to remote
- Any stashed work

### 3. Project Health Snapshot
- Run tests and report pass/fail count (use the project's test command from CLAUDE.md)
- Run linter and report issue count
- Note any failing CI checks if visible

### 4. Next Steps
- Immediate next actions based on current work
- Any questions that need answering before proceeding

Format as a clean, scannable report. Use tables where helpful. Keep it under 50 lines.
