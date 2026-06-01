# The Grammar — csb as a combinator language

> **You don't memorize 33 commands. You learn a dozen primitives in four families and one grammar — every command is a reading of it.**

This document names the thing that was always there. csb's commands, skills, and agents are not independent tools — they are recombinations of a small set of primitives. The composition was real but *implicit*: every `SKILL.md` re-implemented the shared pattern in prose, and the lineage lived only in author's-head and in scattered "this generalizes X" comments. This file makes the grammar explicit.

Every claim below cites a `file:line` you can open. If a line ref is wrong, the grammar is wrong — fix it here, don't paper over it.

---

## Why this is the moat (and the FOMO antidote)

Anthropic and other vendors will keep shipping individual skills — `/review`, `/security-review`, `/code-review` already exist as built-ins. They may even ship a tribunal-shaped thing. **Individual words in a vocabulary are commoditizable. A grammar is not.** The platform must stay unopinionated; it cannot ship *your* opinionated primitives-with-lineage plus a coherence substrate as an integrated whole. So the strategy is: stop competing at the skill level (you lose to the platform) and compete at the **language** level (the platform won't go there).

The triad that makes the language defensible:

> ### Compose · Cohere · Evolve
> - **Compose** — primitives recombine into operators recombine into workflows (this document).
> - **Cohere** — a belief substrate measures whether the system stays self-consistent: `CY` (Coherence Yield) at `memory-mcp/efficacy_measure.py:46`.
> - **Evolve** — an operator (a human, or Claude under instruction) extends the substrate (`/learn` writes confidence-weighted records; `fresh` refreshes lenses to field-current) **with `cohere` as the gate that the change didn't introduce drift.**
>
> An agent that rewrites its own prompts can drift into incoherence and not notice. csb computes a number (`CY`) that catches it. The third leg — *coherence-gated* change — is the differentiator.

**On the vocabulary (before the words do their work):** "belief," "evolve," and "cohere" name *mechanisms*, not agency. A `belief` is a confidence-weighted, contradiction-checked database record — not a held conviction. "Evolve" is an operation someone *runs*; csb does not act on its own. "Cohere" is a computed score (`CY`), not a felt consistency. The claim holds because the mechanism is real and inspectable — not because you project wanting or knowing onto markdown and a database. Any phrase that persuades only by implying the tool *wants* or *knows* something is wrong here — cash it out for the mechanism. *(Weizenbaum lens, /tribunal 2026-05-31.)*

---

## Layer 0 — Primitives (the instruction set)

| Primitive | Signature | Canonical site |
|---|---|---|
| `lens` | a persona file: `lens_type`, `when_to_invoke`, `signature_techniques`, `anti_patterns_called_out` | schema at `personas/README.md:14` |
| `bind` | attach lens(es) to a target; read the lens in full; *become* it before responding | `skills/tribunal/SKILL.md` Phase 2; `skills/reflect/SKILL.md` Phase 2 |
| `verdict` | a structured judgment: `{stance, confidence, dissent_axis}` | `skills/tribunal/SKILL.md` verdict schema |
| `refuse` | a *first-class* decline when preconditions aren't met — surfaced, never dropped | `personas/eliza-refusal__weizenbaum.md`; `commands/diagnose-bound.md` |
| `gate` | pass/fail on a **runnable** proof (not an opinion) | `skills/karpathy-bar/SKILL.md`; `commands/verify.md`; `commands/tdd.md` |
| `iterate` | loop a target under a wall-clock budget, keep the best version | `skills/iterate/SKILL.md` |
| `belief` | a confidence-weighted memory record (`confidence REAL DEFAULT 0.75`) | `memory-mcp/db.py:51` |
| `contradict` | detect an inversion between two beliefs that share ≥1 tag | `memory-mcp/db.py:581` |
| `cohere` | CY: quantified coherence over beliefs (+behavioral counterpart), with Wilson 95% CI | `memory-mcp/efficacy_measure.py:46` and `:183` |
| `recall` / `learn` | read / write the belief substrate | `commands/recall.md`, `commands/learn.md` |
| `checkpoint` / `resume` | serialize / restore session state across a compaction boundary | `commands/context-save.md`, `skills/resume/SKILL.md` |
| `fresh` | refresh a lens to field-current (GitHub / blog / field signal) | `commands/persona-recap.md` |

These twelve cluster into **four families**: *judgment* (`lens`, `bind`, `verdict`, `refuse`, `gate`), *optimization* (`iterate`), *substrate* (`belief`, `contradict`, `cohere`), and *memory/continuity* (`recall`/`learn`, `checkpoint`/`resume`, `fresh`). These are the words. Everything else is grammar over them.

---

## Layer 1 — Operators (compositions of primitives)

Every operator is the same skeleton:

```
operator := bind(lens+) → (verdict | refuse)+ → synthesize
```

The operators differ only in **arity** (how many lenses) and **synthesis rule** (how verdicts combine):

| Operator | = | Synthesis rule | Site |
|---|---|---|---|
| `tribunal` | `operator` | preserve disagreement (majority + dissents + unresolved residue), N lenses | `skills/tribunal/SKILL.md:34` |
| `reflect` | `operator` | three-block retrospective, 1 lens | `skills/reflect/SKILL.md:34` |
| `karpathy-bar` | `operator` | lens = quality-gate; `PASS \| PASS-WITH-NITS \| FAIL` | `skills/karpathy-bar/SKILL.md:29` |
| `iterate` | loop | keep best-at-budget; pair with a `gate` as eval to avoid Goodhart | `skills/iterate/SKILL.md` |

**Documented lineage (the language was evolving in plain sight):**
- `tribunal` *inverts* Karpathy's `llm-council`: same fan-out shape, but synthesis **preserves** disagreement instead of collapsing to one Chairman answer — `skills/tribunal/SKILL.md:12`.
- `iterate` *generalizes* Karpathy's `autoresearch`: a training-loop-to-budget retargeted to any file — `skills/iterate/SKILL.md:8`.
- `reflect` is `tribunal` at **N=1** with a three-block synthesis.

---

## Layer 2 — Workflows & instances (compositions of operators)

The key move (and the reason for *document-don't-merge*): several "separate tools" are not separate — they are **instances or compositions** of operators. They stay independently callable; this table just makes the relationship legible.

```
cv-critique  = tribunal | lens-set = {hiring, skill-match, voice, coach}   # a FROZEN-LENS INSTANCE
scan         ≈ parallel{security, quality+gaps, ops} → one report          # TERRITORY-OVERLAP w/ audit+gap-analysis, NOT a literal pipe
diagnose-bound = diagnose + refuse(preconditions)                          # a GUARDED instance
investigate  = diagnose | mode=autonomous, stop-at-proof                   # a MODE
metaprompt-toggle = metaprompt | under a UserPromptSubmit hook             # a HOOKED mode
team         = analyze → bind(fresh(lens)+ as agents) → execute(layer-strict) → gate
workflow     = operator+ over a substrate, wrapped in checkpoint/resume
```

`team` is worth reading closely: it is the only operator that composes `fresh` into `bind` — it refreshes each member's lens to field-current *before* binding, so an assembled "shadcn" or "React Native" expert reasons about the *current* API, not the training-cutoff one (`commands/persona-recap.md`, auto-invoked in `/team` Phase 0.7).

---

## Layer 3 — Self-evolution (the substrate that makes it compound)

```
self-evolve := (learn | fresh)*  with  cohere  as the gate that evolution didn't drift
```

The substrate primitives that close the loop:
- `belief` + `contradict` → `cohere`: as beliefs accrue, `CY` measures whether they stay consistent. `db.py:581` runs a *live* contradiction detector (defeats the "empty the table to score 1.0" gaming attack); `efficacy_measure.py:46` folds contradiction-rate, unresolved-drift, and mean-confidence into one number with a Wilson CI.
- behavioral counterpart: `feedback_violations.py` extracts imperative rules from past corrections and checks whether the current session is about to break one — `efficacy_measure.py:183` turns that into a behavioral CY.

This is what "self-evolving" *means* here, precisely: not "mutates its own prompts," but "accumulates beliefs and refreshes lenses while a coherence metric watches for drift." See `docs/SUBSTRATE-HEALTH.md` for the honest current state of each piece (some are live, some are designed-but-dormant — this doc describes the architecture, that doc describes what's wired today).

---

## How to read a new command

When you meet a csb command, ask three questions:
1. **Which primitives does it bind?** (lens? gate? belief?)
2. **What's its arity and synthesis rule?** (1 lens or N? preserve disagreement or collapse?)
3. **Does it touch the substrate?** (does it `learn`/`recall`/`cohere`, or is it stateless?)

Answer those and you've understood it — without reading 200 lines of prose. That is the whole point of having a grammar.

---

*Provenance: this grammar was extracted by a three-agent audit of the live codebase (2026-05-31). Every `file:line` was cited from that audit. Re-verify with `/karpathy-bar docs/GRAMMAR.md` before publishing — the gate requires every claim to have a runnable anchor.*
