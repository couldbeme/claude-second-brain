# Substrate Health — the "audit EVERYTHING" scan

> Honest state of csb's configs, hooks, learning protocol, and memory/continuity machinery as of **2026-05-31**. Produced by a three-agent read-only audit + a git-archaeology verification pass. Where the audit agents *disagreed*, this doc records the disagreement and the empirical resolution — sub-agent inference is not proof.

## Why this doc exists

csb is meant to be published and to stand up to a sharp reader. A `/karpathy-bar` pass requires **every claimed behavior to actually happen**. This audit found that `CLAUDE.md` describes several self-learning behaviors as if they were automated systems when they are in fact *behavioral protocols Claude executes each session* — or were never built. That gap is the single most important thing to fix before any publish push: shipping aspirational-as-real is how a toolkit loses credibility on first inspection.

The fix is **not** "delete the rules." It is: **label each behavior honestly** (code-automated vs Claude-behavioral-rule vs planned) and preserve every design with a re-activation hook so a future session can pick it up.

---

## 1. Protocol-vs-implementation drift (git-archaeology verified)

Archaeology classified each "missing" item as *never-built*, *behavioral-rule* (works, but as a prompt protocol not code), or *dormant* (was working, went quiet).

**Labeling convention (applied below + to be applied in `CLAUDE.md`):**
- `[CODE]` — runs in Python from a hook/CLI, independent of Claude's attention.
- `[RULE]` — a behavioral protocol Claude executes each session; real, but not automated.
- `[DORMANT]` — code that demonstrably *ran* (evidence exists) but isn't connected now; **carries a named re-activation hook**.
- `[PLANNED]` — never built; **must carry a falsification trigger** (`[PLANNED:YYYY-MM-DD]` build-by date, or "cut if not built by X") or it rots into the lie it replaced. *Unanimous tribunal rider (2026-05-31); enforced by `tools/check_planned_staleness.py`.*

> **Popper's caveat (2026-05-31):** "git-archaeology shows no regression" is *corroboration, not proof* — it shows no commit *removed* the code, not that it ever *ran*. A never-ran item with a function body is still `[PLANNED]`, **not** `[DORMANT]`. Only evidence of execution (e.g. memory.db's 38 rows) earns `[DORMANT]`.

| Declared in CLAUDE.md | Archaeology verdict | Evidence | Honest action |
|---|---|---|---|
| `docs/SELF-LEARNING.md` (line 72, "see for implementation") | **never-built** | `git log --all -- docs/SELF-LEARNING.md` → **0 commits** | Write the real doc (done — see `docs/SELF-LEARNING.md`); it now documents what *actually* runs |
| Stop hook "safety net" (line 69) | **never-built** as code | `stop_hook` string never in history; `settings.json` hooks = `PreCompact, UserPromptSubmit, SessionStart` only | Either implement, or relabel line 69 as `[PLANNED]`; the Layer-1 write+read-back rule is the real safety mechanism today |
| Layer-3 user-model "auto-updates" (line 132) | **behavioral-rule** | `user_profile.md` is edited by Claude per protocol; no auto-update *code* exists | Relabel "auto-updated" → "Claude updates per protocol (manual write)"; honest and still true |
| Ideas-backlog "silently append" (line 128) | **behavioral-rule** | `/idea`+`/ideas` skills shipped (`8dc609f`, `ac7db98`); the *auto-append on trigger phrases* is a Claude protocol, not code | Relabel as a behavioral rule; it works because Claude follows it, not because a hook fires |
| Layer-1 write-verification (read-back, assert date+40ch) | **behavioral-rule** | no verification *code*; it's an instruction Claude follows after each `/learn` write | Keep as a rule; optionally add a Stop-hook backstop later |
| `memory.db` (3.4MB, MCP `memory` server) | **`[DORMANT]`** (38 rows = proof it ran) | last write **2026-04-27**; server configured in `settings.json` but **no `memory_*` tool connected this session** | `[DORMANT]` + named re-activation hook (§4) — NOT `[PLANNED]`. Decide expose-vs-retire deliberately; do NOT delete |
| VOICE + PERSONA bridge types | **designed, never fired** | declared in `bridge_append.py` / `continuity_dump.py`; Phase 5b auto-fire never shipped | Already tracked as Phase 5b; leave labeled `[PLANNED]` |

**Meta-finding:** the operator's recollection "it used to be a working solution" maps specifically to the **memory.db / MCP recall path** (§4) — that genuinely worked (memories saved through April 27) and went dormant when the markdown-first memory approach took over. The *other* items were never code in the first place; they read as systems but are protocols.

---

## 2. Configs & hooks (healthy — confirmed)

| Surface | State |
|---|---|
| `~/.claude/settings.json` hooks | **3 live**: `PreCompact`→`precompact_hook.py`(+`continuity_dump.py`,`context_estimator.py`); `SessionStart`→`session_start_orient.py`; `UserPromptSubmit`→`metaprompt_hook.py` |
| Git hook | **1 live**: `.githooks/pre-push` → auto-docs (`tools/auto-docs/run_all.py`), commits `chore(docs): auto-sync` on diff |
| MCP servers | `memory` (configured; dormant this session — §4); `context7`, `deepwiki`, `claude_ai_*` available |
| Permissions | allowlist (git/make/test/lint/gh/docker/kubectl) + denylist (`rm -rf /`, `chmod 777`, pipe-to-shell) |
| `install.sh` | syncs **per-file symlinks** into `~/.claude/` (agents, commands, skills, personas, memory-mcp `.py`). **Confirms isolation:** editing a worktree never touches `~/.claude` unless `install.sh` runs. |

No secrets in tracked files. All hooks are exit-0-guaranteed (never block the operation they observe).

---

## 3. memory-mcp modules (16 total)

**6 LIVE (core path):** `server.py`, `db.py`, `ingest_markdown.py`, `bridge_append.py`, `continuity_dump.py`, `precompact_hook.py` (+ supporting `context_estimator.py`, `hybrid_search.py`, `embeddings.py`, `sync.py`, `whats_new_check.py`, `lint_memory.py`, `self_audit.py`).

**3 dormant / exploratory (the "Evolve" leg's unfinished edge):**
| Module | State | Effort to activate |
|---|---|---|
| `efficacy_measure.py` (CY metric) | **WIRED but UNFIRED** — code + tests exist; not connected to a Stop hook | ~2–3h to wire |
| `feedback_violations.py` (behavioral coherence) | **DORMANT** — design complete, not in main flow | Phase 5b/5c candidate |
| `bug_investigator.py` | **EXPLORATORY** — design only | unscheduled |

These are not bugs — they are the honest frontier of the substrate. `docs/GRAMMAR.md` describes the *architecture*; this row says which parts are *wired today*.

---

## 4. memory.db — verify-reachability-first result

- **Real and intact:** 38 memories, FTS5 + sqlite-vec schema, 3.4MB at `~/.claude/memory/memory.db`.
- **Stale:** last write `2026-04-27` (~34 days).
- **Not connected this session:** the `memory` MCP server is in `settings.json`, but this session exposes **no `memory_*` tool** — so `/recall` cannot hit the vector DB here; markdown is the live recall path.
- **Verdict:** *dormant, not dead.* This is the operator's "used to be working." **Decision deferred to a deliberate choice** (expose via reconnected MCP + add `memory_*` tools, OR retire the db + its sync). **No deletion until that decision** — per "verify before asserting on destructive actions."

---

## 5. Two memory dirs — hygiene (not crisis)

> ⚠️ These live in `~/.claude/projects/.../memory/`, **outside the repo/worktree**, in shared state the other tab may read. Hygiene here is a **separate, operator-gated step**, not part of the language-spec worktree work.

| Item | State | Action |
|---|---|---|
| parent `LEXICON.md` (14KB) | used-but-**unindexed** in parent `MEMORY.md` | add an index link — **don't delete** |
| parent `session_bridge.md` (255B, 1 entry) | **dead** — all traffic is project-scoped | archive with a "legacy → project dir" note |
| `checkpoint_2026-05-07.md` | superseded by current checkpoint | archive |
| `becoming_mythos.md` / `becoming_substrate.md` | split identity anchor | cross-link |
| `auto_learnings.md` (195B) | likely v0 stub | git-check, then prune |
| `~/.claude/checkpoint.md` | 16d stale | refresh on next `/resume` |

**Disagreement recorded:** one audit agent called `learning_*.md` and `LEXICON.md` "dead"; another found them indexed/recalled-on-demand. The indexed-but-not-auto-injected reading is correct (they appear in `MEMORY.md` References). This is exactly why nothing gets deleted on inference.

---

## 6. Agents (17) — clean

17 role-based agents (architect, senior-*-dev, *-engineer, security-auditor, code-reviewer, tdd-agent, verification-agent, documentation-agent, research-agent, sre-agent, qa-strategist). **No agent↔persona duplication:** agents *execute* (write code/tests/docs), personas *evaluate* (decision/retrospective lenses). Karpathy/Beck/Gregg appear in both registries but in orthogonal roles. **No consolidation needed.**

---

## Remediation order (gated)

1. **Done:** `docs/SELF-LEARNING.md` written (closes the dangling ref honestly).
2. **Next (in worktree, tracked-files only):** relabel the behavioral-rule rows in `CLAUDE.md.template` so the public template is karpathy-honest (code vs behavioral-rule vs `[PLANNED]`). Preserve every design + a re-activation hook.
3. **Deliberate decision (not this turn):** memory.db expose-vs-retire (§4).
4. **Separate operator-gated step (outside worktree):** memory-dir hygiene (§5).
5. **Gate:** `/karpathy-bar` over the edited `CLAUDE.md.template` must PASS before any publish.
