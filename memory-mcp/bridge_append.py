"""Bridge append CLI — append a structural entry to per-project session_bridge.md.

Claude invokes this via Bash during a session to populate the bridge journal,
which precompact_hook.py reads at compaction time to build the continuity snapshot.

Usage:
    bridge_append.py [--memory-dir PATH] TYPE PAYLOAD

TYPE must be one of: DECISION | THREAD-OPEN | THREAD-CLOSE | INFLIGHT | VOICE | PERSONA
PAYLOAD is capped at 500 chars and newlines are stripped (enforced by core function).

Exit codes:
    0  — entry appended successfully
    1  — write failed (invalid type, IO error) or path-traversal blocked
    2  — argparse error (bad arguments)
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Path helpers — duplicated from precompact_hook.py (3-line function).
# Cross-ref: memory-mcp/precompact_hook.py::_slugify_cwd / _resolve_memory_dir.
# Duplication preferred over a shared module: would require changing imports in
# precompact_hook.py + boilerplate > 15 LOC of churn for a 3-line helper.
# ---------------------------------------------------------------------------

_SAFE_ID_RE = re.compile(r"[^a-zA-Z0-9_\-]")
_PROJECTS_ROOT = Path.home() / ".claude" / "projects"


def _slugify_cwd(cwd: str) -> str:
    """Replicate Claude Code's project-dir slug: replace / with -."""
    safe = (cwd or "unknown").replace("/", "-")
    return _SAFE_ID_RE.sub("_", safe)[:255]


def _resolve_memory_dir(cwd: str) -> Path:
    """Compute the memory dir from cwd. Falls back to unknown/ on bad input."""
    slug = _slugify_cwd(cwd)
    if not slug:
        slug = "unknown"
    target = _PROJECTS_ROOT / slug / "memory"
    try:
        if not target.resolve().is_relative_to(_PROJECTS_ROOT.resolve()):
            target = _PROJECTS_ROOT / "unknown" / "memory"
    except (OSError, ValueError):
        target = _PROJECTS_ROOT / "unknown" / "memory"
    target.mkdir(parents=True, exist_ok=True)
    return target


def _guard_explicit_memory_dir(raw: str) -> Path:
    """Validate an explicit --memory-dir path against _PROJECTS_ROOT.

    If the resolved path is outside _PROJECTS_ROOT, falls back to
    _PROJECTS_ROOT/unknown/memory/ — matching _resolve_memory_dir semantics.
    """
    target = Path(raw)
    try:
        resolved = target.resolve()
        projects_resolved = _PROJECTS_ROOT.resolve()
        if not resolved.is_relative_to(projects_resolved):
            # Path traversal guard: outside _PROJECTS_ROOT — use safe fallback.
            target = _PROJECTS_ROOT / "unknown" / "memory"
    except (OSError, ValueError):
        target = _PROJECTS_ROOT / "unknown" / "memory"
    target.mkdir(parents=True, exist_ok=True)
    return target


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="bridge_append.py",
        description=(
            "Append a structural entry to the per-project session_bridge.md. "
            "Claude invokes this during a session via Bash to populate the bridge journal."
        ),
    )
    parser.add_argument(
        "--memory-dir",
        metavar="PATH",
        default=None,
        help=(
            "Override per-project memory dir. "
            "Must be within ~/.claude/projects/ or will fall back to unknown/. "
            "Default: derive from $PWD."
        ),
    )
    parser.add_argument(
        "type",
        metavar="TYPE",
        help="One of DECISION | THREAD-OPEN | THREAD-CLOSE | INFLIGHT | VOICE | PERSONA",
    )
    parser.add_argument(
        "payload",
        metavar="PAYLOAD",
        help="Structured text (capped at 500 chars, newlines stripped by core).",
    )
    return parser


def main() -> int:
    """Parse args, resolve memory dir, delegate to append_bridge_entry(). Return exit code."""
    parser = _build_parser()
    args = parser.parse_args()

    # Resolve memory directory.
    if args.memory_dir is not None:
        memory_dir = _guard_explicit_memory_dir(args.memory_dir)
    else:
        import os
        cwd = os.environ.get("PWD", "") or os.getcwd()
        memory_dir = _resolve_memory_dir(cwd)

    # Lazy-import so import failures exit cleanly with code 1 rather than crashing.
    try:
        # Ensure the memory-mcp directory is on sys.path for sibling import.
        _scripts_dir = Path(__file__).resolve().parent
        if str(_scripts_dir) not in sys.path:
            sys.path.insert(0, str(_scripts_dir))
        from continuity_dump import append_bridge_entry  # noqa: PLC0415
    except ImportError as exc:
        print(f"bridge_append: import error — {exc}", file=sys.stderr)
        return 1

    success = append_bridge_entry(
        memory_dir=memory_dir,
        entry_type=args.type,
        payload=args.payload,
    )

    if not success:
        print("bridge_append: write failed", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(1)
    except SystemExit:
        raise
    except Exception as exc:  # noqa: BLE001
        print(f"bridge_append: unexpected error — {exc}", file=sys.stderr)
        sys.exit(1)
