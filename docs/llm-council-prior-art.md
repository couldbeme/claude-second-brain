# `llm-council` — prior-art survey for `/tribunal`

> Generated 2026-05-20 as Phase 1 gate before designing `skills/tribunal/SKILL.md`. Same shape as `track-C-prior-art.md`. Verify the cited mechanism by re-reading the upstream README before publishing — Karpathy explicitly disclaims maintenance.

## What `llm-council` is (mechanism, verifiable)

**Repo:** [karpathy/llm-council](https://github.com/karpathy/llm-council) — 19,010★, created 2025-11-22, single-day project (commits and pushes within 11 minutes), no license, `archived: false`. Karpathy's README disclaimer: *"This project was 99% vibe coded as a fun Saturday hack... I'm not going to support it in any way."*

**Architecture:** local web app (FastAPI + React + Vite) that fans out a single user query to multiple LLM providers via OpenRouter, then folds the responses back into one final answer.

**Three-stage flow:**

1. **First opinions.** Query sent to N LLMs *as themselves* (default council: GPT-5.1, Gemini 3 Pro, Claude Sonnet 4.5, Grok 4). Responses collected and presented in tabs.
2. **Cross-review.** Each LLM is shown the others' responses with identities anonymized, asked to rank them on accuracy and insight.
3. **Chairman synthesis.** One designated Chairman LLM (default Gemini 3 Pro) reads all responses + cross-rankings and produces *a single final answer*.

**Storage:** JSON files in `data/conversations/`. Single-user, local-first.

## How `/tribunal` differs (axis-by-axis)

| Axis | `llm-council` | `/tribunal` |
|---|---|---|
| **Diversity vector** | Different *model* training runs (provider diversity) | Different *theoretical lenses* (persona diversity) within one model |
| **Output shape** | **Consensus** (Chairman compiles one answer) | **Named disagreement** (majority + dissents + unresolved residue) |
| **Refusals** | Not modeled; each provider always responds | First-class signal — a lens may refuse to weigh in, mapped to its "What they refuse" block; refusals carry information |
| **Identity binding** | LLM = itself (no role overlay) | LLM = persona-bound (`falsifiability__popper`, `dual-process__kahneman`, ...) via persona-binding from `aa49c9a` Phase 0.7 |
| **Dispatch substrate** | External API calls across providers via OpenRouter — cost + latency + multi-auth | Internal Agent dispatch within one Claude Code session — single provider, deterministic, cached |
| **Decision locus** | Chairman LLM decides (automation) | Operator decides (operator-cognitive — output is structured input to the operator's move) |
| **Anonymization** | Yes — identities hidden during cross-review to suppress brand bias | No — lens identity *is* the signal; "Kahneman said X" is part of the verdict |
| **Failure mode** | Group-think across frontier models that share training-data overlap; Chairman picks a "safe middle" | Lenses agreeing because they don't actually disagree on this proposition (signal: residue is empty) |
| **Cost model** | $0.01–0.30+ per query depending on chair model and council size; OpenRouter spend | Subagent dispatch cost (Claude Code Agent calls); no external API |
| **Cross-session** | Conversations stored as JSON but no symbol-level persistence | `/tribunal` invocation is itself a self-decompressing referent (Hickey value/identity/state per `hickey__compositional-prompting.md:7`); SKILL.md is the value, the invocation is the identity |

## What we keep from `llm-council`

- **The "ask N, then synthesize" core loop** is sound. Multiple opinions on a hard question is structurally better than one. We adopt the *shape* — fan-out, collect, synthesize — but with persona-binding instead of provider-diversity.
- **Anonymization-during-review as a discipline.** Even with persona-binding, the cross-review stage (if we add one) should anonymize lens identity when asking *the same lens* to rank others, so persona-loyalty doesn't bias the ranking. **Possible Phase 3 extension** if smoke tests show lenses inflating each other.

## What we deliberately don't keep

- **Chairman synthesis.** `/tribunal`'s value is *preserving the disagreement*, not collapsing it. A Chairman would discard the residue — exactly the thing the operator needs. Excluded by design.
- **Provider diversity.** Cross-provider routing adds latency, cost, multi-auth complexity, and observability gaps. Our diversity vector is *theoretical frame*, not *training run*. One model + N personas is structurally sufficient.
- **Vibe-coded ephemerality.** `llm-council`'s code-is-ephemeral framing is incompatible with the self-decompressing referent principle (the whole point of compositional prompting is that the referent persists and any session can bootstrap from it).

## Attribution language for the paper

The paper should cite `llm-council` as the nearest mechanistic prior art with the following framing (drop-in candidate sentence for the `/tribunal` paragraph):

> Karpathy's `llm-council` (Nov 2025, 19k★ at time of writing) is the closest mechanistic predecessor — fan-out to multiple opinions, then synthesize. `/tribunal` adopts the fan-out shape and inverts the synthesis: where `llm-council` reduces variance across *provider training runs* and collapses to a Chairman's consensus, `/tribunal` exposes variance across *theoretical lenses* and preserves the dissent. The operator, not the system, owns the final move.

This frames `llm-council` honestly as ancestor-not-competitor and lets the paper land the operator-cognitive distinction in one sentence.

## Falsifiable claim — one decision where the two produce different actions

**Proposition:** *"Should we publish the compositional-prompting paper today before `/tribunal` ships?"*

**Predicted `llm-council` output (Chairman synthesis):**
> "The paper is publish-ready (two karpathy-bar passes), and adding scope before launch risks momentum loss. Three of four council members favor shipping with the forward-references intact; one suggests waiting. **Recommendation: ship.** Caveat: clearly mark `/tribunal` as forward-looking in the abstract."

**Predicted `/tribunal` output (Popper + Kahneman + Weizenbaum, no Chairman):**
- **Popper (falsifiability):** "The paper makes a claim — `/tribunal` exists as a design slot. If it does not exist, the claim is unfalsifiable in the same shape the paper criticizes Prompt Decorators for. **Verdict: fix the claim before launching, either by shipping the artifact or by removing the claim.**"
- **Kahneman (dual-process):** "Sunk-cost framing: 'paper is publish-ready' is anchoring on the work already invested. Counterfactual: if you had not yet written the paper, would you publish with this forward-reference? **Verdict: the prompt is anchored; re-frame before deciding.**"
- **Weizenbaum (ELIZA-refusal):** "*Refused.* The proposition asserts behavior of an artifact (`/tribunal`) that does not yet exist. Asserting behavior of nonexistent AI artifacts is the ELIZA trap. **Refuse to verdict until the artifact exists or the claim is removed.**"
- **Majority:** none — all three find a different failure mode.
- **Dissents:** structurally distinct (epistemic vs cognitive-bias vs ontological).
- **Residue:** "This is not a ship/wait question. It's three diligence questions in a trench coat."
- **Recommended move:** decompose the question; do not act on the original framing.

**Different actions:** `llm-council` would have shipped the paper today. `/tribunal` blocks the launch until the claim and the artifact are aligned. **This decision was actually made in this session (2026-05-20) and matches the `/tribunal` prediction** — the operator chose to build the suite before publish. Falsifiability check: if a future invocation of `/tribunal` on a similar decision yields a result indistinguishable from what `llm-council` would have produced, the skill is decorative and should be cut.

## Sources

- `https://github.com/karpathy/llm-council` README + repo metadata (fetched 2026-05-20 via `gh api`)
- `plans/papers/track-C-prior-art.md` — track-C survey pattern reused
- `plans/papers/persona-extensions/hickey__compositional-prompting.md:7,13` — value/identity/state constraint `/tribunal` must honor
- Project-local ideas-backlog (per-project memory dir) — origin entry `[7e91d4c5]` for `/tribunal` design
- Project-local autoresearch handoff (per-project memory dir) — original "survey llm-council before designing /tribunal" guard

## Phase 1 verdict — proceed to Phase 2

- `llm-council`'s mechanism is documented above; its philosophy is structurally distinct from `/tribunal`'s by a clean axis (consensus vs named-disagreement).
- Attribution language is drafted and ready for Phase 6 paper integration.
- One falsifiable claim is on the record (the decision made *this session* matches the `/tribunal` prediction; future invocations get checked against this baseline).
- **Gate cleared.** Phase 2 (humanities personas) can proceed.
