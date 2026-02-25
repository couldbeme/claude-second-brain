# Quick Start Guide

Get from zero to productive in 5 minutes.

---

## Install (30 seconds)

```bash
# 1. Clone the toolkit
git clone <repo-url> claude-code-team-toolkit
cd claude-code-team-toolkit

# 2. Install commands + agents (global -- works in all projects)
cp -r commands/ ~/.claude/commands/
cp -r agents/ ~/.claude/agents/

# 3. Install global rules
cp CLAUDE.md.template ~/.claude/CLAUDE.md
```

For project-scoped install, copy into `your-project/.claude/` instead.

### Optional: Memory system

Follow [SETUP-MEMORY.md](SETUP-MEMORY.md) to install persistent memory across sessions. The toolkit works without it, but memory makes Claude remember learnings, decisions, and patterns between conversations.

### Optional: Set up your project's CLAUDE.md

```
/new-project my-service "Brief description of what it does"
```

Creates a `.claude/CLAUDE.md` with command table, architecture section, and placeholders. Fill it in as you go.

---

## Your First 5 Minutes -- A Complete Walkthrough

Here's exactly what happens when a new team member uses the toolkit for the first time. This is a real workflow, not a toy example.

### Minute 1: Orient yourself

Open Claude Code in any existing project and type:

```
/guide tour
```

Claude responds with a categorized overview of all 18 commands. You now know what's available.

### Minute 2: Understand what you're working with

```
/status
```

```
Project Status
==============
Branch: main (3 commits ahead of origin)
Tests:  47 passed, 2 failed
Lint:   Clean
Next:   Fix failing tests in test_auth.py, then push
```

You instantly know where things stand -- no digging through git log or running commands manually.

### Minute 3: Fix something with tests

```
/tdd Fix the failing tests in test_auth.py
```

Claude:
1. Reads the failing tests to understand what's expected
2. Reads the source code that's being tested
3. Writes a fix that makes the tests pass
4. Runs the full suite to verify nothing else broke

```
TDD Cycle Complete
==================
RED:      2 failing tests identified (test_login_expired_token, test_refresh_token)
GREEN:    Fixed token expiry check in src/auth/tokens.py:34
REFACTOR: Extracted validate_expiry() helper
Tests:    49 passed, 0 failed
```

### Minute 4: Ship it

```
/verify
```

```
Verification Report
===================
Dependencies:      PASS
Lint:              PASS
Tests:             PASS (49/49)
Build:             PASS
Git:               PASS (clean, 4 commits ahead)
Overall:           HEALTHY
```

```
/commit-push-pr
```

Claude creates a branch, commits with a conventional message, pushes, and opens a PR -- all quality-gated (tests must pass first).

### Minute 5: Save what you learned

```
/learn from session
```

Claude scans the session, finds what was discovered (the token expiry bug, the fix pattern), and saves it to project memory. Next time anyone works on auth, they'll find this knowledge via `/recall auth tokens`.

### That's it

Five commands. Five minutes. You went from "what is this project?" to "PR is open with tests passing." Every future session starts smarter because the toolkit remembers what you learned.

---

## Hands-On Practice: The Sandbox

Want to try the toolkit commands on real (intentionally buggy) code? The sandbox is a small Python app with 4 planted issues.

```bash
cd examples/sandbox/
```

Then run:

```
/scan                                    # find all 4 issues
/tdd Fix the null return bug             # watch TDD in action
/verify                                  # confirm the fix
/audit security                          # see the hardcoded key flagged
/learn from session                      # save discoveries
```

See [examples/sandbox/README.md](examples/sandbox/README.md) for a full step-by-step walkthrough.

---

## Create Your Own Command

Found yourself repeating the same workflow? Turn it into a slash command with `/metaprompt`:

```
/metaprompt Create a command that adds a new API endpoint with route,
            schema, handler, tests, and docs

Claude: Generated command:

        ---
        description: Scaffold a new API endpoint with full test coverage
        argument-hint: <resource-name> <methods>
        ---

        # New Endpoint

        Phase 1: Create route in routes/$ARGUMENTS...
        Phase 2: Add Pydantic schema...
        Phase 3: Write handler...
        Phase 4: Add tests (happy path + 404 + validation)...
        Phase 5: Update API docs...

        Save as command? [yes]

        Saved to: .claude/commands/new-endpoint.md
```

Now anyone on the team can run:
```
/new-endpoint products GET,POST,DELETE
```

That's how the toolkit grows itself -- `/metaprompt` is the command that creates commands.

---

## What's Next

- `/guide [what you want to do]` -- get workflow advice anytime
- `/explain [module]` -- understand unfamiliar code before touching it
- `/audit` -- full health check before releases
- [TOOLKIT.md](TOOLKIT.md) -- the full guide with 9 Before & After scenarios
- [PLAYBOOK.md](PLAYBOOK.md) -- daily workflow recipes and prompt patterns
- [docs/COMMANDS.md](docs/COMMANDS.md) -- detailed reference for all 18 commands
