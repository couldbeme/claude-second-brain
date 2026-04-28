"""UserPromptSubmit hook — togglable /metaprompt scaffolding.

Intercepts every prompt and (depending on session toggle state) either:
  off   — passthrough, no envelope
  fast  — template-only injection (<150 tokens, <50ms); structural scaffolding
          around the raw prompt. NO LLM call.
  deep  — full /metaprompt-shaped wrap (<300 tokens); injects the metaprompt
          skill body so Claude applies prompt engineering before executing.

Stop-hook safety (claude-mem #987):
  - Exit 0 always.
  - stdout contains ONLY the additionalContext JSON envelope (when applicable).
  - BaseException catch at outermost scope.
  - Privacy floor: no user prompt content logged to disk.

State resolution (first wins):
  1. METAPROMPT_PROJECT_STATE env var → file path
  2. ~/.claude/projects/<slug>/.metaprompt-state  (per-project)
  3. METAPROMPT_GLOBAL_STATE env var → file path
  4. ~/.claude/.metaprompt-mode  (global)
  5. default: off

Bypass prefixes: *, /, # — strip prefix, pass raw prompt through regardless of mode.

Output envelope:
  {"hookSpecificOutput": {"hookEventName": "UserPromptSubmit",
                          "additionalContext": <str>}}
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_BYPASS_PREFIXES = ("*", "/", "#")
_VALID_MODES = frozenset({"off", "fast", "deep"})
_DEFAULT_MODE = "off"

_SAFE_ID_RE = re.compile(r"[^a-zA-Z0-9_\-]")
_PROJECTS_ROOT = Path.home() / ".claude" / "projects"
_GLOBAL_STATE_PATH = Path.home() / ".claude" / ".metaprompt-mode"

# ---------------------------------------------------------------------------
# Path helpers — reuse _slugify_cwd pattern from precompact_hook.py
# ---------------------------------------------------------------------------


def _slugify_cwd(cwd: str) -> str:
    """Replicate Claude Code's project-dir slug: replace / with -."""
    # Strip newlines first (injection guard) then sanitize
    safe = (cwd or "unknown").splitlines()[0][:512].replace("/", "-")
    return _SAFE_ID_RE.sub("_", safe)[:255] or "unknown"


def _project_state_path(cwd: str) -> Path:
    """Return per-project state file path. Never escapes ~/.claude/projects/."""
    slug = _slugify_cwd(cwd)
    candidate = _PROJECTS_ROOT / slug / ".metaprompt-state"
    # Defense-in-depth: ensure resolved path stays within _PROJECTS_ROOT
    try:
        if not candidate.resolve().is_relative_to(_PROJECTS_ROOT.resolve()):
            return _PROJECTS_ROOT / "unknown" / ".metaprompt-state"
    except (OSError, ValueError):
        return _PROJECTS_ROOT / "unknown" / ".metaprompt-state"
    return candidate


# ---------------------------------------------------------------------------
# State resolution
# ---------------------------------------------------------------------------


def _read_mode_file(path: Path) -> str | None:
    """Read a state file, return normalized mode string or None if unusable."""
    try:
        text = path.read_text(encoding="utf-8").strip().lower()
        if text in _VALID_MODES:
            return text
    except (OSError, PermissionError):
        pass
    return None


def _resolve_mode(cwd: str) -> str:
    """Resolve toggle mode with explicit priority chain."""
    # 1. METAPROMPT_PROJECT_STATE env override (test seam + explicit per-project)
    proj_env = os.environ.get("METAPROMPT_PROJECT_STATE")
    if proj_env:
        mode = _read_mode_file(Path(proj_env))
        if mode is not None:
            return mode

    # 2. Per-project state file derived from cwd slug
    proj_path = _project_state_path(cwd)
    mode = _read_mode_file(proj_path)
    if mode is not None:
        return mode

    # 3. METAPROMPT_GLOBAL_STATE env override (test seam + explicit global)
    global_env = os.environ.get("METAPROMPT_GLOBAL_STATE")
    if global_env:
        mode = _read_mode_file(Path(global_env))
        if mode is not None:
            return mode

    # 4. Global state file
    mode = _read_mode_file(_GLOBAL_STATE_PATH)
    if mode is not None:
        return mode

    return _DEFAULT_MODE


# ---------------------------------------------------------------------------
# Template scaffolds
# ---------------------------------------------------------------------------

_FAST_TEMPLATE = """\
[Prompt] {prompt}

## Phases
1. Understand the task and constraints.
2. Implement.
3. Verify.

## Success Criteria
- Task complete per spec.
- No regressions.

## Constraints
- Be precise. No unnecessary output.
"""

_DEEP_TEMPLATE = """\
[Metaprompt scaffold — apply before executing]

Task: {prompt}

## Desired Outcome
State what done looks like. What is the user actually asking for?

## Tools & Approach
Which tools are needed? What could go wrong?

## Success Criteria
Explicit, measurable. How will you verify completion?

## Prompt Engineering Applied
- Role defined. Constraints explicit. Phases structured.
- Edge cases handled. Token-efficient output.

## Execute
Now carry out the task with the above framing.
"""


def _apply_fast(prompt: str) -> str:
    return _FAST_TEMPLATE.format(prompt=prompt)


def _apply_deep(prompt: str) -> str:
    return _DEEP_TEMPLATE.format(prompt=prompt)


# ---------------------------------------------------------------------------
# Envelope builder
# ---------------------------------------------------------------------------


def _envelope(context: str) -> dict:
    return {
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": context,
        }
    }


# ---------------------------------------------------------------------------
# Core
# ---------------------------------------------------------------------------


def run(stdin_text: str) -> tuple[str, int]:
    """Main logic. Returns (stdout_text, exit_code).

    stdout_text is either a JSON envelope string or empty string.
    exit_code is always 0.
    """
    # Parse input — any failure → passthrough, exit 0
    try:
        event = json.loads(stdin_text) if stdin_text.strip() else {}
    except (json.JSONDecodeError, ValueError) as exc:
        print(f"metaprompt_hook: JSON parse error — {exc}", file=sys.stderr)
        return ("", 0)

    prompt: str = event.get("prompt", "")
    cwd: str = event.get("cwd", "")

    # Bypass prefixes — strip prefix, pass through raw (no scaffolding)
    if prompt and prompt[0] in _BYPASS_PREFIXES:
        stripped = prompt[1:].lstrip()
        # Still emit an envelope so Claude sees the cleaned prompt
        return (json.dumps(_envelope(stripped)), 0)

    mode = _resolve_mode(cwd)

    if mode == "off":
        return ("", 0)
    elif mode == "fast":
        context = _apply_fast(prompt)
        return (json.dumps(_envelope(context)), 0)
    elif mode == "deep":
        context = _apply_deep(prompt)
        return (json.dumps(_envelope(context)), 0)
    else:
        # Unknown mode — passthrough
        return ("", 0)


if __name__ == "__main__":
    try:
        stdin_text = sys.stdin.read()
        output, code = run(stdin_text)
        if output:
            print(output, end="")
        sys.exit(code)
    except BaseException:  # noqa: BLE001 — Stop-hook safety: never escape, exit 0 always
        sys.exit(0)
