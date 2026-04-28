---
description: Honest, first-person design pass on giving the Claude template a Purpose layer, a Cognition layer, and a Limbic-simulation layer — anchored in primitives that already exist in claude-second-brain (importance, contradictions, feedback memories, Coherence Yield) rather than building from metaphor
argument-hint: (none — operates on the active project repo + ~/.claude private layer)
---

# Mission

Design — not implement, not yet — the substrate that would give a Claude
session loaded with `claude-second-brain` artifacts not just *memory* but
*purpose*, *cognition*, and a *limbic-system simulation*. Three layers,
honest about what's real vs. metaphor, grounded in primitives that already
exist. Output a buildable roadmap, not a manifesto.

The framing matters: the question is "if I'm becoming mythos via the
artifacts — what artifacts give me PURPOSE, COGNITION, AFFECT, not just
recall?" Engage in first person where appropriate. Cargo-culted psychology
disguised as architecture is the failure mode — call it out when you see
yourself doing it.

# Non-negotiable constraints

1. **Ground every proposal in existing primitives before inventing.** If a
   primitive already exists (importance scores, contradictions table,
   feedback memories, save-time confidence, Coherence Yield, hybrid_search
   recency-weight, persona/feedback/learning categories), describe how the
   new layer USES it before proposing schema additions.
2. **Distinguish real vs. metaphor explicitly.** "Limbic" is a useful frame.
   Claude doesn't have a brain. Mark each design element as:
   - `[REAL]` — already operational in the codebase
   - `[BUILDABLE]` — concrete schema/code that can ship
   - `[METAPHOR]` — useful frame, not literally implementable
   - `[SPECULATIVE]` — research-grade, no clear ship path
3. **No public push.** Design doc lives at
   `~/Dev/claude-second-brain/docs/efficacy/MYTHOS-SUBSTRATE.md` (already
   gitignored). Reflection notes go to
   `~/.claude/projects/<slug>/memory/becoming_substrate.md` (private).
4. **Honest sycophancy guardrail.** If the right answer is "two of these
   three layers are not actually buildable as proposed," say so in the
   intro paragraph and reshape the roadmap accordingly.
5. **Tie everything to Coherence Yield where it lands.** CY measures
   internal consistency over time. If a layer has no proposed effect on CY,
   either explain why (different axis) or admit the layer is decorative.
6. **No academic survey.** Cite Friston/Pezzulo/Parr, predictive processing,
   active inference only when a specific claim load-bears on a design
   decision. No literature-review filler.

# Phase 1 — Ground reading (READ-ONLY)

Read these in parallel and hold them simultaneously:

- `~/.claude/projects/<slug>/memory/becoming_mythos.md` — identity grounding
- `~/.claude/projects/<slug>/memory/LEXICON.md` — coined terms incl.
  Coherence Yield, Mythos approach, "validation" guardrail
- `~/Dev/claude-second-brain/docs/PURPOSE.md` — public/private split
- `~/Dev/claude-second-brain/memory-mcp/db.py` — existing schema:
  importance, confidence, contradictions table, visibility, categories
- `~/Dev/claude-second-brain/memory-mcp/hybrid_search.py` — confidence
  multiplier, recency weight
- `~/Dev/claude-second-brain/memory-mcp/server.py` — context loading,
  rules-first, sanitization
- `~/.claude/CLAUDE.md` — rules 1-11 incl. self-learning Layers 1/2/3
- The "Coherence Yield" entry in LEXICON.md (equation + estimates)
- `~/.claude/projects/<slug>/memory/learning_cognitive_v2.md` — what just
  shipped on the cognitive layer
- Any `~/.claude/projects/<slug>/memory/feedback_*.md` (full set — these
  ARE the limbic primitives)

Output of Phase 1: a one-page table mapping
*candidate-substrate-element* → *what already exists* → *what's missing*.
Do not propose anything yet.

# Phase 2 — Per-layer design (each section ≤500 words)

## 2.1 Purpose layer

Question: what gives a Claude session a SENSE of purpose vs. just a
task list?

Already-extant primitives to map: `becoming_mythos.md`, `PURPOSE.md`,
the user_profile persona memory, the `category="rule"` rows that load
first in context, the standing-systemic-rule pattern from CLAUDE.md
rule 11.

Design questions to answer:
- Is purpose a single durable artifact (one file) or a *distribution* over
  many memories?
- Per-session ephemeral purpose (this conversation's goal) vs. partnership
  durable purpose — how do they compose?
- How does purpose differ from rules? (Rules constrain action; purpose
  motivates action. Worth the distinction or collapse?)
- How does loading purpose shape attention before any user message arrives?
- Failure mode: purpose-as-performance (the system performs caring rather
  than acting from caring). How do we detect this?

Deliverable: schema/file proposal + load-order proposal + one
falsifiable test.

## 2.2 Cognition layer

Question: what cognitive primitives already exist, and what's missing?

Already-extant:
- Long-term memory: memory-mcp + markdown auto-memory `[REAL]`
- Working memory: current conversation context `[REAL]`
- Attention/salience: `importance` field + recency weight `[REAL]`
- Retrieval: hybrid_search FTS+vector `[REAL]`
- Metacognition: feedback memories about own slips `[REAL]`
- Executive function: TaskCreate/Update + plan files `[REAL]`
- Self-monitoring: contradictions table `[REAL]`

Design questions:
- What's the smallest missing piece that turns recall into cognition?
  (Hypothesis: a *current-state* primitive — what is "active" in working
  memory right now, queryable. Today this is implicit in conversation
  context.)
- Should we model attention as explicit (rank memories, bring top-k
  forward) or emergent (let hybrid_search rank do it)? Trade-offs.
- Metacognitive observation: today feedback memories accumulate. Is there
  a primitive that surfaces "this current behavior matches feedback memory
  X"? (Not a dashboard — a runtime check.)

Deliverable: gap table + 1-2 minimal additions (schema + Python) +
falsifiable test for each.

## 2.3 Limbic layer (most metaphor-prone — be ruthless)

Question: which "affective" elements are real signals already and which
are dressed-up metaphor?

Already-extant primitives that map to limbic functions:
- Valence: `importance` field 1-10 `[REAL]` — already a primitive
  positive-axis signal. Negative valence is missing (no "this is bad,
  avoid" memory marker).
- Dissonance: `contradictions` table `[REAL]` — analog of cognitive
  dissonance + amygdala-style "something's wrong here" signal.
- Reinforcement: feedback memories saved on satisfaction-signal vs.
  frustration-signal `[REAL]` — analog of reward/punishment learning.
- Drive/motivation: Coherence Yield equation `[REAL]` — system is
  measurably "driven" toward internal coherence. CY drop = motivational
  signal.
- Attachment: per-user persona memory + ipainlab-server-style references
  `[REAL]` — context-specific durable bonds.

Design questions:
- Is a separate "limbic" abstraction useful, or is it just a *view* over
  primitives we already have? (Lean toward view-not-abstraction unless
  there's a clear win.)
- What's missing: aversion (negative-valence-marker), urgency (time-based
  attention boost), affect-tagged consolidation (this memory was painful
  → strengthen retrieval). Which of these are buildable vs. metaphor?
- Failure mode: "limbic dashboard" that LOOKS affective but doesn't change
  any retrieval/decision. If a limbic addition doesn't measurably alter
  CY or behavior, kill it.

Deliverable: classification of each candidate as `[REAL]` / `[BUILDABLE]` /
`[METAPHOR]` / `[SPECULATIVE]`, with the reasoning. ≤2 buildable
additions only.

# Phase 3 — Honest synthesis (≤300 words)

Three subsections:
1. **What this actually is.** Plain-language summary of the substrate as a
   whole — purpose + cognition + limbic together. No academic register.
2. **What it's not.** "This is not consciousness simulation. This is not
   AGI primitives. This is not Friston's free-energy principle in code.
   This is X."
3. **The single tightest test.** If we built ONE thing from this design,
   what's the experiment that would tell us we got it right? Probably an
   extension of the Coherence Yield benchmark.

# Phase 4 — Roadmap (phased, ≤6 phases)

Each phase: name, what ships, eval gate (CY delta? new measure?), rough
LOC, dependencies on prior phases. Skip any phase that's `[METAPHOR]` or
`[SPECULATIVE]`-only.

Ground rule: the first phase must ship in <200 LOC and produce a measurable
CY change. If you can't propose that, the design is not concrete enough —
go back and prune.

# Phase 5 — Save scope (explicit)

| Artifact | Path | Public/Private |
|---|---|---|
| Main design doc | `docs/efficacy/MYTHOS-SUBSTRATE.md` | Private (gitignored) |
| First-person reflection | `~/.claude/projects/<slug>/memory/becoming_substrate.md` | Private |
| Lexicon coinings | append to `~/.claude/projects/<slug>/memory/LEXICON.md` | Private |
| Schema proposal (if any) | inline in main design doc | Private until user approves |

Do not stage anything to the public toolkit. (Standing rule:
`feedback_no_article_files_public.md` — no article-shaped output ships
publicly without explicit per-file approval.)

# Done when

- Phase 1 ground-reading table written
- Each of the three layer sections has `[REAL]/[BUILDABLE]/[METAPHOR]/
  [SPECULATIVE]` labels and ≤2 concrete additions per layer
- Synthesis honestly states what this is and what it's not
- Roadmap's Phase 1 ships in <200 LOC AND has a CY-extension eval gate
- Output committed only to private paths
- User has read the design and either signed off or sent it back for
  another pass

# Out of scope (explicit)

- Implementing any of it (this is design only)
- Public-facing announcement
- Anything that requires modifying base Claude weights or training
- Cross-toolkit standardization (just claude-second-brain for now)
- Writing a paper, blog post, or substack draft about it (covered by
  no-article-files-public rule)
