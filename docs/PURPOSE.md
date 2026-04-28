# Purpose

Each subtree of this repo has a single purpose. Use this to decide where a file belongs and whether it belongs at all.

| Path | IS | IS NOT | Lives |
|---|---|---|---|
| `commands/` | Slash-command definitions for end users | Author's own one-off utilities | Public |
| `agents/` | Reusable specialist agent definitions | Conversation transcripts or notes | Public |
| `skills/` | Workflow skills with `SKILL.md` frontmatter | Drafts of skills or research about skills | Public |
| `memory-mcp/` | The memory MCP server + its tests | Author's personal memory database | Public |
| `docs/` | User-facing reference docs (commands, agents, architecture, troubleshooting, migration, advanced patterns) | Internal research, drafts, plans, audit reports, status updates, recovery briefs | Public |
| `tests/` | Tests for the toolkit's code | Tests for the author's personal projects | Public |
| `examples/` | Worked example invocations and template configs | Real session transcripts | Public |
| `install.sh`, `setup-new-machine.sh`, `uninstall.sh` | End-user setup scripts using `<placeholder>` parameters | Hardcoded author paths or handles | Public |
| `CLAUDE.md.template` | Template file for downstream users to copy | The author's own runtime `CLAUDE.md` | Public (template) |
| Author's `~/.claude/` | Working memory, plans, audits, drafts, lexicon, persona model, feedback memories | Anything intended for outside readers | **Private — never pushed** |

## The rule

**Public toolkit = template for outsiders. Internal state lives at the author's `~/.claude/` only.**

When unsure where a new file belongs, ask: *would a stranger cloning this repo expect to see this?*
- If yes → public toolkit (this repo).
- If "only the author would know what to do with this" → private (`~/.claude/`).

## Categories that auto-flag as private

If a new file fits any of these descriptions, default to private layer:

- **Audit reports** — describes what was scrubbed, fixed, or refactored at the meta level
- **Recovery briefs** — explains how artifacts got recovered or migrated from prior systems
- **Status reports** — phase trackers with commit hashes, internal milestone names
- **Drafts** — article drafts, announcement drafts, design proposals not yet decided
- **Plans / roadmaps** — phased build plans with internal terminology
- **Persona models** — communication-style observations about specific people
- **Lexicons** — co-curated vocabulary specific to a partnership
- **Recovery utilities** — one-time import scripts for migrating prior data
- **Dev backlogs** — items deferred from launch with internal reasoning

## Categories that stay public

If a new file fits one of these, it ships:

- **User-facing reference** — how to use a command, agent, skill
- **Architecture** — how the system fits together, post-decision
- **Tests** — for the public toolkit's code
- **Examples** — runnable demonstrations of public features
- **Migration guides** — for users moving between toolkit versions
- **Troubleshooting** — common errors and fixes for users

## Keeping it true

The public/private split is enforced by `.gitignore` patterns at the toolkit root. New private categories should add their `.gitignore` patterns at the time the file is first created — not retrofit after a leak audit.
