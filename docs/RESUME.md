# RESUME — How to Restart After Compact / New Session

This is the operator runbook for picking up where you left off. Read top-to-bottom on a fresh session, or jump to the scenario that matches your situation.

## TL;DR — three commands

```
/resume         # 1-page re-orientation summary from checkpoint + commits + memories
/ingest         # sync any markdown writes since last sync into memory.db
/memory lint    # health-check the memory layer
```

If `SessionStart` and `PreCompact` hooks are configured (see *Setup* below), `/ingest` runs automatically on every new session and `PreCompact` snapshots before compaction. You then only need `/resume` to re-orient.

---

## Auto vs manual — the decision matrix

| Action | Auto trigger | Manual fallback |
|---|---|---|
| Load `~/.claude/CLAUDE.md` (rules) | Every session start | n/a |
| Load `MEMORY.md` index (17+ entries) | Every session start | n/a |
| Sync markdown → sqlite-vec | `SessionStart` hook (silent) | `/ingest` skill, or `python3 ~/Dev/claude-second-brain/memory-mcp/ingest_markdown.py --apply` |
| Snapshot before `/compact` | `PreCompact` hook (auto) | `/context-save` |
| Read checkpoint + re-orient | `/resume` skill (manual) | `Read ~/.claude/checkpoint.md and orient.` |
| Lint memory layer | None auto | `/memory lint` (recommended weekly) |
| Check context % | None auto | `/context-status` or built-in `/context` |

---

## Scenario A — Resume in same dir, same machine (most common)

1. **Open Claude Code** in `~/Dev` (or your active project root).
2. **Auto-loads happen invisibly** — `CLAUDE.md` rules + `MEMORY.md` index entries land in context.
3. **If `SessionStart` hook is configured:** ingestion runs silently in the background; today's markdown writes become queryable via `/recall`.
4. **Tell Claude: `/resume`** (or paste literally: `Read ~/.claude/checkpoint.md and orient on what was in flight.`).
5. **Claude reads** `checkpoint.md` + the most recent `context_pre_compact_*.md` (if exists) + `git log --oneline -10` from both repos → produces a 1-page summary.
6. **You confirm or correct the framing.** Continue from where you left off.

## Scenario B — Mid-session, after autocompact fired

1. **You'll likely see compaction-related context drop** — Claude's responses feel less grounded in earlier decisions.
2. **PreCompact hook should have fired** automatically (if configured) → the snapshot lives at `~/.claude/projects/<slug>/memory/context_pre_compact_<session_id>.md`.
3. **Tell Claude: `/resume`** to re-orient on what was lost.
4. **`/memory lint`** to sanity-check the markdown layer is intact.

## Scenario C — Different machine (full restart)

```bash
# 1. (Optional) Clone your own private memory/config repo as ~/.claude
#    Skip this step if you don't keep one — `~/.claude` will be created fresh.
git clone <your-private-claude-repo> ~/.claude

# 2. Clone the public toolkit
git clone git@github.com:couldbeme/claude-second-brain.git ~/Dev/claude-second-brain

# 3. Run installer (creates symlinks for commands/agents/skills)
cd ~/Dev/claude-second-brain && bash install.sh

# 4. Set up memory-mcp venv
bash ~/Dev/claude-second-brain/memory-mcp/setup.sh

# 5. (Optional) Import sqlite memories from sync file if present
cd ~/Dev/claude-second-brain/memory-mcp && source .venv/bin/activate && python sync.py import

# 6. Open Claude Code in any project dir → continue from Scenario A step 4
```

---

## Setup (one-time): hooks for auto-trigger

Add to `~/.claude/settings.json` under the root object, alongside `permissions` and `mcpServers`:

```json
"hooks": {
  "SessionStart": [{
    "hooks": [{
      "type": "command",
      "command": "<HOME>/.claude/memory-mcp/.venv/bin/python3 <HOME>/Dev/claude-second-brain/memory-mcp/ingest_markdown.py --apply --quiet"
    }]
  }],
  "PreCompact": [{
    "hooks": [{
      "type": "command",
      "command": "<HOME>/.claude/memory-mcp/.venv/bin/python3 <HOME>/Dev/claude-second-brain/memory-mcp/precompact_hook.py"
    }]
  }]
}
```

**Replace `<HOME>` with your absolute home path** (e.g. `/home/<user>` on Linux, `/Users/<user>` on macOS). Run `echo $HOME` to find it. After this is in place, both auto-fire on every session.

To verify the hooks fired:
- `SessionStart`: `head -3 ~/.claude/plans/ingest-dryrun-report.md` (or apply-report) — recent timestamp = fired
- `PreCompact`: after a `/compact`, `ls ~/.claude/projects/<slug>/memory/context_pre_compact_*.md` — file exists

---

## What auto-loads ALREADY (no setup needed)

When Claude Code starts a session in any project dir:
1. `~/.claude/CLAUDE.md` — global rules (TDD, security, etc.; today's rule 9: never re-read unchanged files)
2. `~/.claude/projects/<slug>/memory/MEMORY.md` — index of all auto-memory files

Sample MEMORY.md auto-load includes (today's session):
- User Profile (communication-style preferences, persona signals)
- Procedural-mode slip feedback memory
- Don't-undersell-us framing rule
- NEVER re-read unchanged files (rule 9)
- Session learnings (10+ gotchas)
- Research notes (Karpathy convergence, OpenClaw, landscape)
- Wishlist (with shipped markers on /memory lint, /context-status)

Each is a one-line index entry — Claude reads the file content only when relevant to the task.

---

## What's preserved on disk vs what's NOT

**Preserved (compaction-survivable):**
- All markdown auto-memory files
- All `~/.claude/plans/*.md`
- All `~/Dev/claude-second-brain/docs/*.md`
- `~/.claude/checkpoint.md`
- All git commits in both repos
- Skills + commands (file-system live; symlinks)
- Rows in `memory.db` reflect prior import plus auto-memory ingestion

**NOT preserved (lost on /compact):**
- The conversational threading — the *reasoning chain* between decisions
- Voice + energy match built up over the session
- Specific exchanges, callbacks, in-the-moment phrasings

The full continuity-preservation system (per `~/.claude/plans/oss-launch-phase-continuity.md`) is the planned `/team` build that addresses the "NOT preserved" gap. Until then, `/resume` + checkpoint cover most of the loss.

---

## When in doubt

```
1. /resume       ← always first; gives you the lay of the land
2. /memory lint  ← if anything feels wrong, run this to surface drift
3. /context-status ← check if you're approaching compact again
```

Three commands, in that order. Most resume situations resolve in those three steps.
