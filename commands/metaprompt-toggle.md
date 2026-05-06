---
description: Toggle /metaprompt auto-enhancement mode for this session (off | fast | deep | status)
argument-hint: off | fast | deep | status
---

# /metaprompt-toggle

Controls the `UserPromptSubmit` hook that auto-scaffolds your prompts before Claude sees them.

## Argument

`$ARGUMENTS` — one of: `off`, `fast`, `deep`, `status`

## Modes

| Mode | What happens | Cost |
|------|-------------|------|
| `off` | Prompts pass through unchanged (default) | 0 tokens |
| `fast` | Adds Phases / Success Criteria / Constraints template (<150 tokens, no LLM) | ~50 tokens |
| `deep` | Injects full /metaprompt scaffold — desired outcome, tools, success criteria (<300 tokens, no LLM) | ~120 tokens |

Bypass prefix: start any prompt with `*`, `/`, or `#` to skip scaffolding for that message regardless of mode.

## State files

- **Per-project:** `~/.claude/projects/<slug>/.metaprompt-state` — overrides global
- **Global:** `~/.claude/.metaprompt-mode` — applies when no per-project file exists

## Steps

1. Parse `$ARGUMENTS` — must be `off`, `fast`, `deep`, or `status`. If unrecognized, show usage and stop.

2. For `status`:
   - Check per-project state file first, then global.
   - Report current mode and which file is active.
   - Done — do not modify any file.

3. For `off | fast | deep`:
   - Determine project slug: replace `/` with `-` in current working directory path.
   - State file path: `~/.claude/projects/<slug>/.metaprompt-state`
   - Create parent dirs if needed.
   - Write the mode string (e.g. `fast`) to the state file.
   - Confirm: read the file back and report the active mode.

4. Report result in one line:
   ```
   /metaprompt mode → <mode> (per-project: ~/.claude/projects/<slug>/.metaprompt-state)
   ```

## Examples

```
/metaprompt-toggle fast
→ /metaprompt mode → fast (per-project: ~/.claude/projects/-Users-me-Dev-myproject/.metaprompt-state)

/metaprompt-toggle status
→ mode: fast (source: per-project) | file: ~/.claude/projects/-Users-me-Dev-myproject/.metaprompt-state

/metaprompt-toggle off
→ /metaprompt mode → off (per-project: ~/.claude/projects/-Users-me-Dev-myproject/.metaprompt-state)
```

## Notes

- Changes take effect on the **next prompt** — not the current one.
- Per-project state wins over global — set global with:
  `echo "fast" > ~/.claude/.metaprompt-mode`
- Hook script: `mcp-bridge/metaprompt_hook.py`
- Registration: `examples/settings-snippets/metaprompt-hook.json`
