# Claude Code Team Toolkit

15 slash commands + 7 specialized agents for [Claude Code](https://docs.anthropic.com/en/docs/claude-code) that enforce consistent, high-quality development workflows.

## Quick Start

```bash
# 1. Clone
git clone <repo-url> claude-code-team-toolkit
cd claude-code-team-toolkit

# 2. Install commands + agents (global)
cp -r commands/ ~/.claude/commands/
cp -r agents/ ~/.claude/agents/

# 3. Optional: install global rules
cp CLAUDE.md.template ~/.claude/CLAUDE.md

# 4. Open Claude Code in any project and try:
#    /status
#    /explain src/
#    /tdd Add input validation
```

For project-scoped install, copy into `your-project/.claude/` instead.

## What's Included

### Commands (15)

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
| `/audit` | Full 5-dimension codebase audit with scorecard |
| `/gap-analysis` | Find missing tests, docs, error handling, types |
| `/research` | Deep 3-track technical research with sources |
| `/orchestrate` | Multi-agent task decomposition and execution |
| `/metaprompt` | Generate optimized slash commands from a task description |
| `/sync-memories` | Export/import knowledge between machines |

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

### Memory System (optional)

Persistent knowledge base that lets Claude Code remember across sessions. Uses local embeddings (LM Studio + nomic-embed-text) and hybrid search (70% semantic + 30% keyword).

- **Works without LM Studio** -- falls back to keyword-only search
- **See [SETUP-MEMORY.md](SETUP-MEMORY.md)** for full installation guide

### Other Files

| File | Purpose |
|------|---------|
| `TOOLKIT.md` | Full guide with examples -- **read this for the presentation** |
| `CLAUDE.md.template` | Global rules template (TDD, security, communication style) |
| `SETUP-MEMORY.md` | Step-by-step memory system installation guide |
| `memory-mcp/` | MCP server source code + requirements.txt + settings template |

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
