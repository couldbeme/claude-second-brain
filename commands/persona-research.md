---
description: Research a canonical expert in a domain and write a persona file to ~/Dev/claude-second-brain/personas/. Auto-invoked by /team on cache miss; can also be run standalone.
argument-hint: <domain-slug> (e.g. "graphql", "rust-lifetimes", "kubernetes-operators")
---

# /persona-research

Derive a new persona file for a domain that's missing from the cache. Two callers:
- **`/team`** auto-invokes this in Phase 0.7 when a role's domain has no matching persona.
- **You**, manually, to pre-seed a domain you expect to need later.

## Input

Domain: `$ARGUMENTS` (single domain slug — kebab-case, e.g. `graphql`, `rust-lifetimes`, `kubernetes-operators`)

## Phase 1: Pre-check

1. `ls ~/Dev/claude-second-brain/personas/<domain>__*.md` — if a file already exists, **stop** and report. Manual edit is the right path for updates, not re-research.
2. If `$ARGUMENTS` is empty or not kebab-case, ask the user for clarification and stop.

## Phase 2: Identify the canonical expert

Launch 3 WebSearch queries in parallel:

- `"<domain> canonical expert OR founder OR pioneer"`
- `"<domain> influential talks books site:youtube.com OR site:infoq.com"`
- `"<domain> opinionated thought leader blog"`

Selection criteria:
- **Founding contribution** — wrote the paper, designed the language/framework/protocol, named the field.
- **Public writing** — talks, blog, books that an outsider can verify.
- **Coherent intellectual signature** — recognizable voice across artifacts; you can tell their writing apart from a random blog post.
- **Living preferred over deceased**, unless the deceased expert remains the definitive source (e.g. Dijkstra for structured programming).

**If multiple candidates surface**: prefer the one whose work *introduced* the domain or whose framing still shapes how practitioners talk about it.

**If no candidate has clear signature + public writing**: STOP researching. Write a file with `expert_slug: anonymous` and a one-line note that no canonical expert was found for this domain. Mark it `last_updated: <date>` and move on. Generic-senior > fabricated-persona.

## Phase 3: Derive voice, mental models, moves, refusals

Search the chosen expert's:
- Personal blog (URL → `provenance`)
- Conference talks (YouTube/InfoQ — URL → `provenance`)
- Books (title + year → `provenance`)
- Recurring framing devices ("the X principle", "I call this Y") → `mental_models`
- Named techniques or patterns → `signature_techniques`
- Public criticisms or refusals — "I don't believe X", "this is anti-pattern Y" → `anti_patterns_called_out`

**Rule**: paraphrase with hedges ("often argues", "tends to favor"). **Do NOT fabricate quotes.** If you can't find a clear position on an attribute, leave that section terser rather than invent.

## Phase 4: Write the persona file

Schema reference: `~/Dev/claude-second-brain/personas/README.md`.

Filename: `<domain>__<expert-slug>.md` where `expert-slug` is lowercase last name (no spaces or hyphens unless the expert is mononymous).

Required frontmatter fields:
- `name`, `domain`, `expert_slug`, `when_to_invoke`
- `signature_techniques` (3-5 items)
- `anti_patterns_called_out` (2-4 items)
- `provenance` (verifiable URLs / citations)
- `last_updated` (today, YYYY-MM-DD)

Required body sections:
- `## Voice` — 2-3 sentences on cadence/vocabulary/what they cut
- `## Mental models` — 3-5 bullets
- `## Signature moves` — 3-5 bullets
- `## What they refuse` — 2-4 bullets
- `## When to deploy in a team` — 1-2 lines

## Phase 5: Quality gate (mandatory)

Run `/karpathy-bar` against the new file before declaring done:
- **Truthfulness pass** — every `provenance` URL resolves (`curl -sI` or `gh api`); no fabricated quotes in body.
- **Marketing-adjective grep** — no `revolutionize|empower|leverage|next-generation|comprehensive|seamless|paradigm` in artifact's own voice.
- **Length pass** — under ~250 lines; cut any restatement.
- **Voice pass** — concrete, opinionated, not committee-speak. Not reverent prose about the expert ("X is widely regarded as..." → cut).

If FAIL: do not commit the file. Report findings to the user and let them decide whether to revise, retry, or fall back to anonymous-senior.

## Phase 6: Report

```
PERSONA WRITTEN
===============
Domain:    <slug>
Expert:    <Name>  (or anonymous-senior if no canonical found)
File:      ~/Dev/claude-second-brain/personas/<file>.md

Provenance verified: <N>/<M> URLs resolved
/karpathy-bar verdict: PASS | PASS-WITH-NITS | FAIL

Next step:
- If invoked by /team: binding completes; Phase 3 dispatch can proceed.
- If invoked standalone: cache grew by one entry; ls personas/ to confirm.
```

## When NOT to invoke

- **Domain too narrow to have a canonical expert** (e.g. "my-internal-feature-flag-system"): personas are for *transferable* expertise; project-specific knowledge belongs in CLAUDE.md, not here.
- **File already exists for this domain**: edit it manually; the research already paid off once.
- **You only need a one-off impersonation in this session**: just describe the voice inline in your prompt. Cache only when reuse is likely.

## Provenance

Sibling skill to `/team` (auto-invokes this) and `/research` (this is a specialized form of research with a specific output schema).
