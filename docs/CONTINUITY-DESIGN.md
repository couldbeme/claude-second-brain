# Continuity Design: Conversation-Threading Preservation

**Version:** v0.1 draft
**Scope:** Pre-compact dump + `/resume` skill + session-bridge journal
**Status:** L1: shipped (commit `74ef573`) | L1.5: shipped (commit `c7f4697`) | Design phase closed

---

## 1. Problem Statement

`/compact` discards the reasoning substrate of a session. What survives: files on disk, committed code, the `checkpoint.md` narrative, auto-memory entries. What disappears: why a rejected alternative was tried and abandoned, what energy level the conversation was at, which thread is half-open and tacitly understood, what persona observations just crossed the 3-occurrence threshold and have not yet been written to `user_profile.md`, and what the current agent is mid-way through building when compaction fires at 80%.

The existing tools preserve artifacts. An artifact is a static fact: "we decided X." Context threading is the living fabric: "we decided X because Y was on the table, Z ruled it out, and the user's frustration signal at 14:30 moved the priority order." That chain cannot be reconstructed from the artifact alone. Without it, a post-compact session re-litigates settled debates, re-introduces dismissed alternatives, and loses relational calibration. This design closes that gap with three components that write before compaction fires and are read on resume.

---

## 2. Existing Primitives Map

| Primitive | Location | What it preserves | What it does not |
|---|---|---|---|
| `checkpoint.md` | `~/.claude/checkpoint.md` | Manual narrative: tasks, decisions, gotchas, next step | Voice tone, rejected alternatives, open micro-threads, persona deltas this session |
| Auto-memory markdown | `~/.claude/projects/<slug>/memory/*.md` | Learnings, feedback rules, project state (durable) | In-session signal accumulation before the 3-occurrence threshold; compaction-bridge content |
| `memory.db` | `~/.claude/projects/<slug>/memory/memory.db` | Structured memories: categories, importance, tags, FTS, vectors | Session-level context; thread state; nothing is written mid-session by default |
| `context_pre_compact_<id>.md` | same memory dir | Token-metric snapshot: usage %, model, plan file refs | All content: no decisions, no voice, no threading |
| Plans (`~/.claude/plans/*.md`) | `~/.claude/plans/` | Spec-level design docs, agent dispatch plans | Execution state, in-flight deltas, session-specific reasoning |
| `precompact_hook.py` | `memory-mcp/precompact_hook.py` | Hook plumbing: runs at compaction, atomic write, exit-0 guarantee | Rich content — current snapshot is a placeholder stub |
| `session-recap` skill | `~/.claude/commands/session-recap.md` | Manual EOD recap when user invokes it | Not automatic; fires after the fact, not at compaction |

---

## 3. Three-Component Architecture

### Component 1: Pre-Compact Content Dump

**Purpose:** Extend the existing `precompact_hook.py` to write a content-rich continuity snapshot alongside the token-metric snapshot. No new hook registration needed — same PreCompact event, same exit-0 contract.

**Data shape** (`continuity_pre_compact_<session_id>.md`):

```markdown
---
type: continuity-pre-compact
session_id: <id>
timestamp: <ISO-8601-UTC>
cwd: <working-dir>
---

## Decisions (this session)
<!-- Max 10 entries. Source: session_bridge.md decision entries. -->
- [YYYY-MM-DDTHH:MMZ] <decision-text> | WHY: <rationale> | REJECTED: <alternative>

## Open Threads
<!-- Source: session_bridge.md thread entries with status=open. -->
- [open] <thread-text> | since: <timestamp>

## In-Flight State
<!-- Source: session_bridge.md inflight entry (latest only). -->
- task: <current-task-text>
- sub-step: <current-sub-step>
- next-action: <immediate-next>

## Voice Signals (metadata-only)
<!-- Source: session_bridge.md voice entries. NO message body content. -->
- energy: <low|medium|high> | signal-type: <reply-length-drop|caps|build-on>
- shared-refs: [<ref-label>, ...]
- session-arc: <rising|plateau|winding-down>

## Persona Deltas (this session)
<!-- Observations approaching or crossing 3-occurrence threshold. -->
- [count=N] <observation-category>: <observation-text>

## Cross-References
- checkpoint: ~/.claude/checkpoint.md
- recent-commits: <git log --oneline -5 both repos, captured at dump time>
- active-plans: [<path>, ...]
- bridge-journal: <path-to-session_bridge.md>
```

**Source:** `session_bridge.md` is the live write target during the session. The pre-compact dump reads it and formats the output. The hook does not parse message bodies at any point.

**Integration point:** `precompact_hook.py::run()` calls `continuity_dump.write_continuity_snapshot(event, memory_dir)` after the existing `_build_snapshot()` call. If `continuity_dump` fails, swallow exception — compaction cannot be blocked.

---

### Component 2: `/resume` Skill

**Purpose:** Invoked at session start (manually or auto per CLAUDE.md rule 10) after compaction or restart. Produces a tight 1-page re-orientation from the most recent continuity artifacts.

**Read-list** (in order, parallel where independent):

1. Most recent `continuity_pre_compact_<session_id>.md` in the memory dir (sorted by mtime)
2. `~/.claude/checkpoint.md` (if modified within 7 days)
3. `~/.claude/projects/<slug>/memory/session_bridge.md` (last 20 lines)
4. `git -C ~/Dev/claude-second-brain log --oneline -5` and `git -C ~/.claude log --oneline -5`
5. Most recent 3 plan files from `~/.claude/plans/` (sorted by mtime)

**Output format** (fixed schema, ≤600 words):

```
## Re-orientation — <timestamp>

### State on entry
- Working on: <in-flight task from dump>
- Sub-step: <current sub-step>
- Next action: <immediate-next>

### Decisions to honor (do not re-litigate)
- <decision> — WHY: <rationale> — REJECTED: <alternative>
[3-5 max]

### Open threads
- [open] <thread>
[max 5]

### Voice calibration
- Energy: <low|medium|high>
- Shared refs active: [<labels>]

### Gotchas (do not re-discover)
- <from checkpoint.md gotchas section>

### Recent commits (both repos)
<git log one-liners>

**Resume from:** <exact next action — specific enough to act without re-reading context>
```

**Skill file location:** `/Users/macbook/Dev/claude-second-brain/skills/resume/SKILL.md`
**Command file:** `~/.claude/commands/resume.md` (mirrors pattern of `session-recap.md`)

---

### Component 3: Session-Bridge Auto-Memory Journal

**Purpose:** Capture threading-critical signals as they happen during a session, not just at compaction. The PreCompact dump reads this file; it is the live write target.

**Location:** `~/.claude/projects/<slug>/memory/session_bridge.md`

**Append-only format** (each entry is one line):

```
[YYYY-MM-DDTHH:MM:SSZ] [DECISION] <text> | WHY: <rationale> | REJECTED: <alt>
[YYYY-MM-DDTHH:MM:SSZ] [THREAD-OPEN] <thread-id-hex> | <description>
[YYYY-MM-DDTHH:MM:SSZ] [THREAD-CLOSE] <thread-id-hex>
[YYYY-MM-DDTHH:MM:SSZ] [INFLIGHT] task=<text> | step=<text> | next=<text>
[YYYY-MM-DDTHH:MM:SSZ] [VOICE] energy=<low|medium|high> | signal=<type> | ref=<label>
[YYYY-MM-DDTHH:MM:SSZ] [PERSONA] count=<N> | category=<cat> | obs=<text>
```

Write triggers (all metadata/structural — no message body content):
- `[DECISION]`: when a CLAUDE.md rule or standing pattern is invoked (auto) or when user uses absolute language (per Mythos rule 11)
- `[THREAD-OPEN]` / `[THREAD-CLOSE]`: when an open question is posed / resolved
- `[INFLIGHT]`: on every agent dispatch and every major sub-step completion
- `[VOICE]`: when a frustration or satisfaction signal is detected (Layer 2 triggers from CLAUDE.md)
- `[PERSONA]`: when Layer 3 observation accumulates a new occurrence

**Rotation:** on session start, if `session_bridge.md` is older than 7 days, rename to `session_bridge_<date>.md` and start fresh. Keep last 2 rotations.

---

## 4. Schema Additions

### New DB table: `session_threads`

```sql
CREATE TABLE IF NOT EXISTS session_threads (
    id TEXT PRIMARY KEY,                        -- hex-8 token
    session_id TEXT NOT NULL,
    description TEXT NOT NULL,                  -- thread description, max 500 chars
    status TEXT NOT NULL DEFAULT 'open',        -- 'open' | 'closed' | 'deferred'
    opened_at TEXT DEFAULT (datetime('now')),
    closed_at TEXT,
    project TEXT,
    FOREIGN KEY (session_id) REFERENCES memories(session_id)
);

CREATE INDEX IF NOT EXISTS idx_threads_session ON session_threads(session_id);
CREATE INDEX IF NOT EXISTS idx_threads_status ON session_threads(status);
```

Example rows:

| id | session_id | description | status | opened_at |
|---|---|---|---|---|
| `a3f9c100` | `abc123` | `voice-signal extraction approach — metadata-only vs body-parse` | `closed` | `2026-04-28T14:30:00` |
| `b7d2e441` | `abc123` | `L2 review of SUBSTACK-FINAL.md` | `open` | `2026-04-28T17:45:00` |

### Markdown: `session_bridge.md`

No DB migration required — pure append-only flat file. Gitignored. Format defined in Component 3 above.

### Gitignore additions

```
# Continuity dumps — local-only, never push
**/memory/continuity_pre_compact_*.md
**/memory/session_bridge*.md
**/memory/session_bridge_*.md
```

---

## 5. Code Interfaces

### `memory-mcp/continuity_dump.py` (new file)

```python
"""Continuity snapshot writer — invoked by precompact_hook.py.

Reads session_bridge.md from memory_dir, formats a content-rich continuity
snapshot, and writes it atomically.

Privacy contract: NEVER reads transcript message bodies. All content sourced
from session_bridge.md entries (metadata/structural writes only) and filesystem
metadata (git log, plan file mtimes). No LLM in the loop.

Exit contract: all public functions swallow exceptions — callers must not be
blocked by failures here.
"""

from pathlib import Path


def write_continuity_snapshot(
    session_id: str,
    cwd: str,
    memory_dir: Path,
) -> bool:
    """Read session_bridge.md and write continuity_pre_compact_<session_id>.md.

    Returns True if written successfully, False if skipped or failed.
    Atomic write via .tmp sibling + os.replace(). Never raises.
    """
    ...


def _read_bridge_entries(bridge_path: Path) -> list[dict]:
    """Parse session_bridge.md into structured dicts.

    Returns list of {"timestamp", "type", "payload"} dicts.
    Returns [] on any parse or IO error. Never raises.
    """
    ...


def _capture_git_log(repo_paths: list[Path], n: int = 5) -> list[str]:
    """Run `git log --oneline -N` on each repo. Returns list of one-liner strings.

    Shells out via subprocess with timeout=5s. Returns [] on any failure.
    Privacy: captures commit message text (public metadata), not file diffs.
    """
    ...


def _format_snapshot(
    entries: list[dict],
    git_lines: list[str],
    session_id: str,
    cwd: str,
    timestamp: str,
) -> str:
    """Format the continuity snapshot markdown from structured inputs.

    Pure function — no IO. Takes pre-parsed entries and pre-fetched git lines.
    Returns the full markdown string.
    """
    ...


def append_bridge_entry(
    memory_dir: Path,
    entry_type: str,
    payload: str,
) -> bool:
    """Append a single line to session_bridge.md in memory_dir.

    entry_type: one of DECISION | THREAD-OPEN | THREAD-CLOSE | INFLIGHT | VOICE | PERSONA
    payload: the text after the type tag (must NOT contain raw message body content)

    Atomic: uses file locking (fcntl on POSIX). Returns True on success.
    Never raises — caller must not be blocked.
    """
    ...
```

### Extension to `precompact_hook.py`

```python
# In run(), after existing _build_snapshot() call succeeds:

def _write_continuity(
    session_id: str,
    cwd: str,
    memory_dir: Path,
) -> None:
    """Attempt continuity dump. Swallows all exceptions — never blocks compaction."""
    try:
        from continuity_dump import write_continuity_snapshot
        write_continuity_snapshot(session_id, cwd, memory_dir)
    except Exception:  # noqa: BLE001
        pass
```

The call is inserted at the end of `run()`, after the atomic write of the token-metric snapshot, before `return 0`.

### `/resume` skill (`skills/resume/SKILL.md` and `~/.claude/commands/resume.md`)

Read-list as enumerated in Component 2. The skill file defines the sequence, output format, and constraints. No Python backing logic needed — it is a markdown skill invoked by Claude directly. The skill reads files and formats output; no writes during `/resume`.

---

## 6. Hooks Integration

| Hook event | What fires | New behavior |
|---|---|---|
| `PreCompact` | `precompact_hook.py::run()` | After existing token-metric write, calls `_write_continuity()`. Swallows all failures. Exit 0 always. |
| `SessionStart` | (not yet wired) | CLAUDE.md rule 10 covers this manually: if `checkpoint.md` is <7 days old, read it. `/resume` is the skill path when auto-resuming. Future: wire a SessionStart hook to auto-invoke `/resume` logic. |
| `Stop` | (existing — safety net for self-learning) | No change. The Stop hook is a safety net for missed `[LEARNING]` tags; continuity writes happen at `PreCompact`, not Stop. |

**Sequence on compaction:**

1. Claude Code detects context at threshold → fires `PreCompact` event
2. `precompact_hook.py::run()` reads hook payload from stdin
3. Token-metric snapshot written to `context_pre_compact_<id>.md` (existing behavior)
4. `_write_continuity()` called → reads `session_bridge.md` → writes `continuity_pre_compact_<id>.md` (new)
5. Hook exits 0 — compaction proceeds
6. After compaction, user or session-start invokes `/resume`
7. `/resume` reads continuity dump + checkpoint + git log → outputs 1-page re-orientation

**Session-bridge writes** happen inline during the session as `append_bridge_entry()` calls, not at compaction time. The PreCompact hook simply reads what has already been written.

---

## 7. Privacy and Boundary Discipline

**Hard rules:**

- `continuity_dump.py` reads `session_bridge.md` ONLY. It never reads transcript JSONL files, chat history, or any file containing message bodies.
- `session_bridge.md` entries are written by code, not by content extraction. Entry text is structural metadata: decision labels, thread IDs, task names, energy-level enum values, persona-observation categories. No verbatim user text, no verbatim assistant response text.
- `context_estimator.py` is the precedent: it reads `usage.input_tokens` only, never message content. The continuity system follows the same discipline.
- Continuity dump files (`continuity_pre_compact_*.md`, `session_bridge*.md`) are gitignored at the repo level. They live in `~/.claude/projects/<slug>/memory/` which is already outside the public toolkit repo.
- `_capture_git_log()` reads commit messages (public metadata — already in version control). It does not read diffs or file content.
- `session_threads` DB table stores thread descriptions written programmatically. If a thread description is derived from a user phrase, it must be a structural label ("open question: approach X vs Y"), not a verbatim quote.

**What VOICE signals capture (metadata only):**

- `energy`: inferred from turn-count rate and reply-length delta (token counts from `usage.output_tokens`), not from message text analysis
- `signal-type`: enum value from the Layer 2 trigger taxonomy in CLAUDE.md (e.g., `reply-length-drop`, `caps-detected`, `build-on`)
- `shared-refs`: labels assigned by the code author at write-time (e.g., "contradiction-table joke"), not extracted from message body

No NLP, no regex over message bodies, no LLM summarization of conversation content.

---

## 8. Falsifiable Test for v0.1

**Hypothesis:** After `/compact` + `/resume`, the new session's first 3 tool calls match what the same task would have produced without compaction in at least 7 of 10 runs.

**Experiment:**

1. Set up a scripted task sequence: 5 steps, each with a tool call as the primary action (e.g., Read a specific file, then Bash a specific git command, then Write to a specific path).
2. Run the sequence to step 3, then trigger compaction.
3. Invoke `/resume` in the new context.
4. Record which tool calls the resumed session makes as its first 3 actions.
5. Repeat steps 1-4 without compaction (control run) and record the same 3 tool calls.
6. Compare: a match is "same tool, same target path or command, within the same step". Score 1 if all 3 match, 0 if any diverge.
7. Repeat 10 times across 3 different task types (file-editing task, research task, build task).

**Pass criterion:** score sum >= 7/10.

**What this falsifies:** if the resumed session opens files the task would not have opened, or runs git commands irrelevant to the in-flight state, the continuity dump did not survive compaction with sufficient fidelity. The test is behavioral, not schema-level.

**Test scaffold:** `memory-mcp/tests/test_continuity_dump.py` covers unit-level: parse `session_bridge.md` → format snapshot → fields present and non-empty. The falsifiable hypothesis above is the integration-level proof; it runs manually against a live session.

---

## 9. Out of Scope

The following are explicitly excluded from this design:

- **LLM-in-loop summarization.** No LLM call to summarize session content at compaction time. Compaction is already a summary; layering another is circular and introduces latency + privacy surface.
- **Automated voice-cloning or joke detection.** Voice signals are captured as enum metadata written by code, not by semantic analysis of message text. Joke callbacks are a labeled ref, not a detected pattern.
- **Cross-session threading.** `session_bridge.md` resets per session. Durable cross-session state belongs in `user_profile.md` and `memory.db`, which already have mechanisms for that.
- **Real-time streaming to DB.** `session_bridge.md` is a flat append file. No live DB writes during the session to avoid lock contention with the MCP server.
- **Automatic SessionStart hook.** Rule 10 covers session-start orientation manually. Wiring a hook requires Claude Code hook configuration changes outside this scope.
- **Transcript archiving or export.** The system explicitly never reads or writes full transcript content. Transcript archival is a separate concern with a distinct privacy review requirement.
- **`session_threads` DB queries in the PreCompact hook.** The hook reads only `session_bridge.md`. DB writes for threads are optional Layer 1 additions; the flat file is sufficient for v0.1.

---

**Key files referenced:**

- `/Users/macbook/Dev/claude-second-brain/memory-mcp/precompact_hook.py` — extension target
- `/Users/macbook/Dev/claude-second-brain/memory-mcp/db.py` — schema reference for `session_threads` table addition
- `/Users/macbook/Dev/claude-second-brain/memory-mcp/context_estimator.py` — privacy precedent (reads `usage.input_tokens` only — same discipline required here)
- `/Users/macbook/Dev/claude-second-brain/memory-mcp/feedback_violations.py` — pattern for a new module that integrates with precompact_hook without rewriting it
- `/Users/macbook/.claude/checkpoint.md` — the manual narrative this system augments (not replaces)
- `/Users/macbook/.claude/commands/session-recap.md` — skill format precedent for `/resume` output structure
- `/Users/macbook/.claude/commands/context-save.md` — the fallback path this system systematizes
- `/Users/macbook/.claude/plans/oss-launch-phase-continuity.md` — the governing spec
