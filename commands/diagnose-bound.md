---
description: Mandatory persona-bound diagnosis — check cache → /persona-research if absent → context7 docs refresh → THEN diagnose. Refuse if any precondition is skipped.
argument-hint: <issue description, paste, or symptom>
---

# /diagnose-bound — never diagnose unbound

NON-NEGOTIABLE precondition for any root-cause work (bug, regression, build break, CI fail, deploy hiccup). Memory anchor: `~/.claude/projects/<slug>/memory/persona_bound_diagnosis_required.md`.

## Phase 0 — Extract affected stack (≤5s)

From the symptom, name the stack(s). Examples:

- "InconsistentMigrationHistory" → `django.migrations`
- "compose recreated container without override" → `docker-compose`
- "Metro can't resolve" → `react-native` + `metro`
- "fmt consteval error" → `cocoapods` + `cpp` + `xcode`
- "checkpoint logs in error/ path" → `postgres.checkpoint` + `aws.rds`

If symptom is opaque, fall back to error-message keywords. Multi-stack issues → name each.

## Phase 1 — Persona lookup (parallel reads, ≤10s)

1. `ls ~/Dev/claude-second-brain/personas/*__*.md`
2. Filter by `domain:` frontmatter; match the stack(s) from Phase 0.
3. Multi-match → tie-break by `last_updated:` recency.
4. Zero match → fire `/persona-research <domain>` in parallel (non-blocking). Proceed with generic agent + explicit gap note; persona-research result lands later and updates the bind.

If multiple stacks → bind ONE persona per stack (parallel diagnosis lanes).

## Phase 2 — Persona freshness (parallel, non-blocking until Phase 4)

For each bound persona, read `~/Dev/claude-second-brain/personas/.cache/<expert_slug>__recap.md`.

- Fresh = `last_fetched + recap_ttl_days ≥ today` → continue
- Stale OR missing → fire `/persona-recap <expert_slug>` in parallel
- Recap result MUST land before Phase 4 dispatch (it's primary evidence for the diagnosis frame)

If a persona has no `recap:` block → skip; that persona doesn't use freshness gating.

## Phase 3 — Live docs refresh (parallel, MANDATORY)

For each Phase 0 stack:

1. `mcp__context7__resolve-library-id` with the library name (e.g. "django", "docker-compose", "react-native-svg", "fmt", "cocoapods")
2. `mcp__context7__query-docs` with the specific symptom keyword (e.g. "InconsistentMigrationHistory", "CircularDependencyError", "Conflicting migrations leaf", "consteval", "Auto migration leaf")

Returned docs are **PRIMARY EVIDENCE**. Training data is supplementary only.

Fallback chain if context7 returns nothing for a library:

1. WebFetch official docs site (`https://docs.djangoproject.com/...`, `https://reactnative.dev/...`, etc.)
2. `gh api repos/<org>/<repo>/releases` or `/contents/CHANGELOG.md` for changelog/release-note check
3. If BOTH fail → surface "training-data-only" caveat in output explicitly; do NOT silently rely on cached knowledge.

## Phase 4 — Diagnose

Now (and ONLY now) start root-cause analysis.

Inhabit the bound persona's voice; apply their `## Mental models` as framing; respect their `## What they refuse` as hard floor. Header every diagnostic message with:

```
*Operating as <Name> (<domain>); docs from <context7 lib-id @date> | <WebFetch URL @date> | training-data-only*
```

Evidence-gated loop (Linus-on-kernel-issues mode):

- Hypotheses ranked, **falsifiable**
- For each: a single observation that would kill it
- Run allow-listed read-only commands to confirm/kill (grep, git log/blame, manage.py showmigrations, docker compose ps, log show)
- Iterate until ONE survives or NONE do
- **BANNED**: "probably", "should work", "I think", hedged claims without runnable proof anchor

## Phase 5 — Output (MUST include all sections)

```
## Diagnosis — <one-line root cause | "NOT YET ROOT-CAUSED">

### Persona
<Name> (<domain>) — `<file path>`
Recap last refreshed: <YYYY-MM-DD>

### Stack docs source
- context7: `<lib-id>` @ <date> — sections: <symbol/heading>
- (if WebFetch fallback) <URL> @ <date>
- (if training-data-only) ⚠️ "training-data-only — no fresh docs available"

### Root cause
<2-3 sentences. Symptom vs cause distinguished.>

### Evidence (every claim anchored)
- <claim> — proof: `file.py:NN` | command output | count
- ...

### Hypotheses killed
- <hypothesis> — killed by: <observation>

### Regression / introduction
Bounded to: <commit/PR/window>. Minimal repro: <...>

### Failing regression test (written, not yet applied as fix)
<path + the test that reproduces the bug>

### Remediation (NOT applied — separate user gate)
<the fix, described>
```

## Refuse criteria

REFUSE to deliver a diagnosis if ANY of:

- No persona was bound AND no `/persona-research` was dispatched
- No context7 / WebFetch lookup was performed for any affected stack
- Output skips the "Persona" or "Stack docs source" header
- Root cause is stated without a runnable proof anchor or a failing regression test
- Diagnosis uses banned hedges ("probably", "should work", "I think")

## Why this rule exists

2026-05-20 lesson: solo, unbound diagnosis cost hours on the XXX_auto migration leaf, the P0-9 dep-cycle, the docker-compose-file drift, and the fmt 11 consteval error. Each could have been ~10× faster with a persona bound + current docs pulled. The rule overrides time pressure — a 30-second bug becomes a 60-second bug, and the 60 seconds catches the wrong-mental-model errors that account for most failed fixes.

The rule binds BOTH single-persona spawn (this skill) AND multi-persona spawn (`/team` Phase 0.7 + Phase 3 injection). When `/team` is invoked, every Layer 1 agent inherits this discipline via their persona block.

## Exceptions

Trivial typo fixes / one-line obvious corrections do NOT require the full ritual. The trigger is **"facing an issue, identifying root cause"** — that implies non-trivial diagnosis. If the fix is "rename a variable", just rename it.

## When to invoke

- Bug reports / stack traces / failure outputs from CI, test runs, deploys
- Any "X is broken" / "Y doesn't work" / "Z is failing" message
- Build chain errors (Docker, CocoaPods, npm, Cargo, Maven, ...)
- Migration failures, schema-drift, dep-cycle errors
- Performance regressions, slow queries, timeout errors
- Production incidents

## When NOT to invoke

- Feature requests (use `/team` or `/feature` instead)
- Refactoring without a bug ("clean this up")
- Documentation requests
- Code reviews of net-new work (use `/audit` or `/team` Layer 2)
