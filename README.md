# Claude Second Brain

29 slash commands + 17 specialized agents for [Claude Code](https://docs.anthropic.com/en/docs/claude-code) that enforce consistent, high-quality development workflows — plus a memory system that lets Claude actually remember across sessions and a *Mythos pattern* for partnerships where the artifacts become the substrate.

**New here?** Jump to [QUICK-START.md](QUICK-START.md) for install + a hands-on walkthrough. Or peek at [docs/METAPROMPT-EXAMPLES.md](docs/METAPROMPT-EXAMPLES.md) to see how `/metaprompt` upskills a fuzzy 15-word ask into a 400-word structured execution plan — the toolkit's most novel capability and the fastest "wait, what" moment.

## Quick Start

```bash
# 1. Clone
git clone <repo-url> claude-second-brain
cd claude-second-brain

# 2. Install (symlinks + memory-mcp venv + git hook)
./install.sh

# 3. Set up the memory system (see SETUP-MEMORY.md)

# 4. Open Claude Code in any project and try:
#    /guide tour                  # new? start here
#    /status
#    /explain src/
#    /tdd Add input validation
```

Updates auto-sync on `git pull` via post-merge hook. Personal agents go in `~/.claude/agents/` as regular files — never touched by updates. See [QUICK-START.md](QUICK-START.md) for full details.

## Documentation

| Doc | What it covers |
|-----|----------------|
| **[QUICK-START.md](QUICK-START.md)** | Install guide + "Your First 5 Minutes" walkthrough + hands-on sandbox |
| **[TOOLKIT.md](TOOLKIT.md)** | Why the toolkit matters — 9 Before & After scenarios |
| **[PLAYBOOK.md](PLAYBOOK.md)** | Daily workflow recipes, prompt patterns, agent composition, AI/LLM security |
| **[docs/TOP-COMMANDS.md](docs/TOP-COMMANDS.md)** | Top 10 commands cheat sheet with examples + decision tree |
| **[docs/COMMANDS.md](docs/COMMANDS.md)** | Full reference for all 29 commands |
| **[docs/AGENTS.md](docs/AGENTS.md)** | Full reference for all 17 agents |
| **[docs/SELF-LEARNING.md](docs/SELF-LEARNING.md)** | CLAUDE.md workflow + 5-layer learning system |
| **[docs/ADVANCED-PATTERNS.md](docs/ADVANCED-PATTERNS.md)** | Skills crystallization, context recovery, post-audit remediation |
| **[docs/PURPOSE.md](docs/PURPOSE.md)** | Public/private boundary — what each subtree IS and IS NOT for |
| **[docs/mythos/PATTERN.md](docs/mythos/PATTERN.md)** | The Mythos pattern — when artifacts become substrate (advanced/optional) |
| **[docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)** | Common issues + Security & Portability env-var reference |
| **[SETUP-MEMORY.md](SETUP-MEMORY.md)** | Memory system installation — LM Studio, MCP server, hybrid search |
| **[CLAUDE.md.template](CLAUDE.md.template)** | Global rules template — TDD, security, self-learning protocol |
| **[docs/FIRST-10-MINUTES.md](docs/FIRST-10-MINUTES.md)** | Onboarding extension — carries QUICK-START's 5-min tour to 10 min |
| **[docs/CONTINUITY-RESUME-DEMO.md](docs/CONTINUITY-RESUME-DEMO.md)** | Hands-on continuity demo — bridge journal, PreCompact snapshot, `/resume` |
| **[docs/OSS-ADOPTION-CHECKLIST.md](docs/OSS-ADOPTION-CHECKLIST.md)** | 7-question fit-check — should you use this toolkit? |

Start with **QUICK-START.md** to get set up. Read **TOOLKIT.md** to see why it matters. Use **PLAYBOOK.md** as a daily reference.

## What's Included

### Commands (29)

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
| `/metaprompt` | Upskill a fuzzy task description into a phased, quality-gated, executable prompt |
| `/sync-memories` | Export/import knowledge between machines |
| `/guide` | Interactive toolkit assistant -- suggests commands and workflows for your task |
| `/diagnose` | Interpret error screenshots, logs, or stack traces and diagnose + fix |
| `/scan` | Full repository health scan -- security, quality, gaps, and operational health in one report |
| `/flag` | Flag findings for team review instead of fixing them unilaterally |
| `/resolve-pr` | Fetch PR review comments, fix code, reply politely, push |
| `/sync-skill-docs` | Sync new skills to the team toolkit repo with documentation updates |
| `/team` | Dynamic agent team assembly -- analyzes project, selects optimal agents, executes in layers |
| `/harden-memory` | Audit and harden the memory auto-sync pipeline end-to-end |
| `/economy` | Optimize token consumption while maintaining result quality |
| `/context-save` | Checkpoint task state to survive context compaction |
| `/mythos-codify` | Codify the Mythos approach as a non-negotiable CLAUDE.md rule + ship a public/private boundary doc |
| `/design-mythos-substrate` | Honest, first-person design pass on extending memory primitives with purpose / cognition / affective layers (research-grade) |

### Agents (17)

**Role-Based Agents (7):**

| Agent | Role |
|-------|------|
| **architect** | Design implementation blueprints from codebase patterns |
| **tdd-agent** | Strict TDD implementation (never codes before tests) |
| **security-auditor** | Vulnerability scanning with severity ratings |
| **code-reviewer** | Confidence-scored bug and issue detection |
| **documentation-agent** | Accurate, concise doc generation |
| **research-agent** | Multi-source technical investigation |
| **verification-agent** | Sequential test/lint/build pipeline |

**Domain Expert Agents (10):**

| Agent | Seniority | Domain |
|-------|-----------|--------|
| **senior-frontend-dev** | 15+ years | React/Vue/Angular, accessibility, Core Web Vitals |
| **senior-backend-dev** | 15+ years | API design, databases, caching, auth |
| **senior-fullstack-dev** | 15+ years | End-to-end features, vertical slices |
| **senior-data-scientist** | 12+ years | ML, statistics, experiment design |
| **ml-engineer** | 12+ years | MLOps, model serving, pipelines |
| **devops-engineer** | 12+ years | CI/CD, Docker, K8s, Terraform |
| **database-engineer** | 15+ years | Schema, query optimization, migrations |
| **performance-engineer** | 12+ years | Profiling, load testing, benchmarking |
| **sre-agent** | 12+ years | Incident response, SLO management |
| **qa-strategist** | 12+ years | Test strategy, contract testing |

### Memory System

Persistent knowledge base that lets Claude Code remember across sessions. Uses local embeddings (LM Studio + nomic-embed-text) and hybrid search (70% semantic + 30% keyword).

- **LM Studio is optional** -- without it, search falls back to keyword-only (the memory system itself is required)
- **See [SETUP-MEMORY.md](SETUP-MEMORY.md)** for installation guide
- **`memory-mcp/continuity_dump.py`** — writes a content-rich pre-compact snapshot (`continuity_pre_compact_<id>.md`) capturing decisions, open threads, in-flight state, and voice signals from the current session; invoked automatically by the PreCompact hook alongside the token-metric snapshot. Privacy: reads only `session_bridge.md` — never touches transcript bodies.
- **`memory-mcp/bridge_append.py`** — CLI that Claude invokes during a session to append structural entries (`DECISION`, `INFLIGHT`, `THREAD-OPEN`, `THREAD-CLOSE`) to `session_bridge.md`. The PreCompact hook then dumps these entries into the continuity snapshot. Trigger taxonomy in `CLAUDE.md.template` rule 8; setup in [SETUP-MEMORY.md](SETUP-MEMORY.md) Step 6.
- **`session_threads` DB table** — optional SQLite table in `memory.db` for durable cross-session thread tracking (open/closed/deferred); schema defined in `memory-mcp/db.py`.

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
