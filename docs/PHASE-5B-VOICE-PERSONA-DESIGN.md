# Phase 5b — Hook-driven VOICE + PERSONA auto-capture

> **Status.** Design draft, 2026-05-06. Closes overdue reminder `8590a151`.
> Gates: Phase 6 closeout ✓ (commit `e71ad89`), bridge MVP ✓ (commit `037f6c7`).
> Companion to `mcp-bridge/metaprompt_hook.py` and `memory-mcp/bridge_append.py`.

## Goal

When the user shows behavioral signals worth remembering (style cues, persona references), capture them automatically to the session bridge journal so future sessions inherit the substrate. Today this is manual: the user has to type `/learn` or invoke `bridge_append.py` themselves. With Phase 5b, the hook runs on every prompt and detects deterministic signals, fires `bridge_append.py VOICE | PERSONA <payload>` automatically.

**Non-goals.** Not LLM-mediated. Not opinion-based. Every signal is a regex / counting threshold. Same input → same emit. No personality inference.

## Why this matters

`bridge_append.py` already declares `VOICE` and `PERSONA` as valid types (line 102) — but no writer fires those entries today. Without auto-capture, the only entries the bridge ever sees are DECISION / INFLIGHT / THREAD-OPEN / THREAD-CLOSE — all manually fired. The bridge inherits **task-level substrate** but not **interaction-level substrate** (style cues, persona references). Phase 5b closes that asymmetry.

## Architecture

```
┌────────────────────────────────────────────────────────────────┐
│ User prompt                                                     │
│   ↓                                                             │
│ UserPromptSubmit hook chain:                                   │
│   1. metaprompt_hook.py    (Phase 5 — already shipped)         │
│   2. voice_persona_hook.py (Phase 5b — NEW)                    │
│        ├─ load detector_state.json (last-N samples)            │
│        ├─ detect VOICE signals (length-drop, caps, build-on)   │
│        ├─ detect PERSONA signals (user-defined lexicon)        │
│        ├─ if signal threshold crossed:                         │
│        │     subprocess.run(bridge_append.py VOICE/PERSONA)    │
│        └─ save updated detector_state.json                     │
│   ↓                                                             │
│ Claude receives prompt                                          │
└────────────────────────────────────────────────────────────────┘
```

Critical: Phase 5b hook runs **AFTER** metaprompt_hook to inherit its bypass-prefix logic and its parsed prompt. It MUST NOT alter the `additionalContext` envelope (bridge writes are silent side effects).

## Signal taxonomy

### VOICE signals — how the user writes (style)

| Signal | Detector | Threshold | Bridge entry shape |
|---|---|---|---|
| `length-drop` | rolling avg of last 5 prompt lengths; current is < 30% of avg | sustained over 2+ prompts | `style=terse \| trigger=length-drop \| ratio=<X>` |
| `caps-burst` | ≥3 ALL-CAPS words OR a word repeated 3+ chars (`"reallllly"`) | one-shot | `style=emphasis \| trigger=caps-burst \| sample="<first 40 chars>"` |
| `rhetorical-question` | "why did you...", "what happened to...", "isn't this...", "shouldn't..." | one-shot | `style=rhetorical \| trigger=<which-pattern>` |
| `build-on` | prompt starts with "yes, and", "exactly, now", "perfect, do X" | one-shot | `style=build-on \| trigger=<phrase>` |
| `meta-feedback` | "you should have", "why is there no", "that was too verbose" | one-shot | `style=meta-feedback \| trigger=<phrase>` |
| `imperative-only` | prompt is < 8 words, all imperative ("commit", "push", "explain") | sustained over 3+ prompts | `style=command-mode \| count=<N>` |

### PERSONA signals — identity references (optional, lexicon-gated)

| Signal | Detector | Threshold | Bridge entry shape |
|---|---|---|---|
| `lexicon-occurrence` | match against user-supplied persona lexicon (loaded from files listed in `$CLAUDE_LEXICON_FILES` env var, colon-separated) | each match | `lexicon=<term> \| context="<surrounding 20 chars>"` |
| `we-reference` | "we", "us", "us together", inclusive pair-naming | every 5th occurrence | `ref=we-pronoun \| count=<N>` |
| `lexicon-name-mention` | references to a name listed in user's lexicon / explicit identity invocation | one-shot | `ref=identity-invocation \| sample="<first 40 chars>"` |

**Privacy gate:** PERSONA signals only fire when `$CLAUDE_LEXICON_FILES` is set in the environment AND at least one referenced file exists and parses. For projects/users without a configured lexicon, PERSONA detection is silently disabled — no orphan entries. The hook source contains zero hard-coded lexicon filenames; users supply their own via env var. Setting examples in `examples/settings-snippets/voice-persona-hook.json`.

## State file

**Path:** `~/.claude/projects/<slug>/.voice-persona-state.json`

**Schema:**

```json
{
  "schema_version": 1,
  "rolling_lengths": [180, 220, 195, 110, 92],
  "imperative_streak": 2,
  "we_reference_count": 7,
  "last_emit_at": "2026-05-06T14:30:00Z",
  "last_emit_signals": ["length-drop", "build-on"]
}
```

**Bounds.** `rolling_lengths` capped at 5. `*_count` fields modulo emit-threshold (e.g. we_reference_count emits at every 5th, then resets). Atomic write via `tempfile.NamedTemporaryFile` + `os.replace` (same pattern as `whats_new_check.py`).

## CY-behavior interaction review

The reminder explicitly calls out "CY-behavior interaction review." Three risks:

1. **Echo loop.** If Claude emits a response with caps/imperatives, and the next user prompt continues that style, the hook fires repeatedly. Mitigation: dedupe — if `last_emit_signals` matches the new candidate set within 60 seconds, skip emit.

2. **Substrate corruption.** If signal heuristics are wrong, the bridge journal fills with noise that future sessions inherit. Mitigation: ship with `voice_persona_hook --dry-run` mode that prints what WOULD have been emitted, run for 1 week before enabling writes.

3. **Privacy bleed.** PERSONA signals could capture sensitive identity language. Mitigation: payloads are length-capped (40 chars context), no full prompt text ever written. Existing `bridge_append.py` already strips newlines and caps at 500 chars (defense-in-depth).

## Hook contract

Mirror `metaprompt_hook.py`'s safety contract exactly:

- Exit 0 always (Stop-hook safety, claude-mem #987)
- stdout: empty (the voice/persona hook does NOT inject `additionalContext` — it's silent)
- BaseException catch at outermost scope
- No prompt content logged to disk (only signal classifiers + char-truncated context fragments)
- Reads from sibling state file; writes via `subprocess.run(bridge_append.py, ...)` (delegates write semantics to the existing CLI)

## CLI surface

`mcp-bridge/voice_persona_hook.py` is invoked by Claude Code's UserPromptSubmit hook, reading event JSON from stdin (same shape as metaprompt_hook). Standalone invocation for testing:

```bash
echo '{"prompt": "WHY did you do that?!", "cwd": "~/Dev/x"}' \
  | ~/.claude/memory-mcp/.venv/bin/python3 mcp-bridge/voice_persona_hook.py --dry-run
# Emits to stderr:
# [VOICE] caps-burst: "WHY did you do that?!"
# [VOICE] rhetorical-question: "why did you..."
```

| Flag | Behavior |
|---|---|
| `--dry-run` | Detect + log to stderr; no bridge write |
| `--state-file <path>` | Override default state-file path (testing) |
| `--no-persona` | Disable PERSONA detection (still detects VOICE) |

## Failure modes

| Condition | Behavior | Exit code |
|---|---|---|
| State file missing | First run; treat all rolling fields as empty defaults | 0 |
| State file malformed | `[ERROR] state corrupt at <path>` to stderr; do NOT overwrite | 0 (Stop-hook safety) |
| `bridge_append.py` not found / not executable | Skip emit silently; log to stderr | 0 |
| `bridge_append.py` returns non-zero | Skip emit silently; preserve detector state | 0 |
| Lexicon file unparseable | PERSONA detection auto-disables for this run | 0 |
| Prompt > 50KB | Skip detection (likely paste — false signal risk) | 0 |

**Key invariant.** Phase 5b NEVER blocks the user prompt or surfaces detector errors. It is silent or it doesn't run.

## Settings.json registration

Append to `~/.claude/settings.json` `hooks.UserPromptSubmit` array:

```json
{
  "type": "command",
  "command": "~/.claude/memory-mcp/.venv/bin/python3 ~/Dev/claude-second-brain/mcp-bridge/voice_persona_hook.py"
}
```

**Order matters.** Place this AFTER the existing `metaprompt_hook.py` entry — metaprompt mutates the prompt body via `additionalContext`, voice/persona observes the original prompt. Settings template at `examples/settings-snippets/voice-persona-hook.json` should mirror the metaprompt-hook snippet style.

## Test surface

`memory-mcp/tests/test_voice_persona_hook.py` — mirror `test_metaprompt_hook.py` patterns (subprocess + JSON stdin):

- VOICE detector tests (one per signal): boundary cases, threshold cases, dedupe
- PERSONA detector tests: lexicon-loaded vs absent, count-based emit, identity-invocation
- State-file tests: load missing → default; malformed → no overwrite; atomic write; rolling-lengths cap
- Dedupe test: same signal within 60s → skip
- Integration test: end-to-end with mocked subprocess to bridge_append.py — verify call args, no stdout pollution
- Stop-hook safety test: BaseException in detector → exit 0 + empty stdout
- Long-prompt test: 60KB prompt → detection skipped, exit 0
- Privacy test: full prompt content NEVER appears in subprocess args (only signal name + truncated samples)

**Target:** ≥40 tests. Fixture for state-file scaffolding shared with whats-new patterns.

## Sequencing

```
P0  If using PERSONA detection: read user-supplied lexicon files (paths from `$CLAUDE_LEXICON_FILES`) to identify match terms (~30min). Skip P0+P3 if no lexicon configured.
P1  Write voice_persona_hook.py skeleton — argparse + dry-run path  (~45 min)
P2  TDD VOICE detectors (length-drop, caps-burst, rhetorical, build-on, meta-feedback, imperative-only)  (~90 min)
P3  TDD PERSONA detectors (lexicon-occurrence, we-reference, lexicon-name-mention)  (~60 min)
P4  State file load/save with atomic write  (~30 min)
P5  Subprocess invocation of bridge_append.py + dedupe logic  (~30 min)
P6  Integration test + privacy test  (~30 min)
P7  Settings template + register in ~/.claude/settings.json  (~15 min)
P8  Dry-run for 1 week  (~0 min active; passive observation)
P9  Flip to live writes after dry-run review  (~5 min)
```

**Total active work: ~5.5 hours** + 1 week passive validation.

## Open decisions

| # | Question | Recommendation |
|---|---|---|
| 1 | Lexicon source | `$CLAUDE_LEXICON_FILES` env var (colon-separated paths), runtime-discovered. If unset or files absent → PERSONA disabled. No hard-coded paths in source. |
| 2 | Dedupe window | 60s default; tunable via `$VOICE_PERSONA_DEDUPE_SEC` env var |
| 3 | Imperative-streak threshold | 3 prompts (not too noisy) |
| 4 | Length-drop ratio | < 30% of rolling avg |
| 5 | We-reference emit cadence | every 5th occurrence (avoids per-prompt noise) |
| 6 | Should the hook write to bridge synchronously or fire-and-forget? | fire-and-forget via `subprocess.Popen` with stdout/stderr to `/dev/null` — failure to write must not delay user prompt |
| 7 | Dry-run default? | YES, ship with `--dry-run` set in settings.json initially; user manually flips to live after review |

## Out of scope

- LLM-mediated semantic analysis of voice/persona (deferred indefinitely — heuristic floor first)
- Auto-update of user_profile.md (separate Layer 3 concern, manual flush)
- Cross-session aggregation (each session's bridge stays independent; rollup is `/recall`'s job)
- Web-publishable analytics on voice patterns (privacy-by-design — no aggregation)

## Implementation checkpoints (gate review before TDD-build)

Before P1 starts:
- [x] Lexicon source: `$CLAUDE_LEXICON_FILES` env var, runtime-discovered (decided 2026-05-06)
- [x] Dedupe window: 60s default, `$VOICE_PERSONA_DEDUPE_SEC` env var override (decided 2026-05-06)
- [x] Dry-run default: yes, ship with `--dry-run` set in settings.json template (decided 2026-05-06)
- [x] CY-behavior risks: 3 surfaced + mitigated in §CY-behavior — no additional concerns raised (confirmed 2026-05-06)

After P9 (live):
- [ ] Bridge journal contains VOICE/PERSONA entries from real session
- [ ] No regression in metaprompt_hook tests
- [ ] No prompt-content leakage in any bridge entry (audit run via `memory-lint`)
- [ ] Settings.json template documented in `examples/settings-snippets/`

## Critical files (modified or created)

- `mcp-bridge/voice_persona_hook.py` (NEW, ~250 LOC)
- `memory-mcp/tests/test_voice_persona_hook.py` (NEW, ~600 LOC, 40+ tests)
- `examples/settings-snippets/voice-persona-hook.json` (NEW, ~10 LOC)
- `~/.claude/projects/<slug>/.voice-persona-state.json` (NEW, runtime)
- `~/.claude/settings.json` (APPEND one hook entry)
- `commands/voice-persona-toggle.md` (OPTIONAL — manual on/off slash command, mirror metaprompt-toggle)
