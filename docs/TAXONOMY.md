# Taxonomy — every command/skill by layer, built-in relationship, and lineage

> The full inventory behind `docs/GRAMMAR.md`. Each entry is tagged with its **layer** (the `layer:` frontmatter field), whether it **extends a Claude Code built-in** or is fully custom, and any **lineage** (what it evolved from). Produced by the 2026-05-31 three-agent audit.

## Layer legend (drives CLI color-coding via `/guide`)

| Layer | Meaning | Color hint |
|---|---|---|
| `primitive` | a Layer-0 building block (lens, gate, belief, memory I/O) | cyan |
| `operator` | binds primitives → verdict/refuse → synthesize | green |
| `workflow` | composes operators + manages state across agents/boundaries | yellow |
| `extends-builtin` | wraps/extends a native Claude Code command | dim/blue |
| `domain` | project- or domain-specific automation | magenta |

> Native skill pickers are not recolorable by us; color is rendered by `/guide`'s layered map and by the `layer:` frontmatter convention — see `docs/SUBSTRATE-HEALTH.md` §2 and the plan's Phase D.

---

## Operators (Layer 1) — the `bind → verdict|refuse → synthesize` family

| Command/Skill | Built-in? | Lineage |
|---|---|---|
| `tribunal` | custom | **inverts** `karpathy/llm-council` — preserves disagreement vs collapsing to one answer (`skills/tribunal/SKILL.md:12`) |
| `reflect` | custom | `tribunal` at **N=1**, three-block synthesis (`skills/reflect/SKILL.md`) |
| `karpathy-bar` | custom | quality-gate operator; distilled from real README-rewrite failures |
| `iterate` | custom | **generalizes** `karpathy/autoresearch` — loop-to-budget on any file (`skills/iterate/SKILL.md:8`) |
| `diagnose` | custom | reactive, interactive error interpretation |
| `investigate` | custom | `diagnose` in autonomous, stop-at-proof mode |

## Workflows (Layer 2) — operator + agent + state composition

| Command/Skill | Built-in? | Lineage / composition |
|---|---|---|
| `team` | uses Agent tool | analyze → `bind(fresh(lens)+ as agents)` → execute(layer-strict) → gate |
| `orchestrate` | uses Agent tool | decompose → parallel agent dispatch |
| `metaprompt` | custom | fuzzy task → phased executable prompt |
| `scan` | custom | parallel tracks {security, quality+gaps, ops} → one report; **territory-overlap** with `audit`+`gap-analysis` (not a literal pipe) |
| `metaprompt-toggle` | wraps `metaprompt` | `metaprompt` under a `UserPromptSubmit` hook |
| `diagnose-bound` | wraps `diagnose` | `diagnose` + `refuse(preconditions)` |

## Instances of operators (kept callable; documented, not merged)

| Command/Skill | Is an instance of | Frozen parameters |
|---|---|---|
| `cv-critique` | `tribunal` | lens-set = {hiring, skill-match, voice, coach} |
| `team-substack-v2` | `metaprompt` + `tribunal` | marketing-content lens-set |
| `fitbit-deployment-audit` | `scan` | Fitbit/FCM/session domain checks |
| `fitbit-gap-analysis` | `gap-analysis` | Fitbit data-integrity domain |

## Primitives & substrate (Layer 0)

| Command/Skill | Role |
|---|---|
| `recall` / `learn` | read / write the belief substrate |
| `ingest` | markdown auto-memory → sqlite (`ingest_markdown.py`) |
| `memory-lint` | health-check the memory layer (`lint_memory.py`) |
| `harden-memory` | end-to-end memory-pipeline audit |
| `context-save` / `resume` | `checkpoint` / `resume` across compaction |
| `context-status` | **extends** `/context` — adds % + threshold tiers |
| `persona-recap` | `fresh` — refresh a lens to field-current |
| `persona-research` | create a new `lens` (auto-invoked by `/team` on cache miss) |
| `self-audit` | toolkit introspection (`self_audit.py`) |
| `whats-new` | platform-update poller (`whats_new_check.py`) |

## Extends-builtin

| Command/Skill | Wraps | Adds |
|---|---|---|
| `verify` | `/verify` | structured phases (deps→lint→type→tests) |
| `context-status` | `/context` | % + threshold + recommendation |
| `new-project` | `/init` | CLAUDE.md template scaffolding |
| `commit-push-pr` | git+PR | TDD-must-pass gate |
| `tdd` | — | red-green-refactor enforcement (a `gate`) |

## Domain / utility

`status`, `session-recap`, `show-mental-model`, `explain`, `document`, `research`, `gap-analysis`, `audit`, `flag`, `resolve-pr`, `economy`, `idea`/`ideas`, `find-open`, `sync-memories`, `sync-skill-docs`, `guide`, `dstu-thesis`.

---

## Paired-workflow lineage (read/write & save/restore duals)

- `ingest` → `recall` → `learn` — write/index/read over one substrate.
- `context-save` → `resume` — save/restore across the compaction boundary.
- `idea` → `ideas` — capture/manage backlog.
- `tdd` → `commit-push-pr` — test-first discipline → gated commit.
- `iterate` + `karpathy-bar` — optimize with one eval, gate with another (anti-Goodhart pairing).

---

*Counts and relationships verified by the 2026-05-31 audit. The `layer:` frontmatter field is added per the plan's Phase D so `/self-audit` and `/guide` can read it programmatically.*
