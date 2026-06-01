---
name: publish-safety
description: >
  Pre-public-push leak audit. Before a private/local repo (or branch) is pushed to a
  public remote or its link shared, prove that NOTHING personal, sensitive, internal,
  planned, client-owned, or artifact-shaped will be exposed — across blob content,
  FULL git history, commit messages, author identity, branch names, tags, and gitignore
  coverage. One-way door: defaults to NO-GO until every acceptance criterion passes.
argument-hint: "[target remote/branch, e.g. 'origin feat/x']  (defaults to detecting the push target)"
---

# /publish-safety — assume an adversary clones everything

A public push is irreversible: once one stranger clones, history rewrites buy nothing.
So audit as if a hostile reader will read **every blob in every commit**, **every commit
message**, **every branch name and tag**, and the **author email** — not just the current
tree. Default verdict is **NO-GO**; you earn GO by passing all criteria with evidence.

## Rails (non-negotiable)
- **Full history, not just the tree.** Secrets/PII hide in old, amended, or deleted-file
  commits. (The canonical failure: a `.gitignore` added *after* `git add` leaves the blob
  in history — `git rm --cached` only removes it going forward.)
- **The stranger test** (CLAUDE.md rule 13): for every line that would publish, ask *"am I
  fine with this at the top of `git log -p` in front of someone I'd never hand a credential
  to?"* If no → it's a finding.
- **Report what you did NOT check.** Silent gaps read as "all clear" when they aren't.
- **Never push.** This skill only audits + prescribes remediation. The push stays the
  operator's explicit action.
- **First push of a branch publishes its WHOLE ancestry since the fork point** — scope to
  that, and flag if it drags intentionally-private commits public.
- **Scanners report COUNTS + `file:line` locations — NEVER the matched secret itself.** A
  grep that *prints* matching lines will echo a live secret into the terminal, the
  transcript, and any log if one exists. Use `grep -c` / report locations; only a human
  opens the actual line. (This rule exists because a printing-scan is itself a leak vector.)

## Phase 0 — Scope
Determine exactly what becomes public: `git remote -v`; is the target remote public? Does
it already have this branch? If not, the publish set = `git log <public-remote>/<base>..HEAD`
(all of it). List the commit count + range. State it before scanning.

## Phase 1 — Secrets (FULL history)
Scan every blob ever committed in the publish set (and `--all` as a base sanity check):
credential patterns — `xai-`, `sk-…`, AWS `AKIA…`, GitHub `ghp_/gho_`, X bearer `AAAA…`,
`-----BEGIN … PRIVATE KEY`, `client_secret`, `bearer <token>`, `.env` values, password
assignments. Distinguish real secrets from **test fixtures** (e.g. AWS's documented
`AKIAIOSFODNN7EXAMPLE`) — note them as benign, don't flag.

## Phase 2 — Personal / identity
Operator real name, email, phone, address, location; author + committer identity across
all commits (`git log --all --format='%an %ae %cn %ce' | sort -u`) — does a real email or
real name leak vs the chosen public handle?

## Phase 3 — Internal / planned / strategy
Plans, roadmaps, monetization, pricing, hiring/job-target, competitive strategy, internal
audits, "operator strategy" content, deferred-secret lists. Confirm `plans/`, `audits/`,
and any strategy docs are **untracked AND absent from history**. Flag any tracked doc that
reads as internal-thinking rather than a public toolkit deliverable.

## Phase 4 — Client / third-party
Client/employer project names, infra (hostnames, instance IDs, internal IPs, SSH paths),
data, or domain-identifying skill names that reveal who the operator works for.

## Phase 5 — Artifacts
Raw transcripts, real (non-synthetic) eval data, logs, `/tmp` dumps, build outputs,
captured user data. Confirm each is gitignored AND never committed.

## Phase 6 — Metadata vectors
Commit messages (all, full bodies), branch names, tags — for codenames/secrets/strategy.
`.gitignore` coverage: every sensitive path both ignored AND never appearing in
`git log --all --name-only`.

## Phase 7 — Acceptance criteria (scorecard, each PASS/FAIL + evidence)
| # | criterion | pass = |
|---|---|---|
| C1 | No real credential in tree or full history | 0 hits (fixtures excluded) |
| C2 | No personal PII / real-identity leak in files or author metadata | 0 |
| C3 | No internal/planned/strategy content tracked or in history | 0 |
| C4 | No client/third-party identifying content | 0 |
| C5 | No raw artifacts/transcripts/real data committed | 0 |
| C6 | Commit messages + branch names + tags clean | 0 |
| C7 | Every sensitive path gitignored AND never in history | verified |
| C8 | Whole-ancestry exposure is intentional + operator-confirmed | explicit yes |

## Phase 8 — Verdict + remediation
- **GO** only if C1–C8 all pass.
- **GO-WITH-REMEDIATION** with exact commands: `git rm --cached <p>` (untrack), `git
  filter-repo --invert-paths --path <p>` (purge from history), genericize a line, or
  **scope down** (cherry-pick the publish-safe commits onto a fresh branch off the public
  base instead of publishing full history).
- **NO-GO** otherwise. List what was not checkable.
Optionally route the verdict through `/tribunal` (security + falsifiability + refusal
lenses) for a one-way-door decision.

## Reuse
`commands/scan.md` / `security-review` (code-vuln complement) · git-archaeology
(`git log --all -p`, `git log --all --name-only`) · the never-push-includes-history +
gitignore-after-add-is-a-no-op lessons are the two failure modes this skill exists to catch.
