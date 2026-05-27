---
description: Refresh a persona's freshness cache — fetch the real expert's recent activity (GitHub, blog, field signal) and write a generic digest to personas/.cache/. Auto-invoked by /team in Phase 0.7 on stale-or-missing cache; can be run standalone.
argument-hint: <expert-slug> (e.g. "karpathy", "fielding", "beck") or "all" to refresh every persona's stale cache
---

# /persona-recap

A persona without freshness is a museum piece. Training cutoff is fixed; the real expert ships code today. This routine bridges that gap by exploiting real-time tool access — `gh`, `WebFetch`, `WebSearch` — so a bound persona inherits *field intelligence as of today*, not as of training cutoff.

## Input

`$ARGUMENTS` — one of:
- `<expert-slug>` (e.g. `karpathy`, `beck`) — refresh that one persona's cache
- `all` — refresh every persona whose cache is missing or stale

## Phase 1 — Locate the persona file

1. `ls ~/Dev/claude-second-brain/personas/*__<slug>.md`
2. If multiple files match (e.g. Karpathy under `ml-pedagogy` and `prompt-engineering`), refresh each one's cache separately — they share an expert but their domain context differs.
3. If no match → report and stop. Suggest `/persona-research` if a new persona is wanted.

## Phase 2 — Read recap config from frontmatter

Parse the `recap:` block from the persona file. Required fields:
- `github_user` (string or null)
- `primary_repos` (list of `owner/repo` strings; may be empty)
- `blog_url` (string or null)
- `recap_ttl_days` (integer)
- `mode` (optional; if `field`, the recap focuses on field activity rather than personal activity — used for dormant experts)

If frontmatter has no `recap:` block at all → skip with a "no recap config" message. Personas without config don't get cached recaps.

## Phase 3 — Cache freshness check (skip-if-fresh)

Cache path: `~/Dev/claude-second-brain/personas/.cache/<slug>__recap.md`

1. If file exists, read its frontmatter `last_fetched: YYYY-MM-DD`.
2. If `last_fetched + recap_ttl_days >= today` (today as of `date +%Y-%m-%d`), cache is fresh → exit early with: `"<slug>: cache fresh (last fetched <date>, ttl <N>d). Skipping."`
3. Otherwise proceed to fetch.

When invoked with `all`: do this check for every persona and only fetch the stale ones in parallel.

## Phase 4 — Fetch (parallel within a single persona)

Run as many of these in parallel as the config supports:

### 4a. GitHub user activity (only if `github_user` not null)

```bash
gh api "users/<github_user>/repos?sort=updated&per_page=5" \
  --jq '.[] | {name, description, updated_at, stargazers_count, html_url}'
```

If the call returns 404 → the handle is wrong. Log the failure to the cache file under `## Issues` and fall back to blog + WebSearch only. Do NOT silently swallow — the persona file should be corrected.

### 4b. Primary repos (only if `primary_repos` non-empty)

For each repo:

```bash
gh api "repos/<owner>/<repo>/commits?per_page=5" \
  --jq '.[] | {sha: .sha[0:7], message: .commit.message, date: .commit.author.date, author: .commit.author.name}'
```

Plus the repo's recent releases (1 call per repo, lightweight):

```bash
gh api "repos/<owner>/<repo>/releases?per_page=3" \
  --jq '.[] | {name, tag_name, published_at}'
```

### 4c. Blog (only if `blog_url` not null)

`WebFetch <blog_url>` — extract:
- Last 5 post titles + dates (if the blog has a feed/list page).
- Headline of any post dated within the last `recap_ttl_days * 3` window.

If WebFetch returns >2x typical token cost (large landing page), narrow to `<blog_url>/feed` or `<blog_url>/archive` if those exist; otherwise truncate to first 4K chars.

### 4d. Field signal (always for `mode: field`; optional otherwise)

```
WebSearch "<expert full name> <current-year>"           # personal-feed mode
WebSearch "<domain> advances OR new tools <current-year>"  # field mode (dormant experts)
```

Filter results to the last 6 months. Skip Twitter/X domains regardless of result rank (no fragile scraping).

## Phase 5 — Synthesize generic digest (NOT task-bound)

Write a 3-section markdown digest. The digest is **task-agnostic** — it summarizes what's new in the expert's world, not what's new *for the current task*. Task-binding happens at `/team` Phase 3 injection, not here. This keeps the cache reusable across many tasks within the TTL.

Cache file structure:

```markdown
---
expert: <Full Name>
slug: <slug>
last_fetched: YYYY-MM-DD
ttl_days: <N>
mode: personal | field
sources_used: [github, repos, blog, search]
sources_skipped: [...with reason]
---

# Recap — <Name> as of <date>

## Recent repos / commits
- <repo>:
  - <date> — <commit message> (<sha>)
  - <date> — <commit message> (<sha>)
- <repo>:
  - ...

(If `mode: field`: this section is absent or replaced with "Field repos showing recent activity" — e.g. for Liskov the recap might list automerge, Rust trait-system crates, TS variance proposals.)

## Recent writing
- <date> — "<post title>" (<blog_url>)
- <date> — "<talk title>" (<source>)

## Field signal (last N months)
- <date> — <headline> (<source>)
- <date> — <headline> (<source>)

## Issues
- (any 404s, blocked URLs, or failed fetches — surfaces a correction signal back to the persona file)
```

## Phase 6 — Quality gate

Run `/karpathy-bar` against the cache file:
- **Truthfulness pass**: every URL listed resolves (`curl -sI` — sample, don't exhaust). Any 4xx → move to `## Issues` section.
- **Marketing-adjective grep**: no `revolutionize|empower|leverage|next-generation|comprehensive|seamless|paradigm` in the digest's own voice.
- **Voice pass**: digest is factual ("Karpathy shipped llm.c 2.0 on 2026-05-12"), not interpretive ("revolutionary new release").

If FAIL: do not commit the cache file. Re-fetch the problematic items or write a `## Issues` note and proceed with what passes.

## Phase 7 — Report

```
PERSONA RECAP REFRESHED
=======================
Expert:        <Full Name>
Slug:          <slug>
Cache:         personas/.cache/<slug>__recap.md
Mode:          personal | field
Fetched:       <YYYY-MM-DD>
Next refresh:  <YYYY-MM-DD>  (today + ttl_days)

Sources used:    github, blog, search
Sources skipped: <list with reasons>

/karpathy-bar verdict: PASS | PASS-WITH-NITS | FAIL

Next step:
- If invoked by /team: binding completes; Phase 3 dispatch can inject the recap block.
- If invoked standalone: cache is now fresh; next /team dispatch within TTL will reuse it.
```

## Bulk mode (`/persona-recap all`)

1. `ls ~/Dev/claude-second-brain/personas/*__*.md` (skip README, .cache)
2. For each persona, run Phase 3 (freshness check).
3. Launch the fetch (Phase 4) **in parallel** for all stale personas — they're independent.
4. Synthesize each cache (Phase 5) sequentially after its fetch completes (to avoid context-window churn).
5. Report aggregate: N refreshed, M skipped (fresh), K failed (with reasons).

## Refuse criteria

- Refuse to write a cache file if `/karpathy-bar` returned FAIL on truthfulness (fabricated URL, hallucinated commit, etc.).
- Refuse to fetch Twitter/X under any code path — user explicitly excluded this surface.
- Refuse to bypass the TTL — if cache is fresh, exit. The TTL is the contract; force-refresh requires the user to delete the cache file manually.

## Provenance

Sibling to `/persona-research` (one creates the persona; this one keeps it living). Auto-invoked by `/team` Phase 0.7 on stale-or-missing cache. Designed under the discipline: the LLM is not "just an AI" — it has real-time tool access; use it to overcome training-cutoff staleness rather than emit confidently outdated advice.
