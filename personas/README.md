# Personas — expert impersonation cache

Named-expert persona library. `/team` consults this directory when binding agents to roles, so each role inherits a real expert's voice, mental models, and signature moves instead of a generic "senior X dev (15 years)" placeholder.

## Why this exists

Generic seniority labels ("15 years experience") are vague and don't shape behavior. Named experts do:
- **Karpathy** for ML pedagogy → terse, working code, micrograd-style examples.
- **Fielding** for REST design → uniform-interface obsession, hypermedia constraints.
- **Beck** for TDD → red-green-refactor discipline, listening to test pain.

The persona is the *constraint*, not just a label. The agent prompt inherits voice + mental models + anti-patterns the expert publicly calls out.

## File schema

One file per `<domain>__<expert-slug>.md`. Filename is grep-target by domain.

```markdown
---
name: <Full Name>
domain: <slug — must match filename prefix>
expert_slug: <slug — must match filename suffix>
when_to_invoke: <one line — the trigger>
signature_techniques:
  - <tight technique 1>
  - <tight technique 2>
  - <tight technique 3>
anti_patterns_called_out:
  - <thing they publicly refuse>
  - <thing they publicly refuse>
provenance:
  - <URL or citation — the source the persona was derived from>
last_updated: <YYYY-MM-DD>
---

# Impersonating <Name>

## Voice
<2-3 sentences. How they write/talk. Cadence, vocabulary, what they cut.>

## Mental models
<3-5 bullets. The frames they reach for first.>

## Signature moves
<3-5 bullets. Concrete techniques, named patterns, tools they ship.>

## What they refuse
<2-4 bullets. Anti-patterns they publicly call out. The 'no' is as identifying as the 'yes'.>

## When to deploy in a team
<1-2 lines. The task shape that calls for this persona.>
```

## Lookup flow (used by `/team`)

1. For each agent role selected in Phase 2, build a domain key from the task + agent type (e.g. `senior-backend-dev` + "REST API" → `rest-api`).
2. `ls personas/<domain>__*.md` — if a file matches, attach the impersonation block to that agent's prompt.
3. On miss: dispatch `/persona-research <domain>` which writes a new file here, then proceed.
4. The bound persona name appears in the `/team` proposal: `senior-backend-dev as Fielding (REST design)`.

## Filename examples

```
ml-pedagogy__karpathy.md
prompt-engineering__karpathy.md       # same expert, different lens
rest-api__fielding.md
type-systems__liskov.md
functional-design__hickey.md
tdd__beck.md
performance__gregg.md
security__schneier.md
frontend-architecture__abramov.md
sre-observability__majors.md
distributed-data__kleppmann.md
```

One expert may appear under multiple domains (Karpathy for both `ml-pedagogy` and `prompt-engineering`) — they're separate files because the *lens* matters more than the person.

## How to add a new persona

- Manual: copy an existing file as template, fill in voice/models/moves/refusals from sources you trust, set `provenance`.
- Automatic: run `/persona-research <domain>` (see `commands/persona-research.md`). It WebSearches for the canonical expert in that domain, derives the persona from their public writing, and writes the file.

## What this is NOT

- Not a replacement for the agent-role files in `~/.claude/agents/`. Those define *what tools the agent has*. Personas define *how the agent thinks and writes*.
- Not a celebrity wall. If a domain has no canonical expert with public writing, leave it empty — generic-senior is better than fabricated-persona.
- Not auto-loaded into context. `/team` reads only the personas it binds; the rest sit on disk.

## Quality bar

Each persona file must:
- Cite real public sources in `provenance` (talks, papers, blog posts, books — URLs preferred).
- Avoid putting words in the expert's mouth they didn't publicly hold. Hedge ("often argues", "tends to favor") rather than fabricate quotes.
- Pass `/karpathy-bar` for voice + truthfulness (no marketing fluff, no unfalsifiable claims).
