# The shared intelligence substrate (DB canonical + Obsidian mirror)

Decision (operator, 2026-06-01): **the belief/memory DB is the canonical store; an
Obsidian vault is a human-facing mirror.** Both, not either — each does what the other
can't.

```
   scouts (X, RSS, Gmail label, web)
            │  write findings
            ▼
   ┌──────────────────────┐        intel_mirror.write_note()
   │  belief/memory DB     │ ───────────────────────────────►  Obsidian vault
   │  (memory-mcp/db.py)   │        (regenerable view)          intel-vault/
   │  CANONICAL            │                                    finding-NNNNNN.md
   └──────────────────────┘
     • dedup (find_conflicts)                                  • graph view
     • contradiction detection                                 • backlinks [[ ]]
     • confidence-weighting                                    • Dataview queries
     • surprise / salience                                     • manual reading
     │
     ▼
   expert panel + /tribunal read the DB
```

## Why the DB is canonical (not Obsidian)

The scouts need three things markdown folders can't give for free, and the belief DB
already ships all three:

- **Dedup** — `db.find_conflicts` / tag-neighbor lookup stops the same X pain-signal
  being re-stored every daily run.
- **Contradiction detection** — two scouts surfacing opposing signal ("market hot" vs
  "market saturating") is itself a finding; the DB flags it (`_detect_contradictions`).
- **Confidence + surprise weighting** — a finding's salience is scored, not flat; the
  panel weighs a 0.9-confidence corroborated signal over a one-off 0.3.

A plain Obsidian vault would re-find duplicates and silently hold conflicting notes.

## Why Obsidian, then (not DB-only)

The DB is a sqlite file — not browsable, not linkable, not yours-to-skim on a Sunday.
The mirror gives the operator a **human surface**: graph view of how niches/pains/
trends interconnect, backlinks, Dataview tables ("show me all trend-scout findings
with signal_strength > 0.7 captured this week"), and notes you can annotate by hand.

## The mirror contract (`memory-mcp/intel_mirror.py`, 14 tests green)

- **Derived + regenerable.** A note is `render_note(db_row)`. Delete the vault, rebuild
  it from the DB. The DB is truth; the note is a view. Never edit a finding in the
  vault expecting it to flow back — it won't.
- **Idempotent by id.** `finding-000042.md` — same DB row always writes the same file;
  re-render overwrites. No duplicate notes when a scout updates a finding.
- **Honesty rails baked in.** No `raw_quote` → the note says **INFERRED**, never invents
  words. No `source_url` → **UNCITED**, never fabricates a link. Provenance + freshness
  + the scout's own confidence ride in frontmatter so a human can weigh each note.

## Vault location (config, not hardcoded)

`OBSIDIAN_VAULT` env var (or the `sinks.obsidian_vault` field in each scout's registry).
Defaults to a local **`./intel-vault/`** inside the worktree — **gitignored**
(findings can contain operator strategy; the vault is local-only by default, per
CLAUDE.md rule 13). Point it at your real Obsidian vault by exporting `OBSIDIAN_VAULT=
/path/to/Vault/startup-intel` — no code change.

## Frontmatter shape (for Obsidian Dataview)

```yaml
---
title: <finding headline>
scout: trend-scout
source_type: x
source_url: https://x.com/.../status/...      # or null  # UNCITED
captured_at: 2026-06-01
signal_strength: 0.72
confidence: 0.8
tags: [trend-scout, b2b-saas, agent-reliability]
mirror_of: belief-db
---
```

Example Dataview query the operator can drop in a dashboard note:

````
```dataview
TABLE signal_strength, confidence, source_url
FROM #trend-scout
WHERE signal_strength > 0.7 AND captured_at >= date(today) - dur(7 days)
SORT signal_strength DESC
```
````
