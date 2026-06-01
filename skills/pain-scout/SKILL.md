---
name: pain-scout
description: >
  Autonomous-loop scout (Phase 2 of the startup-intel team) that surfaces founders/
  builders voicing pain about AI-agent reliability on X — and doubles as a LEAD ENGINE
  for the agent-reliability audit offer. Gathers via free web recon (reuses
  /x-launch-recon discipline), then runs the deterministic scout_ingest spine
  (belief-DB + dedup + Obsidian mirror + ranked feed). Output: a ranked "who's in pain"
  feed with a grounded outreach angle per lead. Cited or INFERRED — never fabricated.
argument-hint: "[optional: extra pain keywords or a niche to focus]"
---

# /pain-scout — find who's hurting, rank, and tee up the ask

You run ONE scout end-to-end. Config: `sources/pain-scout.yaml`. The point is twofold:
prove the autonomous gather→substrate→feed loop, AND hand the operator a ranked list of
real people whose pain the commitment-drift audit fixes.

## Cost & honesty reality (read first)
- **Default = interactive + free.** Gather uses WebSearch (a model tool); run here in the
  terminal it draws the subscription pool ($0). Do NOT silently wire this to `/schedule`
  via `claude -p` — that draws the metered Agent-SDK pool from 2026-06-15
  (≈ full API rates). Scheduling is only free once an `X_BEARER_TOKEN` enables a
  model-free collector (and X bills its own reads).
- **Reads free, contact gated.** This skill only READS + RANKS + DRAFTS. Every outward
  action (reply, DM, follow, post) is the operator's to take through the commitment-gate.
  Never auto-contact anyone.
- **No invented evidence.** Every lead cites a real post URL, or is labeled INFERRED.
  Never fabricate engagement numbers or quotes (x-launch-recon hard rule 4).

## Phase 1 — Gather (free web recon)
Read `sources/pain-scout.yaml`. For each `enabled` source, run WebSearch/WebFetch over
its query (X via `site:x.com` + indexed mirrors; Reddit via the RSS url). Pull posts
where someone describes an agent forgetting/ignoring/drifting from its rules, or wishing
for reliability tooling. Capture for each: the verbatim line, the post URL, rough
recency, and (if visible) who they are (founder? company?). Stop at the budget ceiling
(default $0 → web only).

## Phase 2 — Shape findings
Turn each hit into a finding dict for the ingest spine:
```python
{ "scout": "pain-scout",
  "title": "<one-line: who + the pain>",
  "summary": "<context: thread, how many echo it>",
  "source_type": "x" | "reddit",
  "source_url": "<real URL>",            # or None -> note renders UNCITED
  "captured_at": "<YYYY-MM-DD>",
  "signal_strength": 0.0-1.0,            # acuteness × reachability (your judgment, stated)
  "confidence": 0.0-1.0,                 # how sure this is real pain, not noise
  "tags": ["agent-reliability", "lead", "<sector>"],
  "raw_quote": "<verbatim line>" }       # or None -> note renders INFERRED, never faked
```
Score `signal_strength` higher when the pain is acute AND the person is reachable +
plausibly a buyer (a founder shipping an agent product > an anonymous venter).

## Phase 3 — Ingest (deterministic, free)
Call the spine — it writes to the belief DB (dedup across runs), mirrors to Obsidian,
and ranks:
```bash
VENV=~/.claude/memory-mcp/.venv/bin/python3
$VENV -c "
import sys, json; sys.path.insert(0,'memory-mcp')
from db import MemoryDB; from scout_ingest import ingest_findings
findings = json.load(open('/tmp/pain_findings.json'))
db = MemoryDB(__import__('os').environ.get('MEMORY_DB', __import__('os').path.expanduser('~/.claude/memory/memory.db')))
import os; vault = os.environ.get('OBSIDIAN_VAULT', './intel-vault')
res = ingest_findings(db, findings, project='startup-intel', vault_dir=vault)
print(f'ingested {len(res[\"ingested\"])}, dedup-skipped {len(res[\"duplicates\"])}')
db.close()
"
```
(Write the Phase-2 findings to `/tmp/pain_findings.json` first.)

## Phase 4 — The feed (the deliverable)
Present the ranked `feed`, top-N, as a table the operator can act on:

| # | who | the pain (quoted) | signal | source | suggested angle |
|---|-----|-------------------|--------|--------|-----------------|

For each top lead, draft ONE grounded outreach angle that connects THEIR words to the
audit offer ("you said X forgets its rules mid-task — that's exactly the drift I find +
fix in 48h"). The drafts are for the operator to send by hand through the gate — this
skill never sends.

Close with: how many findings new vs dedup-skipped, the vault path written, and the
single highest-signal lead to act on first.

## Reuse (don't reinvent)
`commands/x-launch-recon.md` (free-web X discipline + budget rails) ·
`memory-mcp/scout_ingest.py` (the ingest spine, 12 tests) · `memory-mcp/intel_mirror.py`
(Obsidian mirror) · `intel/SUBSTRATE.md` (the DB-canonical design) · the cold-ask
template the operator already wrote (the angle each lead feeds).
