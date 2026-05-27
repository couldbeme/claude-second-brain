---
description: Multi-lens decision against a hard binary — bind N personas as lenses, each issues a structured verdict (or refusal), output is the named disagreement (majority + dissents + unresolved residue), not consensus. The operator owns the final move.
argument-hint: <proposition> [--lenses=slug1,slug2,slug3] [--mode=verdict|dissent|both]
---

# /tribunal — Decide under hard binaries, preserve the disagreement

Apply N persona-bound lenses to a single proposition. Each lens issues a structured verdict or a first-class refusal. The output names the majority, names the dissents, and surfaces the unresolved residue — the operator decides; the system does not collapse to a Chairman's consensus.

The driving question: *what does each load-bearing lens see in this proposition that the operator's framing has not yet engaged?*

## How it differs from `llm-council`

`/tribunal` adopts the fan-out shape of [karpathy/llm-council](https://github.com/karpathy/llm-council) and inverts the synthesis. Where `llm-council` reduces variance across *provider training runs* and collapses to a Chairman's single answer, `/tribunal` exposes variance across *theoretical lenses* and preserves the dissent. Diversity vector: persona, not provider. Output: named disagreement, not consensus.

## Requirements

This skill requires a `personas/` directory in your project with one markdown file per expert-lens, named `<domain>__<slug>.md` (e.g. `personas/falsifiability__popper.md`). Each persona file must include YAML frontmatter with: `name`, `domain`, `expert_slug`, `when_to_invoke`, `signature_techniques`, `anti_patterns_called_out`, `provenance`, `lens_type: persona` (or `lens`). See the `personas/` examples shipped alongside this skill for the schema template. Without a `personas/` directory, `/tribunal` refuses the invocation.

## Inputs

- **`proposition`** (required) — the claim or decision to verdict. Phrased as a complete sentence the lenses can argue with. *"Should we ship X?"*, *"Is claim Y supported?"*, *"Does pattern Z apply here?"*
- **`--lenses=slug1,slug2,slug3`** (optional) — list of persona slugs from your project's `personas/` directory. Default: 3 most-relevant lenses chosen by matching the proposition's domain against each persona's `when_to_invoke` field. Max: 5 (beyond 5, the residue stops being signal and starts being noise).
- **`--mode=verdict|dissent|both`** (optional, default `both`) — `verdict` returns only the majority + recommended move; `dissent` returns only the disagreements + residue; `both` returns the full structure.

## Workflow

### Phase 1 — Parse the proposition and select lenses

1. Read the proposition. If it is not a complete declarative or interrogative sentence the lenses could agree or disagree with, **refuse** the invocation and ask the operator to sharpen the framing.
2. If `--lenses` not supplied: select 3 from the project's `personas/` directory by `when_to_invoke` field matching the proposition's domain. Honest about the selection — print which 3 were chosen and why. If `personas/` doesn't exist, refuse and direct the operator to the Requirements section above.
3. Validate each lens slug resolves to a real file in `personas/<domain>__<slug>.md`. Unresolved slug = hard refusal (do not silently substitute).

### Phase 2 — Bind each lens to a subagent (parallel dispatch)

For each lens, dispatch a `general-purpose` Agent in parallel (single message, multiple Agent tool calls). Each agent prompt:

```
You are bound to the persona at `personas/<file>`. Read it in full before responding. You ARE this lens for the purposes of this verdict — voice, mental models, signature moves, what-they-refuse all apply.

The proposition is:
<proposition>

Return a structured verdict in this exact shape:
{
  "lens": "<expert_slug>",
  "verdict": "support" | "oppose" | "refused",
  "confidence": 0.0-1.0,         # how strongly the lens commits to the verdict
  "reasoning": "<one paragraph in the lens's voice>",
  "dissent_axis": "<the axis on which this lens differs from baseline judgment, in one phrase>",
  "refusal_reason": "<if verdict=refused, the persona's 'What they refuse' block clause that fires; else null>"
}

If the persona's 'What they refuse' block applies to this proposition, verdict MUST be "refused" — do not force a yes/no when the lens would not give one. Refusal is first-class signal.
```

Wait for all lenses. Do not proceed on partial responses.

### Phase 3 — Detect the structure

From the N verdicts, compute:

- **Majority**: the most common verdict among non-refusals. If no plurality (e.g., 1 support / 1 oppose / 1 refused with N=3), majority is `null`.
- **Dissents[]**: every verdict whose `dissent_axis` differs from the others by *kind*, not just degree. Two lenses both saying "support but worried about X" share an axis; they are not dissents from each other. A lens that refuses, a lens that opposes on epistemic grounds, and a lens that supports on cognitive grounds are *three structurally distinct* dissents.
- **Refusals**: every verdict where `verdict=refused`. These are first-class — a refusal carries information ("this is the wrong shape of question for this lens to answer") and is NOT a missing data point.
- **Unresolved residue**: the thing the operator's framing did not surface. Compute from: refusals + dissents that point at the framing itself + concerns no other lens addressed.

### Phase 4 — Synthesize the output

Output in this exact shape (drop sections per `--mode`):

```
## /tribunal verdict — <proposition (echoed verbatim)>

### Lenses (chosen, with reasoning)
- <slug-1>: <one-line why this lens>
- <slug-2>: ...
- <slug-3>: ...

### Per-lens verdicts
| Lens | Verdict | Confidence | Dissent axis |
|---|---|---|---|
| <slug-1> | support / oppose / refused | 0.X | <axis> |
| ... | ... | ... | ... |

### Majority
<verdict + N/total + which lenses formed the majority>
*OR*
**No majority** — verdicts are structurally distinct; the proposition does not have a single answer at this level of framing.

### Dissents
- **<slug>**: <one paragraph in the lens's voice — reasoning + dissent axis>
- **<slug>**: ...

### Refusals (first-class)
- **<slug>**: <refusal reason — which 'What they refuse' clause fires + what the refusal points at>

### Unresolved residue
<one paragraph: what the operator's framing did not engage; what would have to be resolved before the proposition becomes a single question>

### Recommended move (operator-owned)
<one paragraph: the action the operator should take given the structure above — NOT "do X" but "the shape of the next move is Y because Z">
```

### Phase 5 — Self-check (Popper-style, internal)

Before returning the output, the skill verifies (silently):

- Did any lens produce a verdict structurally indistinguishable from what baseline Claude would have produced *without* the persona binding? If yes, that lens contributed nothing and should be flagged in the residue (`<slug> verdict tracked baseline — lens may have failed to bind`).
- Did all N lenses produce the *same* verdict with the *same* axis? If yes, the proposition was not genuinely contested — the residue should name "no real disagreement found" and the operator should consider whether `/tribunal` was the right tool.

## Refusal semantics (first-class)

A persona refusing is not a failure mode — it is the most expensive signal `/tribunal` can produce. A refusal means: *this lens believes the proposition is not the right shape of question for this lens to answer.* Examples:

- `eliza-refusal__weizenbaum` refuses propositions that assert behavior of nonexistent AI artifacts.
- `falsifiability__popper` refuses propositions that defend an unfalsifiable claim (the move is to rephrase the claim, not verdict on it).
- `dual-process__kahneman` refuses propositions where the framing itself is doing the work (the move is to reframe).

When `mode=verdict`, refusals are still surfaced in a separate block — they are NOT dropped.

## Failure modes

| Symptom | Diagnosis | Operator move |
|---|---|---|
| All N lenses agree with high confidence and the same axis | Proposition not genuinely contested | Consider whether `/tribunal` was the right tool; perhaps `/karpathy-bar` for a quality gate, or just decide |
| All N lenses refuse | Proposition is structurally unanswerable at the current framing | Rephrase the proposition; do not seek a different lens set |
| N=2 and they split | Tie + no residue surfacing | Add a third lens explicitly; ties are not informative |
| Lens verdict tracks baseline Claude exactly | The persona binding failed (the agent did not actually engage the lens) | Re-dispatch that lens with explicit "read the persona file in full" reinforcement; if still tracking baseline, the persona itself is decorative — cut |
| Recommended move = "ship X" exactly as the operator predicted | `/tribunal` failed to add information | Falsifiability check: did the output name anything the operator did not already know? If no, the invocation was decorative |

## When to use

- A decision that *feels* binary but where the operator suspects the framing is doing work the substance has not done
- A claim about a system / artifact / strategy where multiple incommensurable failure modes are plausible (epistemic + cognitive + ontological)
- A proposition asserting behavior of an AI artifact (Weizenbaum lens fires reliably here)
- A `/idea → /tribunal → /reflect` composition for half-formed thoughts that need to be sharpened into a move

## When NOT to use

- Clear technical decisions with one correct answer (use `/karpathy-bar` or a test, not `/tribunal`)
- Pure-style preferences ("which variable name reads better") — `/tribunal` is too expensive for trivial calls
- When the operator already knows the answer and wants confirmation — `/tribunal` will say so in the residue, but the operator should just commit
- High-frequency decisions — `/tribunal` is a 3-subagent dispatch; budget accordingly

## Falsifiability check (recursive — applies to `/tribunal` itself)

Per Popper's own rule: *what observation would refute the claim that `/tribunal` is more useful than `/karpathy-bar` or unaided Claude judgment?*

- **Refutation criterion**: if `/reflect` on a session shows that `/tribunal`'s output named nothing the operator did not already know, the invocation was decorative.
- **Tracking**: maintain a count via `/reflect lens=popper --scope=tribunal-invocations` of decorative-vs-load-bearing invocations.
- **Cut threshold**: if >2/3 of invocations are decorative across a 10-invocation window, `/tribunal` is more weight than value — deprecate.

The skill ships with this gate, not around it.

## Implementation

- Pure prompt-based skill (no Python script). Claude executes the workflow directly.
- Subagent dispatch via the Agent tool (`subagent_type=general-purpose`), one per lens, parallel.
- Persona binding by reading `personas/<domain>__<slug>.md` in full inside each subagent before that subagent responds.
- No external API; no provider routing; runs entirely within the Claude Code session.

## Related

- `skills/reflect/SKILL.md` — paired retrospective skill; `/tribunal` produces structured disagreement, `/reflect` does the lens-bound retrospective
- `skills/iterate/SKILL.md` — sibling skill for narrow-optimization-under-deadline; different shape, same operator-cognitive family
- `skills/karpathy-bar/SKILL.md` — quality-bar skill; recommended gate for `/tribunal` output before commit
- Example persona files (humanities lenses): `personas/falsifiability__popper.md` (Popperian falsifiability gate), `personas/dual-process__kahneman.md` (System 1/2 + bias detection), `personas/eliza-refusal__weizenbaum.md` (refuse-to-verdict for nonexistent-AI claims). Use these as schema templates for your own domain-specific persona files.
- Prior-art: [karpathy/llm-council](https://github.com/karpathy/llm-council) — the fan-out shape `/tribunal` inverts (council collapses to Chairman consensus; tribunal preserves disagreement as terminal state).
