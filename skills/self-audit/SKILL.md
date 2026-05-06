---
description: Deterministic toolkit health checker — finds underused Claude Code platform features in commands/, agents/, skills/, and CLAUDE.md.template
argument-hint: Optional flags (e.g., "--rules R-CMD-1,R-AGENT-3", "--format markdown", "--no-session")
---

# /self-audit — Toolkit Health Checker

Audits this toolkit's own artifacts against a static feature catalog and reports which Claude Code platform primitives are underused, in which specific files, with effort and impact estimates.

The driving question: *which platform primitives does this toolkit underuse, and in which files?*

No LLM calls. No `.jsonl` body reads. Every rule is a regex or structural check. Deterministic — same input, same output.

## What it checks

| Rule | Target | What fires |
|---|---|---|
| R-CMD-1 | commands/ | `argument-hint` in frontmatter but no `$ARGUMENTS` in body |
| R-CMD-2 | commands/ | Agent/Task keyword in body but no Phase structure |
| R-CMD-3 | commands/ | `$ARGUMENTS` in body but no `argument-hint` in frontmatter |
| R-CMD-4 | commands/ | `settings.json` mentioned but no hook examples |
| R-CMD-5 | commands/ | "plan" mentioned but no plan-mode reference |
| R-AGENT-1 | agents/ | `model: sonnet` + reasoning keywords → suggest opus |
| R-AGENT-2 | agents/ | `model: sonnet` + lightweight keywords → suggest haiku |
| R-AGENT-3 | agents/ | Shell patterns in body but `Bash` not in tools list |
| R-AGENT-4 | agents/ | Web search/fetch in body but `WebSearch`/`WebFetch` not in tools |
| R-AGENT-5 | agents/ | MCP tool referenced in body but server not in tools list |
| R-SKILL-1 | skills/ | SKILL.md has no `argument-hint` |
| R-SKILL-2 | skills/ | SKILL.md references a script path that doesn't exist |
| R-SKILL-3 | skills/ | SKILL.md describes a hook but hook not in `~/.claude/settings.json` |
| R-TMPL-1 | template | `CLAUDE.md.template` missing PostToolUse mention |
| R-TMPL-2 | template | Template references MCP tool not in `settings.json.template` |
| R-SESSION-1 | session | Context > 75% on sonnet → suggest opus |

## Run it

### Standard (text output)

```bash
~/.claude/memory-mcp/.venv/bin/python3 \
  ~/Dev/claude-second-brain/memory-mcp/self_audit.py
```

Default target: the toolkit root adjacent to `self_audit.py` (script-relative, not hardcoded).

### JSON output (for scripting / CI)

```bash
~/.claude/memory-mcp/.venv/bin/python3 \
  ~/Dev/claude-second-brain/memory-mcp/self_audit.py --json
```

### Markdown report

```bash
~/.claude/memory-mcp/.venv/bin/python3 \
  ~/Dev/claude-second-brain/memory-mcp/self_audit.py --format markdown
```

### Audit a specific target

```bash
~/.claude/memory-mcp/.venv/bin/python3 \
  ~/Dev/claude-second-brain/memory-mcp/self_audit.py \
  --target ~/Dev/some-other-claude-toolkit
```

### Run only selected rules

```bash
~/.claude/memory-mcp/.venv/bin/python3 \
  ~/Dev/claude-second-brain/memory-mcp/self_audit.py \
  --rules R-CMD-1,R-CMD-3,R-AGENT-3
```

### Skip session transcript reads

```bash
~/.claude/memory-mcp/.venv/bin/python3 \
  ~/Dev/claude-second-brain/memory-mcp/self_audit.py --no-session
```

### CI gate (non-zero exit on any finding)

```bash
~/.claude/memory-mcp/.venv/bin/python3 \
  ~/Dev/claude-second-brain/memory-mcp/self_audit.py --exit-on-finding
```

## Severity and effort guide

**Severity:**
- `warn` — structural mismatch likely to cause runtime confusion (broken tool list, missing $ARGUMENTS, dead script path). Fix these.
- `info` — optimization opportunity. The artifact works; this is a "you could do better" signal. Triage by effort.

**Effort:**
- `S` (small) — one-line fix: add a key, fix a path, add a word to a tools list
- `M` (medium) — requires a content addition: a Phase block, a hook example, a documentation section

**Impact:** matches effort in most rules (S fix → S improvement). R-AGENT-5 (MCP wiring) has impact M even at effort S because a missing tool declaration silently breaks agent capability.

## Severity-based triage

| Severity | Effort | Action |
|---|---|---|
| warn | S | Fix immediately — 2 minutes each |
| warn | M | Fix before next toolkit release |
| info | S | Fix in next cleanup pass |
| info | M | Defer unless the file is frequently used |

## Threshold details

- **R-AGENT-1/2:** fires on `model: sonnet` only. Models already set to `opus` or `haiku` are exempt.
- **R-SESSION-1:** fires when `ContextEstimate.percent_used > 0.75` on the most recent session transcript with a `sonnet` model. Use `--no-session` to skip.
- **Unverified catalog features:** rules tied to `status: unverified` catalog entries emit `evidence: "feature unverified — refresh catalog via /whats-new"` and are skipped in rule evaluation. Run Phase 6 A `/whats-new` to refresh.
- **Catalog age:** a header warning is emitted to stderr when `catalog_version` is > 90 days old.

## When to use

- After adding a new command or agent (catches missing frontmatter patterns)
- Before a toolkit release or launch (catches structural gaps)
- When onboarding a new Claude session to this toolkit (surface optimization opportunities)
- After a Claude Code version upgrade (catalog may have new verified features)
- Periodically as a health pulse — add to your weekly `/memory-lint` ritual

## When NOT to use

- To audit user project code — use `/scan` or `/audit` for that
- To detect semantic contradictions between commands — LLM-assisted, deferred to a future phase
- To auto-fix findings — this tool is advisory only; apply changes manually after review
- As the sole CI gate without reviewing findings first — some info-severity findings are intentional design choices

## Privacy guarantees

- Never reads `.jsonl` message bodies. Only `usage.input_tokens` metadata flows through `context_estimator.estimate_from_transcript`.
- Transcripts are never written, copied, or included in report output.
- Use `--no-session` to disable all session reads entirely (R-SESSION-1 skipped).

## Implementation

- Module: `~/Dev/claude-second-brain/memory-mcp/self_audit.py` (stdlib only)
- Catalog: `~/Dev/claude-second-brain/memory-mcp/self_audit_catalog.json` (25 entries, git-tracked)
- Tests: `~/Dev/claude-second-brain/memory-mcp/tests/test_self_audit.py` (42 tests, all green)
- Runs in < 1 second on a 50-file toolkit
