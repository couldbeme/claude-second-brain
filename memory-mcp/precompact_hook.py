"""PreCompact hook for Claude Code.

Invoked by Claude Code's PreCompact hook immediately before session compaction.
Reads the hook event JSON from stdin (which contains session_id, transcript_path,
cwd), runs the context estimator, and writes two snapshot files to the memory
directory.

Exit 0 always — never block compaction under any circumstance.

Hook payload shape (Claude Code v2.x):
    {
        "session_id": "abc123",
        "transcript_path": "/Users/me/.claude/projects/..../session.jsonl",
        "cwd": "/Users/me/Dev/myproject",
        "permission_mode": "...",
        "hook_event_name": "PreCompact"
    }

Output files (both written atomically via .tmp sibling + os.replace()):
    ~/.claude/projects/<slug>/memory/context_pre_compact_<session_id>.md
        Token-metric snapshot: usage %, model, plan-file cross-refs.
        (where <slug> is the absolute cwd with '/' replaced by '-' — Claude Code's
        project-slug convention)
    ~/.claude/projects/<slug>/memory/continuity_pre_compact_<session_id>.md
        Content-rich continuity snapshot: decisions, open threads, in-flight state,
        voice signals, persona deltas. Written by continuity_dump.write_continuity_snapshot()
        after the token-metric snapshot. Swallows all exceptions — exit-0 guarantee
        is preserved regardless of continuity-dump outcome.
"""

from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Resolve context_estimator — handles both direct execution and module import
# ---------------------------------------------------------------------------

_HOOK_DIR = Path(__file__).resolve().parent
if str(_HOOK_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOK_DIR))

from context_estimator import ContextEstimate, estimate_from_transcript  # noqa: E402

# ---------------------------------------------------------------------------
# Path helpers (cwd-derived, OSS-portable)
# ---------------------------------------------------------------------------

_SAFE_ID_RE = re.compile(r"[^a-zA-Z0-9_\-]")
_PROJECTS_ROOT = Path.home() / ".claude" / "projects"


def _slugify_cwd(cwd: str) -> str:
    """Replicate Claude Code's project-dir slug: replace / with -."""
    safe = (cwd or "unknown").replace("/", "-")
    # Cap and strip control chars
    return _SAFE_ID_RE.sub("_", safe)[:255]


def _resolve_memory_dir(cwd: str) -> Path:
    """Compute the memory dir from hook-supplied cwd. Falls back to a generic dir
    if cwd is missing/unusable. Never traverses outside ~/.claude/projects/."""
    slug = _slugify_cwd(cwd)
    if not slug:
        slug = "unknown"
    target = _PROJECTS_ROOT / slug / "memory"
    # Defense-in-depth: ensure the resolved path stays within _PROJECTS_ROOT
    try:
        if not target.resolve().is_relative_to(_PROJECTS_ROOT.resolve()):
            target = _PROJECTS_ROOT / "unknown" / "memory"
    except (OSError, ValueError):
        target = _PROJECTS_ROOT / "unknown" / "memory"
    target.mkdir(parents=True, exist_ok=True)
    return target


def _sanitize_session_id(session_id: str) -> str:
    """Restrict session_id to filesystem-safe chars; cap length."""
    safe = _SAFE_ID_RE.sub("_", session_id or "unknown")[:128]
    return safe or "unknown"


# ---------------------------------------------------------------------------
# Core
# ---------------------------------------------------------------------------

def _read_hook_event(stdin_text: str) -> dict:
    """Parse hook payload from stdin. Returns empty dict on any parse failure."""
    try:
        return json.loads(stdin_text)
    except (json.JSONDecodeError, ValueError):
        return {}


def _build_snapshot(
    estimate: ContextEstimate,
    cwd: str,
    session_id: str,
    memory_dir: Path,
) -> str:
    """Build the markdown snapshot content."""
    now_utc = datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    pct = estimate.percent_used * 100
    # Cap cwd before interpolation — defense against payload-injected long/multi-line strings
    cwd_safe = (cwd or "unknown").splitlines()[0][:512] if cwd else "unknown"

    # Locate checkpoint and plan files relative to memory dir for cross-refs
    checkpoint_path = memory_dir / "checkpoint.md"
    checkpoint_ref = (
        str(checkpoint_path) if checkpoint_path.exists() else "(not found)"
    )

    # Find the most recent plan files under ~/.claude/plans/
    plans_dir = Path.home() / ".claude" / "plans"
    recent_plans: list[str] = []
    if plans_dir.is_dir():
        plan_files = sorted(
            plans_dir.glob("*.md"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        # Basename only — avoids leaking absolute path / OS username via the snapshot.
        recent_plans = [p.name for p in plan_files[:3]]

    plans_section = (
        "\n".join(f"- {p}" for p in recent_plans)
        if recent_plans
        else "- (no plan files found)"
    )

    return f"""---
type: context-pre-compact-snapshot
session_id: {session_id}
timestamp: {now_utc}
---

# Context Pre-Compact Snapshot

**Captured at:** {now_utc}
**Session ID:** {session_id}
**Working directory:** {cwd_safe}

## Token Usage at Compaction

| Field | Value |
|---|---|
| Tokens used | {estimate.tokens_used:,} |
| Tokens max | {estimate.tokens_max:,} |
| Percent used | {pct:.1f}% |
| Threshold | {estimate.threshold.upper()} |
| Model | {estimate.model} |

## Cross-References

**Checkpoint:** {checkpoint_ref}

**Recent plan files:**
{plans_section}

## Compaction-Survival Summary

> This summary is a placeholder. The running Claude session should populate
> these bullets via `/context-save` before or immediately after compaction.

- [ ] Active task and current sub-step were: *(fill via /context-save)*
- [ ] Key decisions made this session: *(fill via /context-save)*
- [ ] Files modified or created: *(fill via /context-save)*
- [ ] Blockers or open questions: *(fill via /context-save)*
- [ ] Next action on resume: *(fill via /context-save)*
"""


def run(stdin_text: str) -> int:
    """Main logic. Separated from __main__ for testability. Returns exit code."""
    event = _read_hook_event(stdin_text)

    raw_session_id: str = event.get("session_id", "unknown")
    session_id = _sanitize_session_id(raw_session_id)  # filesystem-safe, capped
    transcript_path_str: str = event.get("transcript_path", "")
    cwd: str = event.get("cwd", "unknown")
    model: str | None = event.get("model") or os.environ.get("ANTHROPIC_MODEL")

    memory_dir = _resolve_memory_dir(cwd)

    # Use a clearly-non-existent path when no transcript provided — yields zero-token
    # estimate while keeping the snapshot's path field honest about missing data.
    transcript_path = (
        Path(transcript_path_str) if transcript_path_str else Path("__no_transcript__")
    )

    try:
        estimate = estimate_from_transcript(transcript_path, model=model)
    except Exception:  # noqa: BLE001 — never crash the hook
        estimate = ContextEstimate(
            session_id=session_id,
            model=model or "claude-sonnet-4-6",
            tokens_used=0,
            tokens_max=200_000,
            percent_used=0.0,
            threshold="ok",
        )

    try:
        snapshot_content = _build_snapshot(estimate, cwd, session_id, memory_dir)

        output_path = memory_dir / f"context_pre_compact_{session_id}.md"
        tmp_path = output_path.with_suffix(".md.tmp")

        tmp_path.write_text(snapshot_content, encoding="utf-8")
        os.replace(tmp_path, output_path)  # atomic on POSIX
    except Exception:  # noqa: BLE001 — never crash the hook
        pass  # Best-effort write; compaction must not be blocked

    _write_continuity(session_id, cwd, memory_dir)

    return 0  # Always exit 0


def _write_continuity(
    session_id: str,
    cwd: str,
    memory_dir: Path,
) -> None:
    """Attempt continuity dump. Swallows all exceptions — never blocks compaction.

    Stop-hook safety (claude-mem #987): writes to disk only. Never prints to stdout.
    """
    try:
        from continuity_dump import write_continuity_snapshot  # noqa: PLC0415
        write_continuity_snapshot(session_id, cwd, memory_dir)
    except BaseException:  # noqa: BLE001 — Stop-hook safety: never escape, always exit 0
        pass


if __name__ == "__main__":
    # Outer except catches BaseException (KeyboardInterrupt, SystemExit) — exit 0 always
    try:
        stdin_text = sys.stdin.read()
        sys.exit(run(stdin_text))
    except BaseException:  # noqa: BLE001 — exit 0 always; never block compaction
        sys.exit(0)
