---
description: End-of-session retrospective through a single persona-bound lens. Reads session_bridge.md and outputs three blocks - what shifted, what stayed wrong, one move forward. Honest when there is not enough substrate to say anything.
argument-hint: --lens=<persona-slug> [--scope=session|last-N-commits|file:<path>]
---

# /reflect — Single-lens retrospective

Bind one persona to the session's structural substrate and produce a three-block retrospective: what shifted, what stayed wrong, one move forward. The output is short on purpose — three blocks, nothing more. The lens is the discipline; the brevity is the rule.

The driving question: *what does this one lens see in the work that was actually done that would change the next move?*

## How it differs from `/tribunal`

`/tribunal` binds N lenses to a *proposition* and preserves the disagreement. `/reflect` binds *one* lens to *completed work* and produces a single-voice retrospective. The mode is different: `/tribunal` is for deciding; `/reflect` is for looking back.

## Inputs

- **`--lens=<persona-slug>`** (required) — exactly one persona slug from `personas/`. The lens IS the retrospective; this is not optional.
- **`--scope`** (optional, default `session`) — what to retrospect on:
  - `session` (default) — recent INFLIGHT + DECISION + THREAD-OPEN/CLOSE entries from `session_bridge.md`
  - `last-N-commits` — read `git log --oneline -N` and the diffs
  - `file:<path>` — read the file's git history + current state; useful for "how did this file evolve and what would <lens> say about that evolution"

## Workflow

### Phase 1 — Resolve scope and read substrate

1. Resolve the lens slug → `personas/<domain>__<slug>.md` exists. Hard refusal if not.
2. By `--scope`:
   - **`session`**: read the bottom 50 entries of `~/.claude/projects/<slug>/memory/session_bridge.md` (the live decision/inflight/thread substrate). If <5 entries OR the most recent entry is >24h old, **refuse with substrate-empty message** — do not invent a retrospective from nothing. The empty-substrate refusal is first-class signal, not failure.
   - **`last-N-commits`**: `git log --oneline -N` + `git show <each-sha>` for the diffs. N defaults to 10 if not specified.
   - **`file:<path>`**: `git log --oneline -- <path>` + the current file content + the most recent diff touching it.

### Phase 2 — Bind the lens (no subagent — direct binding)

`/reflect` is single-lens by design. Read the persona file in full inside the current session (not via Agent dispatch). Voice, mental models, signature moves, what-they-refuse all apply to the retrospective output.

### Phase 3 — Apply the lens to the substrate

For each lens, the questions to ask the substrate are *the lens's signature moves applied retrospectively*. Examples:

| Lens | Retrospective questions |
|---|---|
| `falsifiability__popper` | Which decisions made in this scope are unfalsifiable as currently stated? Which ad hoc rescues were accepted as legitimate? Where did corroboration get treated as proof? |
| `dual-process__kahneman` | Which decisions look anchored (an arbitrary number drove the framing)? Which inside-view forecasts were made without base rates? Where did sunk-cost reasoning win? |
| `eliza-refusal__weizenbaum` | Which AI-feature claims in this scope assert behavior the artifact does not yet possess? Where did anthropomorphic language smuggle ontology? Which design choices exploit the ELIZA effect rather than substantive capability? |
| `typescript-tooling__cherny` | Where did the work add framework dependency when a small tool would have done? Where is type-system gymnastics doing work simpler runtime structure should have done? |

(Other lenses: substitute their `signature_techniques` and `what they refuse` as the retrospective questions.)

### Phase 4 — Output the three blocks

Output in exactly this shape — no more, no less:

```
## /reflect — lens=<slug> | scope=<scope>

### What shifted
<one paragraph, in the lens's voice, naming what genuinely moved during this scope — a decision that resolved, a belief that updated, an artifact that landed>

### What stayed wrong
<one paragraph, in the lens's voice, naming what the lens sees as still wrong — an ad hoc rescue that was accepted, an unfalsifiable claim that shipped, a bias that won, an ELIZA-shape that was productized>

### One move forward
<one paragraph: a single concrete next move the lens would recommend — NOT a list, NOT a hedged suggestion, ONE move, named explicitly>
```

If the lens cannot honestly produce content for any block, write `<nothing surfaced>` for that block — the lens not seeing something is information, not failure.

### Phase 5 — Self-check (Popper-style, internal)

Before returning the output, the skill verifies (silently):

- Is the "what stayed wrong" block structurally distinct from what baseline Claude would have written? If no, the lens binding failed.
- Is the "one move forward" actionable in <1 day, or is it a wish? Wishes are forbidden — re-prompt the lens for a concrete move.
- Does any block re-state the substrate verbatim instead of applying the lens to it? If yes, the binding failed and the retrospective is decorative.

## Refusal semantics (first-class, same as `/tribunal`)

A lens may refuse to retrospect on a scope:

- `eliza-refusal__weizenbaum` refuses to retrospect on a scope that contains only anthropomorphic claims about nonexistent AI (the move is to require the work be done first, not to verdict on it).
- `falsifiability__popper` refuses to retrospect on a scope with no falsifiable decisions to evaluate (the substrate did not contain testable claims).

Refusals are first-class output — print the refusal reason in place of the three blocks. Do not substitute a different lens.

## Failure modes

| Symptom | Diagnosis | Operator move |
|---|---|---|
| `substrate-empty` refusal | Bridge journal has <5 entries or is stale | Either work some more before reflecting, or pick a different `--scope` (e.g. `last-N-commits`) |
| Three blocks all read like baseline Claude | Lens binding failed | Verify the persona file was read; re-invoke with explicit re-read |
| "One move forward" is a wish, not a move | Lens did not commit | Re-invoke with sharper scope; the lens may not have enough to commit |
| All three blocks restate the substrate | Lens did not apply, only summarized | The skill failed — the retrospective is decorative; cut |

## When to use

- End of a working session — pair with `/session-recap` (which is content-summary; `/reflect` is lens-shaped)
- After a significant decision lands — *what does Popper / Kahneman / Weizenbaum see in that decision?*
- Before a `/tribunal` invocation — `/reflect lens=popper` on the prior decisions helps surface the proposition's framing problem
- Periodically (weekly?) on `--scope=last-N-commits` to track lens-shaped drift over time

## When NOT to use

- Pure information lookup ("what shipped this week") — use `/session-recap` or `git log`
- When the bridge journal is empty — `/reflect` refuses honestly; do not force it
- As a substitute for `/tribunal` on a contested proposition — `/reflect` is one-lens; it cannot surface disagreement

## Falsifiability check (recursive)

Per Popper's own rule: *what observation would refute the claim that `/reflect` adds value over re-reading the bridge journal directly?*

- **Refutation criterion**: if the three blocks contain nothing the operator could not have extracted by reading the substrate themselves, the lens added nothing.
- **Tracking**: log invocations with `/reflect lens=popper --scope=last-N-commits` periodically; track decorative-vs-load-bearing.
- **Cut threshold**: if >2/3 of invocations are decorative across a 10-invocation window, the skill is more weight than value — deprecate.

## Implementation

- Pure prompt-based skill (no Python script).
- Persona binding by reading `personas/<domain>__<slug>.md` directly in the current session (no Agent dispatch — `/reflect` is single-lens).
- Substrate reading via direct file access (`session_bridge.md` for default scope; `git log` + `git show` for commit scope; `Read` for file scope).
- No external API.

## Related

- `personas/falsifiability__popper.md`, `personas/dual-process__kahneman.md`, `personas/eliza-refusal__weizenbaum.md` — primary lenses for retrospection
- `skills/tribunal/SKILL.md` — sibling skill (decide vs reflect); `/idea → /tribunal → /reflect` composition
- `skills/iterate/SKILL.md` — sibling skill (narrow-optimization-under-deadline)
- `skills/resume/SKILL.md` — content-summary re-orientation; `/reflect` is lens-shaped retrospection (different shape, different time)
- `~/.claude/projects/<slug>/memory/session_bridge.md` — primary substrate for default scope
