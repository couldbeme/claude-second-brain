---
description: Run the Karpathy-grade quality bar against an artifact (README, doc, skill, module, commit diff) — every claim has a runnable proof; no marketing fluff; ≥20% cut on second draft. Catches inaccuracies before commit.
argument-hint: <file-path> | <commit-sha> | "current-diff" | "all-uncommitted"
---

# /karpathy-bar — Quality bar with runnable proofs

Apply the Karpathy-grade quality bar to a target artifact. Born from real failures: the README rewrite agent shipped 4 fake commands + 1 misattributed taxonomy + 1 fabricated incident URL + 1 wrong star count + 1 inaccurate "no scanner" claim before this gate caught them. The bar is a checklist, not vibes.

## What "Karpathy-grade" means here

8 properties drawn from Karpathy's significant artifacts (micrograd, nanoGPT, llm.c, Software 2.0, neural-networks-zero-to-hero):

1. Minimal LOC, maximal clarity — every line earns its place
2. Working code over claims — running examples, not papers
3. Reproducibility is the spec — clone + install + same output
4. First-principles framing — "what concrete problem, what concrete cost?"
5. Teaching-shaped — reader is more capable after, not just informed
6. No hype, no marketing — facts, observations, working artifacts
7. Distinctive intellectual signature — single coherent mind
8. Verification artifacts shipped with claims — test / benchmark / runnable check

The user's qualifier: "all proven and valuable."
- **Proven** = every claim has a *runnable proof* (test passing, command executing, benchmark documented). Not "we believe"; only "you can run this."
- **Valuable** = solves a problem someone actually has. Cited or observed; not "we built this because we could."

## Workflow

### Phase 1 — Identify the target

Resolve the argument:
- File path → read full content
- Commit SHA → `git show <sha>` for the diff
- `"current-diff"` → `git diff` (unstaged + staged)
- `"all-uncommitted"` → `git status --short` + read each modified/new file

### Phase 2 — Truthfulness pass (per claim)

For every claim of novelty, uniqueness, capability, or count:

1. **Identify the claim.** Quote the exact sentence.
2. **Identify the proof anchor.** Does the artifact reference a file, function, test, benchmark, command, or external source as evidence?
3. **Verify the anchor.**
   - File reference → does the file exist? `ls -la <path>` or `[ -f <path> ]`
   - Function reference → does the function exist with that name? `grep -n "def <name>\|<name>(" <file>`
   - Command reference → does the command file exist? `[ -f commands/<name>.md ]` or `[ -f skills/<name>/SKILL.md ]`
   - Count claim ("27 commands") → re-grep: `ls commands/*.md | wc -l`
   - URL claim → `curl -sI <url>` returns 2xx? Use `gh api repos/...` for GitHub URLs.
   - Star count → `gh api repos/<owner>/<repo> --jq .stargazers_count`
   - Test claim ("X tests pass") → `pytest path/to/tests -q`
4. **If anchor missing or unverifiable** → flag as `[UNVERIFIED]`. The claim must either be hedged ("we believe", "appears to") or removed.

### Phase 3 — Marketing-adjective grep

Run against the artifact body (NOT inside code-block examples that show literal external content):

```
grep -iE 'revolutionize|empower|leverage|AI-powered|next-generation|synergy|robust|comprehensive|seamless|professional-grade|magic|paradigm shift|game.changer'
```

Any hit in the artifact's own voice = blocking finding.

### Phase 4 — Length pass

- Word/line count.
- Could a second draft cut ≥20% without losing meaning?
- For prose: any paragraph that restates the previous? Cut.
- For tables: any row that adds <1 unit of information? Cut.

### Phase 5 — Reproducibility pass

For every command shown in the artifact:
- `bash -n` parses it (extract code blocks, syntax-check)
- Path arguments resolve on disk
- The expected output description matches what the command actually produces (spot-check by running, if safe)

### Phase 6 — Voice pass

Read the artifact aloud (or scan):
- Distinctive voice (terse, opinionated)? Or committee-speak / corporate-fluff?
- Reverent prose anywhere? (e.g., "We believe deeply that..." — refuse.)
- Defensive comparisons or trash-talk? Refuse.

### Phase 7 — Output the verdict

```
## /karpathy-bar verdict — <PASS | PASS-WITH-NITS | FAIL>

### Blocking findings (must fix)
- [TRUTHFULNESS] file:line — claim X has no proof anchor; suggested fix: <hedge | remove | add proof>
- [MARKETING] file:line — banned word "<word>" in artifact's voice
- [REPRODUCIBILITY] file:line — command Y references missing path Z
- ...

### Nits (should fix, not blocking)
- [VOICE] file:line — "<sentence>" reads as committee-speak; suggest tightening
- [LENGTH] could cut ~N% — list 2-3 paragraphs to consolidate
- ...

### Truthfulness verification (table)
| Claim (location) | Proof anchor | Status |
|---|---|---|
| ... | ... | VERIFIED / UNVERIFIED / INACCURATE |

### Voice / length / reproducibility
- Voice: PASS | needs tightening
- Length: PASS (current N lines; can/can't cut 20%)
- Reproducibility: PASS | N issues
```

## Refuse criteria

Refuse to issue PASS verdict if:
- Any claim has no proof anchor and isn't hedged
- Any banned marketing word in artifact's own voice
- Any cited file/function/command/URL doesn't resolve
- Inflated counts not re-grep'd
- Defensive or trash-talking comparisons

## When to invoke

- Before any commit that changes a public-facing doc (README, CHANGELOG, marketing copy)
- After any agent-generated content (especially documentation-agent output — this skill was born from those)
- Before merging a PR that adds external claims
- Quarterly self-audit on key artifacts

## When NOT to invoke

- Internal-only / private notes (truthfulness still matters but the bar is lower)
- Code-only changes (use `code-reviewer` agent instead)
- Pure refactors without claim changes

## Implementation notes

This is a *workflow skill* (no backing script). The skill body IS the workflow. Claude reads/inspects the target via Read/Bash and produces the verdict. Compare to `/memory lint` (Python script): `/karpathy-bar` is closer to `/resume` and `/remind`'s shape — structured prompt engineering against a fixed checklist.

## Provenance

Distilled from a quality-bar checklist developed in practice after a rewrite caught 6+ inaccuracies that would have shipped without the gate (2026-04-28). Generalized as a marketplace skill once it earned its place.
