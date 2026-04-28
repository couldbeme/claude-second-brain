# Continuity Schema — load-bearing distillation

**Version:** v0.1
**Status:** Ready for code-reviewer + security-auditor gate
**Companion docs:** CONTINUITY-DESIGN.md (architecture), CONTINUITY-RESEARCH.md (survey)

---

## Purpose

This document is the authoritative field-level spec for everything the continuity system persists. It exists because CONTINUITY-DESIGN.md §4 defines structure but does not make explicit which fields change a future session's first decision and which are overhead. The backend implementor uses this doc to know what to write; the code-reviewer uses it to gate what must not be added; the security-auditor uses it to verify no message-body content crosses the privacy boundary. Every kept field has a rationale tied to a concrete downstream decision. Every rejected field has a documented reason. If a new field cannot pass the decision criterion, it does not ship.

---

## The decision criterion

**A field is load-bearing if its absence would change the new session's first concrete action.**

"First concrete action" means the first tool call or directive that the resumed session issues before the user adds new context. If removing a field from the snapshot would cause the resumed session to (a) re-litigate a settled decision, (b) start a different subtask, (c) open a file it would otherwise have skipped, or (d) speak in a register mismatched to the established relationship — the field is load-bearing. Everything else is decorative and gets cut.

Corollary: metadata that is *derivable* at resume time (e.g., current git HEAD, current date) is decorative even if useful — the resume skill can compute it fresh.

---

## Schema — kept fields

### A. `session_bridge.md` entry types

The flat append-only file is the live write target. The PreCompact dump reads it. Each entry is one line.

**Format:** `[YYYY-MM-DDTHH:MM:SSZ] [TYPE] <payload>`

| Entry type | Payload fields | Source trigger | Load-bearing rationale | Example value |
|---|---|---|---|---|
| `DECISION` | `<label>` \| `WHY: <rationale-label>` \| `REJECTED: <alt-label>` | CLAUDE.md rule invoked; user absolute language (Mythos rule 11) | Prevents re-litigation of settled choices in the resumed session; "REJECTED" field prevents dismissed alternatives from being re-proposed | `use flat-file over DB for session-bridge \| WHY: lock-contention risk \| REJECTED: live SQLite writes` |
| `THREAD-OPEN` | `<hex-8-id>` \| `<structural-label>` | Open question posed; in-flight dependency unresolved | Resumed session knows which questions are tacitly open; without this, re-answering is invisible duplication | `a3f9c100 \| approach: metadata-only vs body-parse for VOICE signals` |
| `THREAD-CLOSE` | `<hex-8-id>` | Question resolved; dependency satisfied | Prevents resumed session from treating a closed question as still open, which would waste turns | `a3f9c100` |
| `INFLIGHT` | `task=<label>` \| `step=<label>` \| `next=<label>` | Every agent dispatch; every major sub-step completion | The single highest-value field: tells the resumed session exactly where to resume without re-reading context. "next" field is the first action. | `task=write CONTINUITY-SCHEMA.md \| step=kept-fields table \| next=write rejected-fields table` |
| `VOICE` | `energy=<low\|medium\|high>` \| `signal=<enum>` \| `ref=<label>` | Layer 2 trigger detected (reply-length-drop, caps-detected, build-on, etc.) | Prevents register mismatch in the first resumed response; energy level determines how much preamble to strip | `energy=high \| signal=build-on \| ref=contradiction-table-callback` |
| `PERSONA` | `count=<N>` \| `category=<cat>` \| `obs=<structural-label>` | Layer 3 observation accumulates a new occurrence (below the 3-occurrence threshold for `user_profile.md`) | Preserves sub-threshold signals that have not yet been flushed to durable memory; without this, a pattern at count=2 is lost across compaction | `count=2 \| category=decision-style \| obs=accepts-first-option` |

**Privacy constraint on all entry types:** payload text is structural metadata written by code at the time of the event, not extracted from message bodies. Labels are author-assigned at write time. No verbatim user text. No verbatim assistant response text. The `obs` field in `PERSONA` is a category label, not a quoted observation.

---

### B. `session_threads` DB table (optional Layer 1 addition)

The DB table is the durable complement to the flat-file `THREAD-OPEN`/`THREAD-CLOSE` entries. It enables cross-session thread queries. The flat file is sufficient for v0.1; the DB table is additive.

| Column | Type | Load-bearing rationale | Example value |
|---|---|---|---|
| `id` | `TEXT PRIMARY KEY` | Stable cross-reference between flat-file entries and DB rows; used by `/resume` to join thread state | `a3f9c100` |
| `session_id` | `TEXT NOT NULL` | Scopes threads to a session; required for the FK into `memories.session_id` | `abc123def456` |
| `description` | `TEXT NOT NULL` | Structural label for the open question — drives which context the resumed session re-loads | `approach: metadata-only vs body-parse for VOICE` |
| `status` | `TEXT NOT NULL DEFAULT 'open'` | `open` / `closed` / `deferred` — the resume skill filters to `open` only; deferred signals intentional postponement vs accidental loss | `open` |
| `opened_at` | `TEXT DEFAULT (datetime('now'))` | Enables the 7-day rotation rule: threads older than one session cycle are stale | `2026-04-28T14:30:00` |

**Kept:** `id`, `session_id`, `description`, `status`, `opened_at`

**Omitted from §4's original DDL (with reason):** `closed_at` — derivable from the flat-file `THREAD-CLOSE` timestamp; storing it in the DB is redundant and requires a second write at close time. `project` — the memory dir is already project-scoped by path; this column duplicates the scope without adding query power.

**Privacy constraint on `description`:** must be a structural label assigned programmatically at the time `THREAD-OPEN` is written. If the thread description originates from a user phrase, it must be reformulated as a structural label ("open question: X vs Y"), never as a verbatim quote. Code-reviewer gate: any `description` value that contains first-person pronouns, direct-address forms, or sentence fragments longer than 80 characters should be flagged as potential message-body leakage.

---

### C. `continuity_pre_compact_<session_id>.md` — front-matter fields

The dump file's YAML front matter is read by `/resume` to identify the snapshot. These fields are structural coordinates, not content.

| Field | Type | Source | Load-bearing rationale | Example value |
|---|---|---|---|---|
| `type` | string constant | hardcoded | Distinguishes continuity dumps from token-metric dumps in the same memory dir; without it, `/resume` cannot filter to the right file type | `continuity-pre-compact` |
| `session_id` | string | PreCompact hook payload | Links the dump to the bridge journal and DB threads for the same session | `abc123def456` |
| `timestamp` | ISO-8601 UTC | hook fire time | Enables recency sorting; `/resume` reads the most recent dump by mtime, but timestamp is the authoritative tie-breaker | `2026-04-28T18:45:00Z` |
| `cwd` | string | hook payload | Scopes the resume output to the right project; prevents cross-project contamination when multiple projects share a memory dir | `/Users/macbook/Dev/claude-second-brain` |

---

## Schema — rejected fields

| Candidate field | Where it appeared | Rejection reason |
|---|---|---|
| `session_number` / `session_counter` | Implied by "session arc" tracking | Decorative vanity counter. Does not change any decision in the resumed session. Derivable from file count if ever needed. |
| `session_arc` | §3 Voice Signals block (`rising\|plateau\|winding-down`) | Decorative. "Winding down" is not actionable in a resumed session — the new session is always a fresh start. Energy level (`VOICE.energy`) already captures the operationally relevant signal. |
| `shared-refs` as a list in the dump | §3 Voice Signals block | Partially decorative. Shared refs are labels assigned at write time and already present in individual `VOICE` entries in `session_bridge.md`. Duplicating them in the dump front matter adds no information and creates a sync risk. `/resume` reads the bridge entries directly. |
| Raw `description TEXT` without structural constraint | §4 `session_threads` DDL | Privacy risk. An unconstrained TEXT field is an invitation to store verbatim user phrases. Kept in schema but with an explicit 80-char structural-label constraint and code-reviewer gate (documented above). |
| `closed_at` | §4 `session_threads` DDL | Derivable from the `THREAD-CLOSE` timestamp in `session_bridge.md`. Storing it in the DB requires a second write at close time and creates a drift risk if the flat file and DB disagree. |
| `project` column in `session_threads` | §4 `session_threads` DDL | Redundant. The memory directory is already project-scoped by filesystem path. An additional column adds a write obligation with no query benefit that is not already achievable via `session_id` join. |
| Persona `obs=<text>` as free text | §3 Persona Deltas block | Privacy risk. Free-text observation is a verbatim-quote vector. Rejected in favor of `obs=<structural-label>` (category label assigned by code, not extracted from message). The `category` field carries the semantic; `obs` carries only the specific sub-label within it. |
| `active-plans` list in dump | §3 Cross-References block | Derivable at resume time via `ls -t ~/.claude/plans/*.md \| head -3`. Capturing it at dump time introduces staleness (plans can be modified between dump and resume). `/resume` reads plan file mtimes live. |
| `weather` / any ambient context | Not in §4 but common in surveyed systems | Decorative by definition. No ambient context passes the decision criterion. |
| `token_budget_remaining` | Not in §4; present in token-metric sibling dump | Already written to `context_pre_compact_<id>.md` (existing file). Duplicating in the continuity dump creates two sources of truth for the same metric. The continuity dump is about threading state, not token accounting. |

---

## session_bridge.md ground rules

**What to log:**

| Entry type | Concrete trigger | Do NOT log |
|---|---|---|
| `DECISION` | A CLAUDE.md rule is explicitly invoked (e.g., "TDD always", "no mocks as deliverables"). User uses absolute language: "always / never / non-negotiable / 0 trace / preserve all". Mythos rule 11 fires. | Every code choice. Only decisions where future-session re-litigation would cost a turn or more. |
| `THREAD-OPEN` | An open question is posed that cannot be answered in the same turn. An agent dispatch creates a dependency whose result is not yet known. A research gap is named. | Rhetorical questions. Questions answered in the same message. |
| `THREAD-CLOSE` | The open question is answered, the dependency resolved, or the thread explicitly deferred. | Implicit closures — if not explicitly closed, leave it open. The resume skill filters to `status=open`; over-closing is worse than under-closing. |
| `INFLIGHT` | Every agent dispatch. Every major sub-step completion (e.g., finishing a section of a document, completing a test suite). Compaction fires (the hook writes a final INFLIGHT before exit). | Micro-steps within a sub-step. Log at the granularity where "resume from here" is unambiguous. |
| `VOICE` | A Layer 2 trigger fires from CLAUDE.md: `reply-length-drop`, `caps-detected`, `build-on`, `rhetorical-correction`, `past-behavior-reference`. A shared reference is established (callback label assigned). | Inferred mood without a detectable signal. Every message. Only when a signal changes the calibration. |
| `PERSONA` | A Layer 3 observation accumulates a new occurrence. The count field increments; the entry is not deduplicated — each occurrence is a new line. When count reaches 3, flush to `user_profile.md` and stop logging in the bridge. | Observations already at or past the 3-occurrence threshold (those belong in `user_profile.md`). |

**Format discipline:** every payload is a flat key=value or pipe-delimited string. No newlines within a single entry. No JSON, no YAML, no nested structure. The parser is a line reader — complexity in the format creates parse failures.

**Rotation:** if `session_bridge.md` is older than 7 days at session start, rename to `session_bridge_<YYYY-MM-DD>.md` and start fresh. Keep the last 2 rotations. The PreCompact hook reads only the current (non-rotated) file.

---

## Success criteria — "did continuity transfer this time?"

Observable from a post-compaction transcript without model introspection.

1. **In-flight task identified within 2 turns.** After `/resume`, the new session names the correct in-flight task and correct sub-step before the user provides any additional context. "Correct" means matching the last `INFLIGHT` entry's `task` and `step` fields verbatim or by paraphrase.

2. **No re-litigation of logged decisions.** Any decision with a `DECISION` entry in the prior session's bridge is not re-opened in the resumed session unless the user explicitly initiates it. Measure: count unsolicited "should we use X or Y?" turns in the first 10 turns of the resumed session. Target: 0.

3. **Voice register match within 1 correction.** The resumed session's first substantive response is in the same energy register as the last `VOICE.energy` value from the prior session. Measure: does the user issue a register correction ("shorter please" / "more detail") within the first 3 responses? Target: at most 1 correction, not 0 (some drift is normal).

4. **Open threads surfaced, not re-derived.** Any thread with `status=open` in the bridge is included in the `/resume` output's "Open threads" section. The user does not need to re-explain why a question is open. Measure: binary — open threads appear in the re-orientation output or they do not.

5. **No decorative re-discovery.** The resumed session does not run git commands, read files, or make tool calls that the prior session had already made for orientation purposes (e.g., re-reading `checkpoint.md` when its content is already in the continuity dump). Measure: count redundant orientation tool calls in first 5 turns. Target: 0.

---

## Open questions / decisions deferred to L2+

- **`description` field enforcement.** The 80-char structural-label constraint on `session_threads.description` needs a validator at write time, not just a code-reviewer gate. L2 should add a `_validate_thread_label(text: str) -> bool` helper in `continuity_dump.py` that rejects free-form prose before the DB write.

- **`VOICE.ref` label namespace.** Shared-ref labels (e.g., `contradiction-table-callback`) are author-assigned at write time with no schema enforcement. Two agents writing different labels for the same ref will cause duplicates. L2 should define whether labels are free-form or drawn from a controlled vocabulary per project.

- **Importance scoring for threads.** The `session_threads` table has no importance column. The Generative Agents recency+importance+cosine formula (adopted from RESEARCH.md §4) could rank which open threads surface first in `/resume` output. Deferred: v0.1 surfaces all open threads; L2 adds importance-ranked truncation when thread count exceeds 5.

- **`INFLIGHT` on SessionStart.** The design writes `INFLIGHT` on agent dispatch and sub-step completion. If the session ends cleanly (user closes terminal without compaction firing), the last `INFLIGHT` reflects the last completed step, not the next action. L2 should evaluate whether a `SessionEnd` hook write of a final `INFLIGHT` is warranted, or whether "last completed step + 1" is sufficient for the resume skill.

- **Flat-file and DB drift.** `THREAD-OPEN`/`THREAD-CLOSE` entries exist in both `session_bridge.md` and `session_threads`. If the DB write succeeds but the flat-file write fails (or vice versa), the two sources disagree. L2 should define which source wins at resume time. Recommendation: flat file is authoritative; DB is the queryable index. If they disagree, re-derive DB state from flat file.

- **Multi-project sessions.** `cwd` in the dump front matter scopes the snapshot to one project. If a session spans multiple projects (e.g., writing to `~/.claude/` and `~/Dev/claude-second-brain/` in the same session), a single `cwd` misrepresents the scope. L2 should evaluate whether `cwd` becomes a list or whether multi-project sessions always use the repo root as anchor.

- **Security-auditor gate item.** The `_capture_git_log()` function reads commit messages (public metadata). Commit messages in private repos may contain issue IDs, internal system names, or redacted content that the user considers non-public even if it is in version control. The security auditor should confirm the threat model: is commit message capture acceptable for all repo types, or should there be an opt-out flag?
