---
description: Show current Claude Code context-window usage as a percentage and recommend whether to /context-save or /compact now (manual companion to the built-in /context command + the PreCompact auto-trigger)
argument-hint: (none — auto-detects current session via hook env vars when available)
---

# /context-status — Manual Context-Window Check

> Companion to the built-in `/context` command. Where `/context` gives a snapshot, `/context-status` adds threshold judgment and ties into the auto-trigger layer so you know whether action is needed before compaction fires silently.

## What it does

Runs `context_estimator.py` against the current session JSONL. The script reads the `usage.input_tokens` field emitted by Claude Code on every turn — no tokenization required, no content ever loaded. It sums those counts, compares to the model's known window size, and returns a percentage plus a threshold tier.

```
session JSONL  →  sum usage.input_tokens  →  percent_used  →  tier + recommendation
```

Session identification uses the `transcript_path` value available in hook env vars when the script is called from a hook. When invoked manually (outside a hook), it falls back to finding the most recently modified JSONL under `~/.claude/projects/<url-encoded-cwd>/`.

Model window is resolved by reading the `model` field from the JSONL metadata and comparing to a local static map:

| Model | Window |
|---|---|
| `claude-sonnet-4*` | 200K |
| `claude-opus-4*` | 200K |
| `claude-haiku-4*` | 200K |
| unknown | 200K (default) |

If tiktoken is installed, character-count estimates are cross-checked. When it is absent the script relies solely on the `usage.input_tokens` fields already present in the transcript. `fallback_used=True` surfaces in output if the heuristic path was taken.

## Output shape

The script emits both a human-readable line and a machine-readable JSON block.

**35% — ok**
```
[CONTEXT-STATUS] 35% used (70K / 200K tokens) — ok, no action needed
{"percent_used": 35.2, "tokens_used": 70400, "tokens_max": 200000, "status": "ok", "session_path": "~/.claude/projects/<slug>/5350.jsonl", "fallback_used": false}
```

**85% — warn**
```
[CONTEXT-STATUS] 85% used (170K / 200K tokens) — warn threshold crossed; run /context-save now
{"percent_used": 85.1, "tokens_used": 170200, "tokens_max": 200000, "status": "warn", "session_path": "~/.claude/projects/<slug>/5350.jsonl", "fallback_used": false}
```

**92% — imminent**
```
[CONTEXT-STATUS] 92% used (184K / 200K tokens) — COMPACTION-IMMINENT; run /context-save immediately
{"percent_used": 92.0, "tokens_used": 184000, "tokens_max": 200000, "status": "imminent", "session_path": "~/.claude/projects/<slug>/5350.jsonl", "fallback_used": false}
```

## When to use

Run `/context-status` at natural break points rather than waiting for compaction to fire mid-task:

- Before starting a long file-editing pass (lots of Read + Edit calls ahead)
- Before spawning subagents (each turn's tool output is large)
- When you sense the session is "heavy" — responses slowing, multi-hop reasoning feeling lossy
- Before any operation whose result you cannot afford to reconstruct (deploy, migration, large refactor)
- As a sanity check after returning to an idle session that has been open for hours

## Threshold tiers

| Usage | Status | Recommendation |
|---|---|---|
| < 60% | `ok` | No action needed |
| 60–80% | `notice` | Heads-up; consider `/context-save` if a long operation is next |
| 80–90% | `warn` | Run `/context-save` now; the `PreCompact` auto-trigger will also fire near here if configured |
| ≥ 90% | `imminent` | Run `/context-save` AND `/compact` immediately; compaction is close |

## Differences from built-in `/context`

| | `/context` (built-in) | `/context-status` (this skill) |
|---|---|---|
| What it shows | Snapshot: token count, loaded CLAUDE.md files, MCP traces | Percentage + tier + action recommendation |
| Judgment | None — raw numbers only | Threshold-aware: tells you what to do |
| Auto-trigger awareness | No | Yes — tier labels align with the `PreCompact` hook thresholds |
| /context-save integration | Manual | Flags the right moment; auto-trigger fires it for you when hooks are configured |
| Invocation | Any time in session | Any time in session, or automatically via hook |

The two commands are complementary. `/context` gives the authoritative snapshot; `/context-status` gives the verdict.

## Privacy note

`context_estimator.py` reads **only the `usage.input_tokens` field** from each JSONL line. It never loads message bodies, tool inputs, tool outputs, or file content. Token counts and model names are metadata — no conversation content is parsed, logged, or transmitted. Transcripts never leave the local machine.

## Setup for the auto-trigger

To have context percentage prepended automatically on every turn, add the following block to `~/.claude/settings.json` under `"hooks"`. This is the configuration proposed in the senior-backend-dev's report:

```json
{
  "hooks": {
    "UserPromptSubmit": [
      {
        "matcher": "*",
        "hooks": [
          {
            "type": "command",
            "command": "~/.claude/memory-mcp/.venv/bin/python3 ~/Dev/claude-second-brain/memory-mcp/context_estimator.py --hook-mode"
          }
        ]
      }
    ],
    "PreCompact": [
      {
        "matcher": "*",
        "hooks": [
          {
            "type": "command",
            "command": "~/.claude/memory-mcp/.venv/bin/python3 ~/Dev/claude-second-brain/memory-mcp/context_estimator.py --trigger-save"
          }
        ]
      }
    ]
  }
}
```

- `--hook-mode`: silent below 60%; prepends `[CONTEXT: X%]` banner at warn+; prepends `[COMPACTION-IMMINENT]` at imminent. Adds latency to every turn — acceptable trade-off at < ~20ms.
- `--trigger-save`: fires only at `PreCompact`; calls `/context-save` automatically before compaction drops fidelity.

`transcript_path` and `session_id` are delivered by Claude Code in the hook environment, so no PID-sniffing is needed when running through hooks.

## Running manually

```bash
~/.claude/memory-mcp/.venv/bin/python3 \
  ~/Dev/claude-second-brain/memory-mcp/context_estimator.py
```

With an explicit session file:

```bash
python3 context_estimator.py \
  --session ~/.claude/projects/<slug>/5350.jsonl
```

JSON-only output (for scripting):

```bash
python3 context_estimator.py --json
```

## Implementation notes

- Pure Python; no dependencies beyond stdlib for the `usage.input_tokens` path
- `tiktoken` is an optional install in `memory-mcp/requirements.txt` — improves estimate cross-check but is not required
- Reuses `~/.claude/memory-mcp/.venv` — no new venv
- Tests at `~/Dev/claude-second-brain/memory-mcp/tests/test_context_estimator.py`

## Roadmap

- **v0.2** — rolling per-turn delta to detect sudden token spikes (large file reads, image inputs)
- **v0.2** — 1M window support once the `sonnet[1m]` tier is detectable from JSONL metadata
- **v0.3** — `/context-save` auto-call from `autosave` tier without requiring `PreCompact` hook
