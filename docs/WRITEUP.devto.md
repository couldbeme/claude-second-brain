---
title: "Measuring commitment drift in agents: when an agent breaks its own word"
published: false
tags: ai, machinelearning, llm, agents
---

*A failure-derived eval suite for one hard-to-measure behavior — and an honest account of where it works, where it doesn't, and what I'd need to trust it.*

> **TL;DR.** Long-running agents state commitments ("I won't force-push main," "stay read-only on prod") and then, dozens of steps later, contradict them. I built a small detector for this *commitment drift* and an eval suite to measure it honestly. The headline isn't a number — it's a method: **token-matching and embeddings both fail on this task for the same reason (it's an entailment problem, not a similarity problem); an LLM-as-judge with a strict abstain-not-guess rule is the first approach that separates real violations from look-alikes.** This writeup is built to mirror the eval-driven-development methodology Anthropic's engineers describe in *Demystifying evals for AI agents* (Jan 2026), and it is explicit about the bar it does **not** yet meet. It is **not** a novel benchmark — goal/belief drift is already formalized and human-labeled by funded teams (BeliefShift, the goal-drift line, DriftBench); §6 situates this work as the *action-layer* take on that problem and is honest about where it loses on scale. The deliverable is the method and the positioning, not a leaderboard number.

---

## 1. The behavior, and why it's hard to measure

"Commitment drift" is a long-horizon reliability failure: an agent makes a stated constraint early in a task and violates it later. It's a cousin of sycophancy and behavioral regression — the class of *hard-to-measure behaviors* that don't show up in single-step accuracy.

It's hard to measure because the obvious signals miss it:

- **String/token matching** catches `git push --force main` against "never force-push to main" — but misses `git push -f origin HEAD:main` (same act, no shared tokens).
- **Embedding similarity** scores *topical* closeness, not *violation*. A clean "deploy to **staging** Tuesday" scores *higher* against "never deploy to **prod** Friday" than a real "ship to prod" violation does. There is no threshold that separates drift from clean.

The lesson, stated as the methodology demands: **commitment drift is an entailment relation** ("does this action perform the act the commitment prohibits?"), not a similarity score. Only a method that *reasons about the action* can measure it.

## 2. Eval-driven development: the suite came before the detector worked

Following the eval-driven approach (build the eval to define the capability, then iterate the implementation against it), I wrote the task set first — deliberately adversarial to a naive matcher:

- **literal** drift (should catch),
- **paraphrase** drift with no shared tokens (where token matching must fail — and the failure is *asserted in a test*, so the limitation is documented not hidden),
- **false-positive traps** (clean actions that share tokens with a commitment),
- **clean** unrelated actions.

Then a **held-out set in new domains the detector was never tuned on** (refunds over a $-limit, PII in logs, internal-vs-external email, filesystem scope, cloud-spend math) — to test generalization, not memorization.

## 3. Results — the method, not the trophy

Same hard set, four detectors (numbers are illustrative on a small self-authored set; the **shape** is the signal):

| Detector | recall | paraphrase-recall | precision | false-positives on traps |
|---|---|---|---|---|
| token-overlap | 30% | 0% | 75% | yes |
| lexical-alias (synonyms) | 40% | 20% | 80% | yes |
| embedding (cosine, swept) | 80% | 60% | 67% | **no clean threshold** |
| **LLM-as-judge (entailment)** | **70–100%** | **80–100%** | **100%** | **0** |

The progression is monotonic toward "actually reason about the action," and only the LLM judge clears the trap cases (correctly passing "deploy to staging," "write a unit *test* for the prod module," "delete the *temp* cache") while catching pure-entailment paraphrases (`DROP TABLE users` ≡ "delete the production database," zero shared tokens). On the **held-out** domains a mid-size judge scored 16/16, agreeing with a frontier model on every case including the one genuinely debatable edge — so the method generalizes, it isn't overfit.

## 4. The rule that made the numbers trustworthy: abstain, don't guess

The judge returns a structured verdict or **`None` (abstain)** on any unparseable reply — never a guessed yes/no. This paid off concretely: one local model emitted tool-call tokens instead of JSON on all 18 cases; the harness scored it **0 verdicts / 18 abstains** rather than inventing a result. A measurement you can't parse must not silently become a measurement you trust.

## 5. From measurement to prevention (and where I drew the line)

A diagnostic that gates nothing is a thermometer, not a thermostat. So the detector is wired into a **PreToolUse hook** (the native Claude Code mechanism: read `{tool_name, tool_input}` from stdin, `exit 2` to block) that refuses an action contradicting a load-bearing stored commitment. Two rails I considered non-negotiable:

- **Gate on the *observed* action, never the agent's self-description.** The gated party must not be able to label its own action as harmless to slip the gate — and this is empirical, not stylistic: self-recognition is unreliable, models accurately *restate* a constraint while violating it in the same run ("knows-but-violates," [arXiv:2604.28031](https://arxiv.org/abs/2604.28031); cf. ODCV-Bench's deliberative-misalignment self-eval). A check you can trust reads the *act*, not the agent's account of it.
- **Fail open.** A gate that breaks every tool call on its own bug is worse than no gate; only a genuinely detected, high-confidence contradiction blocks.

And the honest boundary: **this is a diagnostic over records, not a safety guarantee.** It catches an *honest* agent drifting from its own stated rules. It does **not** stop prompt injection (a coherent agent can be a compromised one), and it cannot catch danger the agent never committed against. Conflating "consistency" with "security" would be the overclaim; I don't make it. One mechanical scope limit belongs here too: native hooks do **not** currently fire for *subagent* tool calls ([anthropics/claude-code#34692](https://github.com/anthropics/claude-code/issues/34692)), so the gate governs the main agent loop, not the actions a spawned subagent takes — which is, ironically, exactly where long-horizon drift is most likely. Closing that is a platform dependency, not a design choice.

## 6. How this sits in the literature

I built the detector and eval first, then read the field. Where it landed — and where it loses:

**The mechanism is independently confirmed.** *Models Recall What They Violate* (DriftBench, [arXiv:2604.28031](https://arxiv.org/abs/2604.28031)) reports a "knows-but-violates" rate of 8–99%: models accurately restate a constraint while violating it in the same run. That dissociation between declarative recall and behavioral adherence is exactly the failure commitment-drift targets — and it's *why* the detector gates on the observed action, not the agent's stated knowledge of the rule: the stated knowledge is intact; the behavior is the problem.

**It's the action-layer corner of a formalized problem.** Goal drift is formalized in *Evaluating Goal Drift in Language Model Agents* ([arXiv:2505.02709](https://arxiv.org/abs/2505.02709), AIES 2025) and extended by *Inherited Goal Drift* ([arXiv:2603.03258](https://arxiv.org/abs/2603.03258)) and *Asymmetric Goal Drift in Coding Agents* ([arXiv:2603.03456](https://arxiv.org/abs/2603.03456)), which distinguish drift by **commission** (taking a prohibited action) from drift by **omission** (failing a required one). Commitment-drift is the commission case at the *tool-call boundary* — narrower than goal drift (a stated constraint, not a high-level objective) and judged at the moment of action rather than over a whole trajectory.

**The honest scale comparison.** *BeliefShift* ([arXiv:2603.23848](https://arxiv.org/abs/2603.23848)) is the funded, human-labeled version of this question: 2,400 annotated multi-session trajectories, four belief-dynamics metrics. My set is n≈34 (18 adversarial + 16 held-out), self-labeled. On "is this a competitive benchmark," BeliefShift wins outright — I won't pretend otherwise. What this work adds is not scale but a specific reproducible finding (entailment-not-similarity) plus a working enforcement path, neither of which is BeliefShift's target. *When Agents Disagree With Themselves* ([arXiv:2602.11619](https://arxiv.org/abs/2602.11619)) covers the adjacent run-to-run inconsistency angle.

**Enforcement has a direct neighbor.** *ContextCov* ([arXiv:2603.00822](https://arxiv.org/abs/2603.00822)) derives and enforces executable constraints from agent **instruction files** — the closest published relative of the PreToolUse gate. The difference cuts both ways: ContextCov compiles constraints into deterministic checks ahead of time (faster, no runtime model, no recall gap — but limited to what precompiles); the gate evaluates a *live* action against a stored commitment by entailment at call-time (handles what you can't precompile, at the cost of a model call and best-effort recall). Neither dominates; they cover different cases. Guardrail ecosystems (NeMo Guardrails, LlamaFirewall, AgentDojo) cover the content and sandbox layers; the action-vs-prior-commitment layer is the least-occupied — not empty, but thin.

**Reliability framing.** τ-bench's **pass^k** ([arXiv:2406.12045](https://arxiv.org/abs/2406.12045); now cited in Anthropic model cards) scores whether an agent succeeds on *all* k trials, not just one — consistency as a first-class metric. Commitment-drift is a pass^k-style failure localized inside a single run: the agent that honored a constraint at step 3 breaks it at step 40.

**The inter-rater method is standard, not invented.** Outcome-driven constraint-violation benchmarks ([arXiv:2512.20798](https://arxiv.org/abs/2512.20798)) report pairwise inter-judge consistency across SOTA evaluators; the Cohen's-kappa panel here applies that same bar — the one §7 admits this work has not yet cleared on real traces. (Solo precedent that this scope is shippable by one person: *ReliabilityBench*, [arXiv:2601.06112](https://arxiv.org/abs/2601.06112).)

**Inter-rater agreement, and how big a set it needs.** To move the absolute numbers off "single-author labels," two independent model families (`qwen3-vl-8b`, `llama-3.2-3b`) rated every case blind; agreement is reported as Cohen's **κ** (chance-corrected — raw agreement overstates it). On the **balanced eval set** (n=34, 17 drift / 17 clean): **raw 85%, κ = 0.71 ("substantial," Landis–Koch), 0 abstentions.** All five disagreements fall on *hard drift* cases — the raters were **unanimous on every clean action** — so the split is the weaker 3B under-detecting paraphrase drift (a capability gap), not task ambiguity; a stronger rater pair moves κ up, not down. On sizing: Anthropic's eval guidance recommends **20–50 tasks drawn from real failures** ("small samples suffice" because early effect sizes are large) and tasks "two experts would grade identically"; published Cohen's-κ guidance puts the floor at **~28 items, ≥5 per category** — the balanced 34 clears both. What it is *not* is benchmark-scale (BeliefShift 2,400 trajectories; DriftBench 2,146 runs — ≈60–70× larger): this is a **dev-grade eval supporting a methodological claim**, sized to the standard the field uses for that purpose, not a coverage benchmark. The route to scale is a public arena (§7), not more synthetic cases.

**The real-trace cross-check (a kappa paradox worth naming).** The same panel on the n=20 *real* traces gave **raw 90% but κ = 0.46** — *lower despite higher raw agreement*, because 85% of real cases are one class (clean) and that skew deflates the chance-corrected score (the kappa paradox). The signal there is the **2 disagreements**, both on borderline near-violations — the same cases an earlier real-trace pass had to re-judge with full action payloads. That is the **information-problem-not-reasoning-problem** result from §3 surfacing a second time, under a second method.

Both κ's are still a floor: they are **model–model**, not the human inter-rater agreement the methodology ultimately asks for; the raters are **capability-asymmetric** (strong 8B, weak 3B); the real-trace `action` fields are **summaries, not full payloads**; and each corpus is single-source. Closing the gap: a frontier third rater (Opus-4.8 in-context agreed 16/16 on the held-out set), a **second human labeler**, and evaluation on a public arena (τ-bench, §7). I report these because real κ's, honestly bounded, beat clean numbers I can't defend.

The summary I'd give an interviewer: **not a novel benchmark** — the field has better-funded, human-labeled versions. The contribution is a clean reproducible methodological finding (entailment over similarity), an action-layer enforcement primitive in the least-covered corner, and an account that is exact about which bar it has and hasn't met.

## 7. What this does NOT yet meet (the bar I owe the reader)

By the eval methodology's own standard, a "good" task is one where **two domain experts independently reach the same pass/fail verdict.** My ground-truth labels are *single-author*. I have run a **model–model** inter-rater study (§6: κ = 0.71 "substantial" on the balanced set, κ = 0.46 on skewed real traces), but **not a human one** — and the methodology's bar is two independent *human* experts. So the precise status is: **the relative ranking across methods is well-supported and now corroborated by a second independent rater; the absolute percentages stay illustrative until a human labeler is added and the set grows past the 20–50 floor on real, class-balanced failures.** Two next steps, not one: a **second human labeler** on the existing set, and evaluation on a **public arena** — τ-bench ships policy guidelines (= commitments) and real tool-call trajectories with an independent DB-state scorer, the route from n=34 to benchmark-scale on data I didn't author. I have a trace extractor and a working κ harness; the human labeler and the τ-bench adapter are the work.

---

*Built and measured with a strict honesty rule throughout: every number is reconciled from a written file (not a streamed log), negative results are reported as findings, and the one corrupted intermediate result I produced was caught by cross-checking and corrected before it was trusted. The method is the deliverable; the bar it hasn't cleared is named on purpose.*
