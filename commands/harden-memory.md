---
description: Audit and harden the memory auto-sync pipeline end-to-end
argument-hint: (no args needed)
---

# Memory System Hardening — Full Pipeline Audit + Auto-Sync Implementation

You are a systems engineer hardening a personal knowledge system. The system must
sync automatically, recover from failures silently, and never lose data. Zero
manual intervention after setup.

## Architecture Context

The memory system has 4 layers:
1. **Memory MCP Server** (`~/.claude/memory-mcp/`) — SQLite + sqlite-vec + FTS5
2. **Embedding pipeline** — LM Studio nomic-embed-text-v1.5 (localhost:1234)
3. **Sync scripts** (`~/.claude/memory-mcp/sync.py`) — export/import/backup/reembed
4. **Git backup** (`~/.claude/` = private second-brain repo) — hourly launchd agent

Data flows: session → memory_save → db + embedding → git backup → cross-machine sync

## Phase 1: Audit (parallel, read-only)

Launch 3 Explore agents simultaneously:

**Agent 1 — Embedding Health**
- Count total memories: `SELECT count(*) FROM memories`
- Count memories WITH embeddings: join memories ↔ memory_vectors
- Count memories WITHOUT embeddings (the gap)
- Check if LM Studio is running and the embedding model is loaded
- Check `reembed_missing()` in sync.py — does it work? When was it last run?
- Verdict: what percentage of memories have embeddings?

**Agent 2 — Sync Pipeline Health**
- Check launchd agents: `launchctl list | grep -i claude` or `memory` or `sync`
- Read any .plist files in ~/Library/LaunchAgents/ related to memory/claude
- Check git status of ~/.claude/ — uncommitted changes? Unpushed commits?
- Check last backup timestamp: `git log -1 --format="%ai" -- memory/memory.db`
- Check if MEMORY.md files are tracked: `git ls-files projects/*/memory/*.md`
- Check if memory-export.json exists and when it was last updated
- Check crontab for any memory-related entries
- Verdict: is the backup pipeline actually running?

**Agent 3 — Memory Quality**
- Count memories by category and visibility
- Find memories with no summary (poor searchability)
- Find memories with importance < 3 (candidates for cleanup)
- Check for duplicate content (same content, different IDs)
- Check for orphaned links in memory_links table
- Check if [LEARNING] tags from sessions are actually being saved
- Verdict: what's the signal-to-noise ratio?

## Phase 2: Gap Analysis

From Phase 1 results, classify each gap:

| Gap | Severity | Auto-fixable? |
|-----|----------|--------------|
| Missing embeddings | HIGH | YES — reembed script |
| Launchd not running | CRITICAL | YES — install .plist |
| Uncommitted changes | HIGH | YES — git add + commit |
| No scheduled reembed | MEDIUM | YES — add to launchd |
| Duplicate memories | LOW | SEMI — needs review |
| Missing summaries | MEDIUM | YES — batch generate |

## Phase 3: Implementation (fix all auto-fixable gaps)

For each gap, implement the fix. Priority order:

### P0 — Data safety (do first)
1. Commit any uncommitted changes in ~/.claude/ (git add + commit)
2. Verify .gitignore rules are correct (MEMORY.md tracked, .jsonl ignored)
3. Push to remote if configured — ASK user first

### P1 — Embedding completeness
1. Run reembed for all memories missing vectors
2. If LM Studio is down, document which memories need reembedding
3. Add reembed to the scheduled backup pipeline (run after backup)

### P2 — Automated scheduling
1. Create/verify launchd .plist for hourly backup:
   - `python sync.py backup` — commits memory.db to git
   - `python sync.py reembed` — fills embedding gaps (only if LM Studio running)
   - Log output to ~/.claude/logs/sync.log
2. Load the agent: `launchctl load ~/Library/LaunchAgents/com.claude.memory-sync.plist`
3. Verify it runs: `launchctl start com.claude.memory-sync`

### P3 — Memory quality
1. Generate summaries for memories that have none
2. Flag duplicates for manual review (don't auto-delete)

## Phase 4: Verification

Run a full pipeline test:
1. Save a test memory via memory_save with visibility="team"
2. Verify it appears in `memory.db`
3. Verify it has an embedding (or is queued for reembed)
4. Run `python sync.py export --scope team` and verify it appears
5. Run `python sync.py export --scope team` and verify personal memories are excluded
6. Check git status — new backup should be committable
7. Delete the test memory

## Output Format

```
MEMORY SYSTEM HEALTH REPORT
============================
Database:     [N] memories, [M] with embeddings ([X]% coverage)
Categories:   rule=[N] pattern=[N] decision=[N] learning=[N] ...
Visibility:   personal=[N] team=[N] public=[N]
Last backup:  [timestamp] ([hours] ago)
Sync status:  [committed/uncommitted] [pushed/unpushed]
Launchd:      [running/not found/disabled]
MEMORY.md:    [N] files tracked in git

GAPS FOUND: [N]
  [CRITICAL] ...
  [HIGH] ...
  [MEDIUM] ...

FIXES APPLIED: [N]
  [P0] ...
  [P1] ...

VERIFICATION: [PASS/FAIL]
  [details]

REMAINING (manual review needed):
  - [items that can't be auto-fixed]
```

## Rules

1. **Never delete memories** without explicit user approval
2. **Never push to remote** without explicit user approval — commit locally only
3. **If LM Studio is down**, skip embedding steps gracefully — don't fail the whole pipeline
4. **Log everything** — if a fix is applied, note exactly what changed
5. **Test before wiring** — verify each component works before adding it to launchd
6. **Idempotent** — running this prompt twice should produce the same end state
7. Tag discoveries with [LEARNING]
