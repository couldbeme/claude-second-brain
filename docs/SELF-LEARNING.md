# Self-Learning — implementation reference

> `CLAUDE.md` (Self-Learning Protocol) referenced this file for implementation details. The file never existed (`git log --all -- docs/SELF-LEARNING.md` → 0 commits). This is the honest version: it documents **what actually runs as code** vs **what runs as a behavioral protocol Claude follows**, and flags the gaps between the protocol's claims and the implementation. Honesty here is load-bearing — see `docs/SUBSTRATE-HEALTH.md`.

## The two mechanisms

csb's self-learning has **two distinct mechanisms** that the protocol prose sometimes blurs together:

1. **Code-automated** — runs in Python, fires from a hook or CLI, independent of Claude's attention.
2. **Behavioral-rule** — an instruction in `CLAUDE.md` that **Claude executes each session**. It "works" only because the model follows the protocol; there is no code enforcing it.

Both are legitimate. The failure mode is *describing a behavioral-rule as if it were code-automated* — a reader who greps for the automation finds nothing and concludes the toolkit overclaims. Label honestly and that failure disappears.

---

## Code-automated (real, wired)

| Mechanism | Code | Trigger |
|---|---|---|
| Session-bridge journal append | `memory-mcp/bridge_append.py` → `continuity_dump.append_bridge_entry()` | CLI, fire-and-forget during a session |
| Atomic write + lock | `fcntl.flock()` (exclusive) + `os.replace()` in `continuity_dump.py` | every bridge append |
| Pre-compact continuity snapshot | `memory-mcp/precompact_hook.py` → `continuity_dump.write_continuity_snapshot()` + `context_estimator.py` | `PreCompact` hook |
| Session-start orientation | `~/.claude/hooks/session_start_orient.py` | `SessionStart` hook (reads checkpoint, MEMORY.md, reminders) |
| Markdown → sqlite ingest | `memory-mcp/ingest_markdown.py` | `/ingest` skill |
| Markdown auto-memory write | `/learn` skill → Write to `~/.claude/projects/<slug>/memory/` | `/learn` invocation |

### Audit-log schema (session_bridge.md)

Each entry: `[YYYY-MM-DDTHH:MM:SSZ] [TYPE] payload` (parser at `continuity_dump.py`). Types:

| Type | Fired by | Payload |
|---|---|---|
| `DECISION` | Claude (manual, per protocol) | `<text> \| WHY: <…> \| REJECTED: <…>` |
| `INFLIGHT` | Claude (manual) | `task=… \| step=… \| next=…` |
| `THREAD-OPEN` / `THREAD-CLOSE` | Claude (manual) | `<8-hex-id> [\| desc]` |
| `VOICE` / `PERSONA` | **[PLANNED — Phase 5b]** auto-fire hook, not yet shipped | — |

The CLI caps payloads at 500 chars and strips newlines as defense-in-depth.

---

## Behavioral-rule (works via protocol, not code)

These are `CLAUDE.md` instructions Claude follows each session. **No code enforces them.** Documenting them as protocols (not systems) is the honesty fix.

| Behavior | CLAUDE.md ref | Honest status |
|---|---|---|
| Layer-1 `[LEARNING]` tag + immediate Write | self-learning §Layer-1 | behavioral-rule; the Write itself is real, the *decision to write* is the model's |
| Layer-1 write-verification (read-back, assert date+40ch) | self-learning protocol | behavioral-rule; **no verification code** — relabel or add a Stop-hook backstop |
| Layer-2 correction-pattern detection | self-learning §Layer-2 | behavioral-rule; the model watches for rhetorical/emphasis signals |
| Layer-3 user-model update | self-learning §Layer-3 (says "auto-updates") | behavioral-rule; Claude edits `user_profile.md` per protocol — **relabel "auto-updated" → "Claude updates per protocol"** |
| Ideas-backlog auto-append on trigger phrases | self-learning §ideas-bridge | behavioral-rule; `/idea`+`/ideas` skills are code, the *silent auto-append* is protocol |

---

## Known gaps (claimed but absent)

Surfaced by the 2026-05-31 audit; tracked in `docs/SUBSTRATE-HEALTH.md`:

- **Stop hook** — `CLAUDE.md` calls it the "safety net." It is **not configured** (`settings.json` hooks = PreCompact, UserPromptSubmit, SessionStart). The real safety mechanism today is the Layer-1 write+read-back behavioral rule. Either implement the Stop hook or relabel line 69 `[PLANNED]`.
- **Secret-scan on writes** — `CLAUDE.md:72` lists "secret-scan" among implementation details. **No secret-scanning runs** on bridge entries or memory writes today. The protection that *does* hold is CLAUDE.md rule 13 (publish-safe-by-default) as a behavioral rule. Implement a scan or drop the claim.
- **memory.db recall** — configured MCP `memory` server, 38 rows, dormant since 2026-04-27, not connected in every session. See `docs/SUBSTRATE-HEALTH.md` §4 — expose-vs-retire is a deliberate pending decision.

---

## The re-activation hooks (so this is resumable, not rotting)

If/when these get built, the design is preserved here:

- **Stop hook** → `~/.claude/hooks/session_stop_learn.py`, registered under `settings.json` `hooks.Stop`; reads the session for untagged learnings, writes any it finds, emits `[SAVE-FAILED]` on write error.
- **Layer-3 auto-update** → extend `session_start_orient.py`'s companion or a Stop hook to diff observed signals against `user_profile.md` sections and append.
- **VOICE/PERSONA auto-fire** → Phase 5b: `UserPromptSubmit` hook detecting deterministic voice/persona signals, fired into `bridge_append.py` (types already declared).

Until then, the behavioral-rule versions are the implementation, and that is stated plainly — not disguised as automation.
