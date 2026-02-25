# Claude Code Team Toolkit

21 slash commands + 7 specialized agents for [Claude Code](https://docs.anthropic.com/en/docs/claude-code) that enforce consistent, high-quality development workflows.

**New here?** Jump to [QUICK-START.md](QUICK-START.md) for install + a hands-on walkthrough.

## Quick Start

```bash
# 1. Clone
git clone <repo-url> claude-code-team-toolkit
cd claude-code-team-toolkit

# 2. Install commands + agents (global)
cp -r commands/ ~/.claude/commands/
cp -r agents/ ~/.claude/agents/

# 3. Install global rules
cp CLAUDE.md.template ~/.claude/CLAUDE.md

# 4. Set up the memory system (see SETUP-MEMORY.md)

# 5. Open Claude Code in any project and try:
#    /guide tour                  # new? start here
#    /status
#    /explain src/
#    /tdd Add input validation
```

For project-scoped install, copy into `your-project/.claude/` instead.

## Documentation

| Doc | What it covers |
|-----|----------------|
| **[QUICK-START.md](QUICK-START.md)** | Install guide + "Your First 5 Minutes" walkthrough + hands-on sandbox |
| **[TOOLKIT.md](TOOLKIT.md)** | Why the toolkit matters — 9 Before & After scenarios |
| **[PLAYBOOK.md](PLAYBOOK.md)** | Daily workflow recipes, prompt patterns, agent composition, AI/LLM security |
| **[docs/COMMANDS.md](docs/COMMANDS.md)** | Full reference for all 21 commands |
| **[docs/AGENTS.md](docs/AGENTS.md)** | Full reference for all 7 agents |
| **[docs/SELF-LEARNING.md](docs/SELF-LEARNING.md)** | CLAUDE.md workflow + 5-layer learning system |
| **[docs/ADVANCED-PATTERNS.md](docs/ADVANCED-PATTERNS.md)** | Skills crystallization, context recovery, post-audit remediation |
| **[SETUP-MEMORY.md](SETUP-MEMORY.md)** | Memory system installation — LM Studio, MCP server, hybrid search |
| **[CLAUDE.md.template](CLAUDE.md.template)** | Global rules template — TDD, security, self-learning protocol |
| **[docs/ROLLOUT-GUIDE.md](docs/ROLLOUT-GUIDE.md)** | Operational guide — when to scan, how to interpret, team cadence |
| **[docs/ANNOUNCEMENT.md](docs/ANNOUNCEMENT.md)** | Internal rollout announcement template |

Start with **QUICK-START.md** to get set up. Read **TOOLKIT.md** to see why it matters. Use **PLAYBOOK.md** as a daily reference.

## What's Included

### Commands (21)

| Command | Description |
|---------|-------------|
| `/status` | Instant progress report -- git state, tests, next steps |
| `/explain` | 3-level code explainer with ASCII data flow diagrams |
| `/tdd` | Strict red-green-refactor TDD cycle |
| `/verify` | 7-step health check with traffic-light report |
| `/commit-push-pr` | Quality-gated commit, push, and PR workflow |
| `/document` | Generate or update docs -- always shows diffs |
| `/new-project` | Scaffold a project with CLAUDE.md template |
| `/learn` | Capture learnings into CLAUDE.md |
| `/recall` | Search project knowledge (CLAUDE.md, docs, code) |
| `/audit` | Full 6-dimension codebase audit with scorecard |
| `/gap-analysis` | Find missing tests, docs, error handling, types |
| `/research` | Deep 3-track technical research with sources |
| `/orchestrate` | Multi-agent task decomposition and execution |
| `/metaprompt` | Generate optimized prompts from a task description |
| `/sync-memories` | Export/import knowledge between machines |
| `/guide` | Interactive toolkit assistant -- suggests commands and workflows for your task |
| `/diagnose` | Interpret error screenshots, logs, or stack traces and diagnose + fix |
| `/scan` | Full repository health scan -- security, quality, gaps, and operational health in one report |
| `/flag` | Flag findings for team review instead of fixing them unilaterally |
| `/resolve-pr` | Fetch PR review comments, fix code, reply politely, push |
| `/sync-skill-docs` | Sync new skills to the team toolkit repo with documentation updates |

### Agents (7)

| Agent | Role |
|-------|------|
| **architect** | Design implementation blueprints from codebase patterns |
| **tdd-agent** | Strict TDD implementation (never codes before tests) |
| **security-auditor** | Vulnerability scanning with severity ratings |
| **code-reviewer** | Confidence-scored bug and issue detection |
| **documentation-agent** | Accurate, concise doc generation |
| **research-agent** | Multi-source technical investigation |
| **verification-agent** | Sequential test/lint/build pipeline |

### Memory System

Persistent knowledge base that lets Claude Code remember across sessions. Uses local embeddings (LM Studio + nomic-embed-text) and hybrid search (70% semantic + 30% keyword).

- **LM Studio is optional** -- without it, search falls back to keyword-only (the memory system itself is required)
- **See [SETUP-MEMORY.md](SETUP-MEMORY.md)** for installation guide

## Your First 5 Minutes

```
/guide tour                          # see everything available
/status                              # where am I? what's in flight?
/tdd Add input validation to signup  # build something with TDD
/verify                              # full health check
/learn from session                  # save what you discovered
```

For a detailed walkthrough with expected outputs, see **[QUICK-START.md](QUICK-START.md)**. To practice on real (intentionally buggy) code, try the **[sandbox](examples/sandbox/)**.

## How It Works

**Slash commands** are markdown files with YAML frontmatter. Type `/command-name` in Claude Code and it follows the structured workflow inside.

```yaml
---
description: What shows in the autocomplete menu
argument-hint: Placeholder text for the argument
---

# Workflow instructions here...
```

**Agents** are dispatched automatically by commands like `/orchestrate` and `/audit`. They run as focused subprocesses with specific tools and return structured results.

**CLAUDE.md** is a project-level file that Claude Code reads at session start. It stores commands, architecture notes, domain rules, and gotchas -- persistent context across sessions.

## Contributing

Built a useful workflow? Add it:

1. Create a `.md` file in `commands/` or `agents/`
2. Include YAML frontmatter with `description:`
3. Write clear, phased instructions
4. Open a PR

## License

MIT
