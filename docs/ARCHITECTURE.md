# Architecture Overview

## System Diagram

```
┌─────────────────────────────────────────────────────┐
│                  Claude Code Session                 │
│                                                     │
│  User types /command ──► Slash Command (.md file)    │
│                              │                      │
│                              ▼                      │
│                     Agent Dispatch                   │
│                    (if multi-agent)                  │
│                     ┌────┼────┐                     │
│                     ▼    ▼    ▼                      │
│                  Agent  Agent  Agent                  │
│                  (.md)  (.md)  (.md)                  │
│                     │    │    │                      │
│                     └────┼────┘                      │
│                          ▼                          │
│                    MCP Tools ◄──── memory_save       │
│                    (server.py)     memory_search     │
│                          │        memory_context     │
│                          ▼        ...                │
│                    SQLite DB                         │
│                  + sqlite-vec                        │
│                  + FTS5                              │
└──────────────────────┬──────────────────────────────┘
                       │
              ┌────────┼────────┐
              ▼                 ▼
        LM Studio          Git Backup
     (embeddings)        (launchd hourly)
     localhost:1234            │
                               ▼
                        GitHub Remote
                       (cross-machine sync)
```

## Information Flow

1. **Session start**: Claude Code reads `~/.claude/CLAUDE.md` (global rules) and project `.claude/CLAUDE.md`
2. **User invokes command**: `/tdd`, `/audit`, etc. — resolved to `.md` file in `~/.claude/commands/`
3. **Command dispatches agents**: Complex commands spawn specialized agents (architect, tdd-agent, etc.)
4. **Agents use MCP tools**: `memory_save`, `memory_search`, `memory_context` for persistent knowledge
5. **Embeddings**: Content is vectorized via LM Studio (768-dim nomic-embed-text-v1.5)
6. **Search**: Hybrid ranking — 70% vector similarity + 30% BM25 keyword relevance
7. **Backup**: Launchd agent runs hourly — commits memory.db to git, pushes, re-embeds missing vectors
8. **Cross-machine sync**: Export → git push → git pull → import on second machine

## Repository Relationship

```
claude-code-team-toolkit/          (source of truth for code)
├── commands/*.md                  ──symlink──►  ~/.claude/commands/*.md
├── agents/*.md                    ──symlink──►  ~/.claude/agents/*.md
├── memory-mcp/*.py                ──symlink──►  ~/.claude/memory-mcp/*.py
└── install.sh                     (creates symlinks)

~/.claude/  (second-brain repo)    (source of truth for data)
├── memory/memory.db               (SQLite database — git-tracked for backup)
├── projects/*/memory/*.md         (per-project knowledge — git-tracked)
├── CLAUDE.md                      (global rules — git-tracked)
└── settings.json                  (MCP config — git-tracked)
```

**Key principle**: Code lives in the toolkit repo. Data lives in the second-brain repo. Symlinks connect them. Updates to toolkit auto-propagate via `git pull` + post-merge hook.

## Component Details

### Slash Commands (25)
Markdown files with YAML frontmatter. Claude Code resolves `/name` to the file and follows the instructions inside. Commands can dispatch agents, use MCP tools, and produce structured output.

### Agents (17)
Specialized subprocesses with bounded scope. 7 role-based (architect, TDD, security, etc.) + 10 domain experts (frontend, backend, ML, etc.). Dispatched by `/orchestrate`, `/team`, and `/audit`.

### Memory MCP Server
Python FastMCP server running via stdio transport. 7 tools for CRUD + search. SQLite with sqlite-vec for vector search and FTS5 for keyword search. Falls back to keyword-only if LM Studio is down.

### Launchd Agent
`com.claude.sync-memories` — runs `scheduled-sync.sh` every hour:
1. Backup: `sync.py backup --push` (git commit + push memory.db)
2. Reembed: `sync.py reembed` (fill embedding gaps, only if LM Studio running)
Logs to `~/.claude/logs/sync.log` and `sync-error.log`.
