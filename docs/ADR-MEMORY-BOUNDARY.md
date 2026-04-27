# ADR: Memory System Boundary — Code in Toolkit, Data in Second Brain

**Status:** Accepted
**Date:** 2026-03-03
**Deciders:** Toolkit maintainer

---

## Context

The toolkit includes a memory MCP server (`memory-mcp/`) that gives Claude Code persistent knowledge across sessions. Two distinct concerns emerged:

1. **The MCP server code** — Python implementation of `memory_save`, `memory_search`, embedding logic, and sync scripts. Generic infrastructure any developer can run.
2. **The memory data** — SQLite database (`memory.db`), 768-dimensional embedding vectors, per-project context files, and personal behavioral observations. Inherently individual.

### The two systems

**Second Brain** (`~/.claude/`, private repo)
- `~/.claude/memory/memory.db` — local SQLite database with embeddings
- `~/.claude/projects/*/memory/MEMORY.md` — per-project context files
- `~/.claude/CLAUDE.md` — personal global rules
- Syncs between developer's own machines via private git remote
- Launchd agent runs hourly backup

**Claude Second Brain** (public/org repo)
- 24 slash commands, 17 agents
- Memory MCP server implementation (`memory-mcp/`)
- Install scripts, documentation
- Symlinked into `~/.claude/` on install

### Why this boundary matters

Without a clear boundary, two failure modes emerge:

- **Data leakage:** Session context, proprietary code snippets, or personal behavioral observations accidentally committed to a public or org repo.
- **Data coupling:** A shared database creates a single point of failure, prevents per-developer customization, and makes the toolkit impossible to use offline.

---

## Decision

**Strict separation: the toolkit shares code, the second brain holds data. No data flows from second brain to toolkit.**

- `memory-mcp/*.py` lives in the toolkit repo, symlinked into `~/.claude/memory-mcp/` on install.
- `memory.db` and all embedding vectors live exclusively in `~/.claude/memory/`, never committed to the toolkit repo.
- `projects/` is gitignored in the second brain — except `projects/*/memory/*.md` files (architecture knowledge, not session data).
- Each developer runs their own `memory.db` locally. There is no shared database.

### How teams share learnings

Filtered export → pull request review → import:

```
Developer A:
  python sync.py export --scope team    # strips personal memories
  Opens PR to shared learnings repo

Developer B:
  Reviews PR for sensitive content
  python sync.py import filtered-learnings.json
```

The `--scope team` export:
- Strips all memories with `visibility: personal`
- Strips `persona` and `user_model` categories entirely (always personal)
- Does NOT include embedding vectors — only text content and metadata
- Recipients regenerate embeddings locally on import

---

## Data Classification

Every memory has a `visibility` field. Defaults by category:

| Category | Default Visibility | Share via PR? | Notes |
|----------|-------------------|---------------|-------|
| `rule` | team | YES | Engineering standards |
| `pattern` | team | YES | Reusable implementation patterns |
| `decision` | team | YES | Architecture decisions |
| `learning` | team | YES | Process discoveries, gotchas |
| `solution` | team | YES | Solved problems with context |
| `error` | personal | PARTIAL | Sanitize before sharing — may contain proprietary paths |
| `context` | personal | MIXED | May contain proprietary code — review before sharing |
| `persona` | personal (forced) | NEVER | Communication style and working preferences |
| `user_model` | personal (forced) | NEVER | Behavioral profile from session observations |

### Embedding vectors are quasi-sensitive

768-dimensional vectors from `nomic-embed-text-v1.5` encode semantic meaning. Even without original text, vectors reveal topical relationships. Therefore:

- Vectors are never included in team-scoped exports
- Each developer regenerates vectors locally on import
- The `.db` file is never committed to any shared repository

---

## Consequences

### Enables

- **Zero-friction install:** `./install.sh` sets up a working memory system in minutes
- **Safe public repo:** Toolkit can be open-source without data exposure risk
- **Independent customization:** Each developer's database reflects their own projects and style
- **Human-reviewed sharing:** Learnings flow through PRs, keeping a human in the loop
- **Offline-first:** Local database works without network connectivity

### Constrains

- **No automatic team sync:** Developer must export, PR, and teammate must import. Intentional friction.
- **Cold start on new machines:** Must restore from second-brain backup or start empty
- **Embedding regeneration cost:** Import requires LM Studio for re-embedding. Without it, keyword-only search until available.

### Boundary enforcement layers

1. **`.gitignore` in second brain:** `projects/` contents excluded except `*/memory/*.md`
2. **`.gitignore` in toolkit:** `*.db`, `memory/`, `.env` excluded
3. **Forced visibility in MCP server:** `persona`/`user_model` reject any visibility except `personal`
4. **Export scope filter:** `--scope team` required for shareable exports; default includes everything
5. **Symlink architecture:** Toolkit code lives in toolkit repo; second-brain gitignore excludes symlinked files

---

## Related Docs

- [SETUP-MEMORY.md](../SETUP-MEMORY.md) — Installation, LM Studio setup, MCP config
- [SELF-LEARNING.md](SELF-LEARNING.md) — Five-layer learning system
- `memory-mcp/sync.py` — Export/import with `--scope team` flag
