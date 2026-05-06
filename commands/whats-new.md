---
description: Surface new Claude Code platform features since last local check — diffs GitHub releases of anthropics/claude-code into Hooks/Skills/MCP/Settings/Model/CLI buckets
argument-hint: Optional flags (e.g., "--since v2.1.100", "--format markdown", "--no-network", "--quiet")
---

# /whats-new — Platform-Update Surfacer

Run the deterministic update-surfacer module. No LLM analysis — pure regex categorization of GitHub release bodies. Output groups bullets into Hooks, Skills, MCP, Slash Commands, Settings, Model, CLI, Misc.

## Execution

```bash
~/.claude/memory-mcp/.venv/bin/python3 \
  ~/Dev/claude-second-brain/memory-mcp/whats_new_check.py $ARGUMENTS
```

State file at `~/.claude/projects/-Users-macbook-Dev/memory/whats_new_state.json` tracks last-seen releases and ETag for conditional GETs.

## After running

If `/whats-new` surfaces hook / skill / MCP additions you care about, follow up with `/self-audit` — it will re-evaluate catalog entries against the refreshed feature surface and may flip `unverified` evidence to actionable findings.

## See also

- Skill: `~/Dev/claude-second-brain/skills/whats-new/SKILL.md` — full reference
- Companion: `/self-audit` — toolkit health check that consumes this surface
- Design: `docs/WHATS-NEW-DESIGN.md`
