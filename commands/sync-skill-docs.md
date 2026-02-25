---
description: Sync a new or updated skill to the claude-code-team-toolkit docs
argument-hint: skill name (e.g., "flag") or "all" to sync everything
---

# Sync Skill Documentation to Team Toolkit

When a new skill (slash command or agent) is created or updated in `~/.claude/commands/` or `~/.claude/agents/`, this workflow syncs it to the `claude-code-team-toolkit` repo with proper documentation updates.

## Input

Skill: $ARGUMENTS

## Pre-flight

1. Verify the toolkit repo exists at `~/Dev/claude-code-team-toolkit`
2. Verify the skill file exists in `~/.claude/commands/{name}.md` or `~/.claude/agents/{name}.md`
3. Check current git state of the toolkit repo (branch, clean?)

## Phase 1: Create a Branch

```bash
cd ~/Dev/claude-code-team-toolkit
git checkout main && git pull your-org main
git checkout -b docs/add-{skill-name}-skill
```

**Never work directly on main.**

## Phase 2: Copy the Skill File

Copy the source file into the toolkit:

- Commands → `commands/{name}.md`
- Agents → `agents/{name}.md`

Verify the file has proper YAML frontmatter:
```yaml
---
description: One-line description
argument-hint: What user provides (commands only)
---
```

If frontmatter is missing or malformed, fix it before copying.

## Phase 3: Update Documentation (4 files)

Update these files to include the new skill. Match existing style exactly.

### 3a. `README.md` — Quick reference table

Find the commands or agents table and add a row. Commands are grouped by purpose:
- **Orient**: status, explain, recall, guide
- **Build**: tdd, diagnose, verify, commit-push-pr
- **Analyze**: audit, gap-analysis, scan, research
- **Sustain**: document, new-project, learn, sync-memories
- **Meta**: orchestrate, metaprompt
- **Collaborate**: flag, sync-skill-docs (new category if needed)

Determine which category fits. Add the row in alphabetical order within the category.

Format: `| /command | One-line description |`

Update the total count in the header (e.g., "18 slash commands" → "19 slash commands").

### 3b. `docs/COMMANDS.md` or `docs/AGENTS.md` — Detailed reference

Add a section for the new skill matching the existing format:

```markdown
### `/command-name`
> One-line description

**When to use**: [2-3 scenarios]
**Example**: `/command-name some input`
**Output**: [What the user gets back — format description]
```

Place it in the correct category section, alphabetically.

### 3c. `TOOLKIT.md` — Commands at a glance table

Find the "Commands at a Glance" table (around line 29-50) and add the new entry.

### 3d. `PLAYBOOK.md` — Add usage recipe (if the skill has a non-obvious workflow)

Only if the skill involves multi-step usage or combines with other skills. Add a recipe in the appropriate section.

## Phase 4: Verify

- Run any existing tests: `cd ~/Dev/claude-code-team-toolkit && source .venv/bin/activate && python -m pytest tests/ -q`
- Verify markdown formatting: no broken tables, no orphan links
- Count total commands and agents — ensure README numbers match actual file counts

## Phase 5: Commit (DO NOT PUSH)

```bash
git add commands/{name}.md  # or agents/{name}.md
git add README.md docs/COMMANDS.md TOOLKIT.md  # and any other changed docs
git commit -m "docs: add /{name} skill with documentation"
```

**STOP HERE.** Present a summary of all changes and wait for user approval before pushing.

## Output

```
Skill sync complete (not pushed):
  Branch: docs/add-{name}-skill
  Files changed: [list]
  Docs updated: README.md, docs/COMMANDS.md, TOOLKIT.md [, PLAYBOOK.md]
  Command count: X → Y

  Ready to push? Specify remote: your-org (org) or origin (personal)
```

## Rules

- **Never push without explicit approval** — always stop and show the diff first
- **Never work on main** — always create a feature branch
- **Match existing doc style exactly** — read surrounding entries before writing
- **Ask which remote** before pushing — user has dual accounts (your-work-account / couldbeme)
- If `$ARGUMENTS` is "all", diff `~/.claude/commands/` against `commands/` in the toolkit and sync any missing or newer files
- Update counts everywhere they appear (README header, TOOLKIT intro, etc.)
