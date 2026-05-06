---
description: Search project knowledge for relevant context
argument-hint: What to search for
---

# Recall — Search Project Knowledge

Search across all knowledge sources relevant to the user's working context. **Do not assume a single repo or directory** — discover the relevant sources at runtime and merge.

## Input

Query: $ARGUMENTS

## Source discovery (runtime — do NOT hard-code paths)

The user's "project knowledge" can span multiple locations. Before searching, enumerate what's present:

1. **Current project repo** — the git repo containing `cwd`. Walk up from `cwd` looking for `.git`. This is the primary source.

2. **Parent config / dotfiles repo** — many users keep their tool config in a separate git repo (commonly under their home directory). For Claude Code specifically, check the standard config dir (typically `~/.claude` on Linux/macOS, but discover via `$CLAUDE_CONFIG_DIR` env var if set). If that dir is a git repo, treat it as a second knowledge source. Other common patterns: `~/.dotfiles`, `~/.config/<tool>`.

3. **Sibling repos** — if `cwd` is inside a monorepo or workspace dir with sibling repos, each sibling is a candidate source.

4. **Memory directories** — Claude Code's auto-memory convention puts project-scoped memory at `<config-dir>/projects/<slugified-cwd>/memory/`. Cross-project user state often lives in a parent dir like `<config-dir>/projects/<parent-slug>/memory/`. Read **both** when present. The slug is derived from `cwd` — don't hard-code it.

5. **Bridge / continuity artifacts** — if the auto-memory dir contains `session_bridge.md`, `continuity_pre_compact_*.md`, or `context_pre_compact_*.md`, these are structural state from prior sessions. For "activity / state / what changed" queries, read them.

When multiple sources are present, **merge results** rather than picking one. Label each finding by its source so the user can trace it.

## Process

Branch the search by query intent:

### Branch A — Conceptual / "where is X documented?"

1. **CLAUDE.md files** — both project (`<repo-root>/CLAUDE.md` or `<repo-root>/.claude/CLAUDE.md`) and global (`<config-dir>/CLAUDE.md`). Both, when present.
2. **Project documentation** — `README.md`, `docs/`, `PLAYBOOK.md`, inline docstrings.
3. **Code** — Grep for the query topic across source + test files.
4. **Auto-memory files** — topic files matching the query in any discovered memory dir (`<config-dir>/projects/<slug>/memory/*.md`). Read `MEMORY.md` first as the index.

### Branch B — Activity / "what changed?" / "latest actions" / "recent work"

1. **Run `git log --since="<window>" --oneline`** on **every discovered repo** (project + parent config repo + siblings). Default window: 7 days. Merge timeline.
2. **`session_bridge.md`** (if present) — most recent INFLIGHT entry = current task; recent DECISION entries = what was decided this session-arc.
3. **`continuity_pre_compact_*.md`** (latest by mtime, if present) — what was in flight at last compact.
4. **`reminders.md` / TODO journals** — overdue and upcoming items.
5. **Cross-repo merge** — if the parent config repo has activity but the project repo doesn't (or vice versa), surface both. A common failure mode is scoping to one repo when the user's mental model spans both.

### Branch C — User profile / preferences / behavioral memories

1. Memory files matching `user_*.md`, `feedback_*.md`, `*_profile.md` in any discovered memory dir.
2. Cross-project memories often live in the **parent** memory dir; project-specific tweaks in the **project** memory dir. Read both.

## Synthesis

```
## Recall Results: [query]

### From [source 1 — e.g. project CLAUDE.md, ~/repo/CLAUDE.md]
[relevant excerpts with file:line]

### From [source 2 — e.g. config repo CLAUDE.md, <config-dir>/CLAUDE.md]
[relevant excerpts with file:line]

### From documentation
[file:line excerpts]

### From auto-memory
[memory file references with one-line summaries]

### From git activity (if Branch B)
| When | Repo | Commit | Subject |
|---|---|---|---|
| <date> | <repo-name> | <sha> | <subject> |

### From bridge / continuity (if present and relevant)
- [INFLIGHT / DECISION / etc. entries]

### Related files
- [file1] — [relevance]
- [file2] — [relevance]
```

## Failure mode

If results are scoped only to the current repo when the user's mental model spans multiple repos, the user will catch the gap and re-prompt — this wastes their attention. **Default to multi-source.** It's cheaper to surface a slightly broader scope than to under-scope and force a follow-up.

If nothing is found across all discovered sources: "No existing knowledge found for this topic across [list-of-searched-sources]. Try broadening the query or naming the specific area."
