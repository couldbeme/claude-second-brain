---
description: Modify-one-file under a wall-clock budget — single-agent loop edits target_file, runs eval_command, keeps the best version. Karpathy `autoresearch` shape retargeted for prose-agent and code-agent work. Output is best version at T+budget, not "the answer."
argument-hint: <target_file> --eval=<command> --budget=<Nmin> [--keep=N]
---

# /iterate — Modify-one-file under wall-clock budget

Single-agent narrow-optimization loop. Edit ONE file, run an eval, score, keep the best version, repeat until the budget is exhausted. The output is the best version at T+budget plus a diff log of the attempts. Adapted from [karpathy/autoresearch](https://github.com/karpathy/autoresearch) — 82k★ as of 2026-05-20, designed for ML training-loop automation; this skill generalizes the pattern to any single-file optimization.

The driving question: *given a fixed budget, what is the best version of this one file the agent can produce against this eval?*

## How it differs from `/tribunal` and `/team`

- `/tribunal` is multi-lens *decision* on a proposition; output is structured disagreement.
- `/team` is multi-agent *deliberation* with role-bound perspectives; output is synthesis.
- `/iterate` is single-agent *optimization*; output is the best version of one file at the budget boundary.

Same family (operator-bound work primitives); different shape.

## Inputs

- **`target_file`** (required) — path to one file. Hard refusal if the path is a directory or a glob; this skill is single-file by design.
- **`--eval=<command>`** (required) — shell command that scores the file. Must return one of:
  - **Numeric score on stdout** (lower is better by default; flag `--higher-better` to invert) — e.g. `wc -l`, a benchmark
  - **Exit code** (0 = pass; nonzero = fail) — e.g. `pytest`, `ruff check`, `bash -n`
  - **`PASS` / `FAIL` on last line of stdout** — e.g. `/karpathy-bar` output
  Hard refusal if the eval does not produce a parseable signal.
- **`--budget=<Nmin>`** (required) — wall-clock cap in minutes. The budget IS the spec; the budget terminates the loop unconditionally. Min: 1. Max: 60. (Beyond 60 the agent typically over-fits; if you need more, run two budgets.)
- **`--keep=N`** (optional, default 3) — number of historical best versions to retain in the diff log. Older attempts are dropped.

## Workflow

### Phase 1 — Pre-flight (must pass before loop starts)

1. **Resolve target_file.** Must exist, must be a regular file, must be readable + writable. Hard refusal otherwise.
2. **Test the eval.** Run `--eval` against the *unmodified* `target_file`. Capture the baseline score / pass-fail. If the eval does not return a parseable signal, refuse with the captured output so the operator can fix the eval command before re-running.
3. **Snapshot baseline.** Save the unmodified `target_file` content + baseline score as `iteration-0` in the in-memory log. The baseline is the floor; no iteration is kept that scores worse than baseline.
4. **Confirm budget reasonable.** If `--budget=Nmin` is less than the time the baseline eval took × 3, refuse — there isn't budget for at least 3 iterations.
5. **Print the loop plan.** One line: `target=<file> | eval=<cmd> | budget=<N>min | baseline=<score-or-PASS/FAIL>`.

### Phase 2 — The loop

While `(elapsed_wall_clock < budget)`:

1. **Read the current best version** of `target_file` (initially = baseline; updated as the loop finds improvements).
2. **Propose ONE edit.** A single coherent change — not a sweep across the file. Examples:
   - For prose: tighten one section that scored lowest on `/karpathy-bar`
   - For code: replace one function with a simpler implementation
   - For configs: change one parameter the eval suggests is suboptimal
   The edit must be *named explicitly* in the iteration log (e.g. `"tightened the prior-art section by collapsing the two AutoGen paragraphs"`).
3. **Write the edit** to `target_file` (the live file, not a copy — `/iterate` is destructive; if the operator wants safety they should branch first).
4. **Run the eval.** Capture score + exit code + stdout.
5. **Compare to current best.**
   - Score improved (or PASS where baseline was FAIL) → update current best; log as `iteration-N-KEPT`
   - Score equal or worse → revert `target_file` to current best content; log as `iteration-N-REJECTED` with the reason
6. **Rotate the diff log.** Keep at most `--keep=N` historical bests + the most recent rejection.
7. **Check elapsed wall clock.** If `elapsed >= budget`, exit the loop on the current iteration boundary.

The loop does NOT continue after a `PASS` from a binary-eval — once the eval returns PASS, the file is in spec and the work is done. Continuing wastes budget on already-acceptable output.

### Phase 3 — Output

After the loop exits, output in this exact shape:

```
## /iterate result — target=<file>

### Baseline (iteration-0)
- Score: <baseline-score-or-PASS/FAIL>
- Elapsed: 0 min

### Final (iteration-<N>)
- Score: <final-score-or-PASS/FAIL>
- Improvement vs baseline: <delta-or-FAIL→PASS-or-no-change>
- Elapsed: <N> min of <budget> min

### Best-version diff (baseline → final)
```diff
<unified diff between iteration-0 and final>
```

### Iteration log (kept in chronological order)
| # | Verdict | Score | Reason / Change |
|---|---|---|---|
| 0 | baseline | <s> | <baseline> |
| 1 | KEPT | <s> | <one-line description of the edit> |
| 2 | REJECTED | <s> | <why this attempt scored worse> |
| ... | ... | ... | ... |

### Honest assessment
<one paragraph:
- Did the final beat the baseline? By how much?
- Was the improvement saturating (last 30% of budget yielded < 10% of total improvement)?
- Did the agent likely Goodhart the metric (improved the score in a way that doesn't reflect real quality)?
- Recommended next move: ship the final, re-run with a different eval, run a second budget, or accept that baseline was already optimal.>
```

## Failure modes

| Symptom | Diagnosis | Operator move |
|---|---|---|
| All iterations rejected, final = baseline | Baseline was already optimal for this eval, OR the agent could not find any improvement direction | Re-run with a different eval; or accept baseline; or change `target_file` |
| Score improves every iteration without saturating | Budget was probably too small | Re-run with `2× budget` and compare final scores |
| Score saturates in the first 20% of budget | Budget was wastefully large | Future invocations on similar tasks can use 20% the budget |
| Final passes binary eval but a human re-read says it got worse | **Goodharting** — eval did not capture the real quality | The eval was wrong, not the loop; pick a stricter eval (e.g. `/karpathy-bar` instead of `bash -n`) |
| Loop edited a section unrelated to the eval signal | Eval is too coarse to direct the loop | Tighten the eval; this is the engineer's responsibility, not the skill's |
| `target_file` is a binary / image / SQLite db | Skill refuses — `/iterate` is for text files | Different skill required |

## When to use

- Tightening prose that has a measurable quality eval (e.g. `/karpathy-bar` on a paper paragraph)
- Optimizing one config / one function against a clear metric (latency, memory, line-count)
- Refining a SKILL.md against a binary "passes self-review" gate
- Time-boxed exploration where the operator wants to know "what's the best version achievable in N min?"

## When NOT to use

- Multi-file refactors — use a different workflow; `/iterate` will refuse
- Open-ended creative work without an eval — the eval is the spec; without it there's nothing for the loop to optimize against
- Anything where the eval doesn't actually measure what the operator cares about (Goodhart risk dominates)
- High-stakes irreversible changes — `/iterate` is destructive on the live file; the operator should branch first if rollback matters

## Falsifiability check (recursive)

Per Popper's own rule: *what observation would refute the claim that `/iterate` produces better output than a single best-effort pass by the agent?*

- **Refutation criterion**: if the final iteration's score is indistinguishable from `iteration-1` (the first edit) across multiple invocations, the loop is decorative — one shot would have done.
- **Tracking**: log `final - iteration_1` delta per invocation; if median delta is < 5% of the baseline-to-final improvement, the loop is decorative.
- **Cut threshold**: if >2/3 of invocations show single-shot quality matches the looped output, deprecate.

## Goodhart's-law guard (explicit, not implicit)

`/iterate` optimizes the eval. If the eval is wrong, the output is wrong-but-high-scoring. The operator is responsible for picking the right eval. This skill cannot detect Goodharting from inside the loop — that is the operator's job (or a downstream `/karpathy-bar` invocation against the result).

Recommended: use composable evals (`/karpathy-bar` on the result of `/iterate` with `--eval=ruff check`) so the optimization pressure and the quality pressure are separate gates.

## Comparison with `karpathy/autoresearch`

| Axis | `autoresearch` | `/iterate` |
|---|---|---|
| Target | `train.py` (ML training loop) | Any single text file |
| Eval | `val_bpb` (continuous, well-understood) | User-supplied; any parseable signal |
| Time budget | 5 min per experiment, run overnight | 1–60 min, single invocation |
| Iterations | ~100 over a night | Whatever fits in budget |
| Agent | One AI agent edits `train.py`, human edits `program.md` | One Claude session edits the file directly |
| Domain | ML optimization (Karpathy's specific focus) | General single-file optimization |
| Goodhart guard | Held-out eval (different val set than the optimized one) | Operator's responsibility; recommend composable evals |

The `/iterate` shape is generalized from Karpathy's pattern; the bet that single-agent narrow-optimization works under a wall-clock budget transfers. The Goodhart guard does NOT transfer — Karpathy has held-out ML eval, we do not (yet).

## Implementation

- Pure prompt-based skill (no Python script).
- Loop executed by Claude in the current session — read file, propose edit, write, run eval via Bash, compare, decide.
- Wall-clock check via the `date` command on each iteration boundary (no external timer needed).
- Diff log kept in-memory during the loop; printed only on output.
- No external API; no Agent dispatch (single-session by design — Agent dispatch would add cold-start overhead that wastes budget).

## Related

- `skills/tribunal/SKILL.md` — sibling skill (multi-lens decision)
- `skills/reflect/SKILL.md` — sibling skill (single-lens retrospective)
- `~/.claude/skills/karpathy-bar/SKILL.md` — recommended eval for prose `/iterate` invocations
- `~/.claude/projects/-Users-macbook-Dev-claude-second-brain/memory/autoresearch_handoff_raw.md` — design substrate (handoff doc with the autoresearch analysis)
- `plans/AUTORESEARCH-BRAINSTORM.md` — wall-clock-as-forcing-function principle
