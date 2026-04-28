"""Continuity snapshot writer — invoked by precompact_hook.py.

Reads session_bridge.md from memory_dir, formats a content-rich continuity
snapshot, and writes it atomically.

Privacy contract: NEVER reads transcript message bodies. All content sourced
from session_bridge.md entries (metadata/structural writes only) and filesystem
metadata (git log, plan file mtimes). No LLM in the loop.

Exit contract: all public functions swallow exceptions — callers must not be
blocked by failures here.
"""

from __future__ import annotations

import fcntl
import os
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

VALID_ENTRY_TYPES = frozenset(
    ["DECISION", "THREAD-OPEN", "THREAD-CLOSE", "INFLIGHT", "VOICE", "PERSONA"]
)

# Defense-in-depth: cap payload to prevent prompt-injection-induced large blob
# writes that would echo into every future snapshot.
_MAX_PAYLOAD_LEN = 500


def _to_tilde_path(p: Path) -> str:
    """Render a path with home-dir prefix replaced by '~'. Prevents leaking the
    OS username via absolute paths in the snapshot.
    """
    home_str = str(Path.home())
    s = str(p)
    if s.startswith(home_str):
        return "~" + s[len(home_str):]
    return s

# Regex: [YYYY-MM-DDTHH:MM:SSZ] [TYPE] payload
_ENTRY_RE = re.compile(
    r"^\[(?P<timestamp>\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z)\]\s+"
    r"\[(?P<type>[A-Z\-]+)\]\s+"
    r"(?P<payload>.*)$"
)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def write_continuity_snapshot(
    session_id: str,
    cwd: str,
    memory_dir: Path,
) -> bool:
    """Read session_bridge.md and write continuity_pre_compact_<session_id>.md.

    Returns True if written successfully, False if skipped or failed.
    Atomic write via .tmp sibling + os.replace(). Never raises.

    Privacy: reads ONLY memory_dir/session_bridge.md. Never reads .jsonl files.
    """
    try:
        bridge_path = memory_dir / "session_bridge.md"
        if not bridge_path.exists():
            return False

        entries = _read_bridge_entries(bridge_path)

        now_utc = datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        # Gather git log lines for cross-references (pure metadata, no diffs)
        repo_paths = [
            Path.home() / "Dev" / "claude-second-brain",
            Path.home() / ".claude",
        ]
        git_lines = _capture_git_log(repo_paths, n=5)

        snapshot_content = _format_snapshot(
            entries=entries,
            git_lines=git_lines,
            session_id=session_id,
            cwd=cwd,
            timestamp=now_utc,
            memory_dir=memory_dir,
        )

        output_path = memory_dir / f"continuity_pre_compact_{session_id}.md"
        tmp_path = output_path.with_suffix(".md.tmp")

        # Clear any orphan .tmp from a prior crashed write before our own.
        tmp_path.unlink(missing_ok=True)

        tmp_path.write_text(snapshot_content, encoding="utf-8")
        os.replace(tmp_path, output_path)  # atomic on POSIX

        return True

    except Exception:  # noqa: BLE001 — never raise; callers must not be blocked
        return False


def append_bridge_entry(
    memory_dir: Path,
    entry_type: str,
    payload: str,
) -> bool:
    """Append a single line to session_bridge.md in memory_dir.

    entry_type: one of DECISION | THREAD-OPEN | THREAD-CLOSE | INFLIGHT | VOICE | PERSONA
    payload: the text after the type tag (must NOT contain raw message body content)

    Atomic: uses file locking (fcntl on POSIX). Returns True on success.
    Never raises — caller must not be blocked.
    """
    try:
        if entry_type not in VALID_ENTRY_TYPES:
            return False

        bridge_path = memory_dir / "session_bridge.md"
        memory_dir.mkdir(parents=True, exist_ok=True)

        # Sanitize payload: strip line breaks (preserve one-entry-per-line invariant)
        # then cap at _MAX_PAYLOAD_LEN to prevent unbounded growth.
        safe_payload = (payload or "").replace("\n", " ").replace("\r", " ")[:_MAX_PAYLOAD_LEN]

        timestamp = datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        line = f"[{timestamp}] [{entry_type}] {safe_payload}\n"

        # Open in append mode; create if absent.
        # fcntl.flock provides exclusive write lock for the append.
        with open(bridge_path, "a", encoding="utf-8") as fh:
            fcntl.flock(fh, fcntl.LOCK_EX)
            try:
                fh.write(line)
                fh.flush()
                os.fsync(fh.fileno())
            finally:
                fcntl.flock(fh, fcntl.LOCK_UN)

        return True

    except Exception:  # noqa: BLE001 — never raise
        return False


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _read_bridge_entries(bridge_path: Path) -> list[dict]:
    """Parse session_bridge.md into structured dicts.

    Returns list of {"timestamp", "type", "payload"} dicts.
    Returns [] on any parse or IO error. Never raises.

    Privacy: reads ONLY the bridge file — no .jsonl access ever.
    """
    try:
        text = bridge_path.read_text(encoding="utf-8")
    except Exception:  # noqa: BLE001
        return []

    results: list[dict] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        m = _ENTRY_RE.match(stripped)
        if m:
            results.append(
                {
                    "timestamp": m.group("timestamp"),
                    "type": m.group("type"),
                    "payload": m.group("payload"),
                }
            )
    return results


def _capture_git_log(repo_paths: list[Path], n: int = 5) -> list[str]:
    """Run `git log --oneline -N` on each repo. Returns list of one-liner strings.

    Shells out via subprocess with timeout=5s. Returns [] on any failure.
    Privacy: captures commit message text (public metadata), not file diffs.
    """
    lines: list[str] = []
    for repo in repo_paths:
        try:
            result = subprocess.run(
                ["git", "-C", str(repo), "log", f"--oneline", f"-{n}"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                for log_line in result.stdout.splitlines():
                    stripped = log_line.strip()
                    if stripped:
                        lines.append(f"{repo.name}: {stripped}")
        except Exception:  # noqa: BLE001 — subprocess timeout, missing git, etc.
            pass
    return lines


def _format_snapshot(
    entries: list[dict],
    git_lines: list[str],
    session_id: str,
    cwd: str,
    timestamp: str,
    memory_dir: Path,
) -> str:
    """Format the continuity snapshot markdown from structured inputs.

    Pure function — no IO. Takes pre-parsed entries and pre-fetched git lines.
    Returns the full markdown string.

    Privacy: constructs output from structured entry metadata only. Never
    interpolates raw message body content.
    """
    # Partition entries by type
    decisions = [e for e in entries if e["type"] == "DECISION"][:10]
    threads_open: dict[str, dict] = {}
    for e in entries:
        if e["type"] == "THREAD-OPEN":
            tid = e["payload"].split("|")[0].strip()
            threads_open[tid] = e
        elif e["type"] == "THREAD-CLOSE":
            tid = e["payload"].strip()
            threads_open.pop(tid, None)
    open_threads = list(threads_open.values())

    # Latest INFLIGHT only
    inflights = [e for e in entries if e["type"] == "INFLIGHT"]
    latest_inflight = inflights[-1] if inflights else None

    # Voice signals
    voices = [e for e in entries if e["type"] == "VOICE"]

    # Persona deltas
    personas = [e for e in entries if e["type"] == "PERSONA"]

    # Token metrics — no transcript reads; use zero baseline (honest about no-JSONL policy)
    tokens_used = 0
    tokens_max = 200_000
    percent_used = 0.0
    model = "claude-sonnet-4-6"

    bridge_entry_count = len(entries)

    # Sanitize cwd for safe interpolation
    cwd_safe = (cwd or "unknown").splitlines()[0][:512]

    # --- Build sections ---

    # Decisions section
    if decisions:
        decisions_lines = "\n".join(
            f"- [{e['timestamp']}] {e['payload']}" for e in decisions
        )
    else:
        decisions_lines = "- (none recorded this session)"

    # Open threads section
    if open_threads:
        threads_lines = "\n".join(
            f"- [open] {e['payload']} | since: {e['timestamp']}" for e in open_threads
        )
    else:
        threads_lines = "- (no open threads)"

    # In-flight state section
    if latest_inflight:
        inflight_lines = latest_inflight["payload"]
    else:
        inflight_lines = "- (no in-flight state recorded)"

    # Voice signals section (metadata only — enum values, no message bodies)
    if voices:
        voice_lines = "\n".join(
            f"- [{e['timestamp']}] {e['payload']}" for e in voices
        )
    else:
        voice_lines = "- (no voice signals recorded)"

    # Persona deltas section
    if personas:
        persona_lines = "\n".join(
            f"- [{e['timestamp']}] {e['payload']}" for e in personas
        )
    else:
        persona_lines = "- (no persona deltas recorded)"

    # Git cross-references
    if git_lines:
        git_section = "\n".join(f"- {ln}" for ln in git_lines)
    else:
        git_section = "- (git log unavailable)"

    # Plan files cross-reference
    plans_dir = Path.home() / ".claude" / "plans"
    recent_plans: list[str] = []
    try:
        if plans_dir.is_dir():
            plan_files = sorted(
                plans_dir.glob("*.md"),
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            )
            # Use basename only (not absolute path) — avoids leaking the OS
            # username and home-dir layout via the snapshot.
            recent_plans = [p.name for p in plan_files[:3]]
    except Exception:  # noqa: BLE001
        pass
    plans_section = (
        "\n".join(f"- {p}" for p in recent_plans)
        if recent_plans
        else "- (no plan files found)"
    )

    # Cross-reference the actual bridge journal in the same memory dir we wrote to.
    # Render with ~ prefix to avoid leaking the OS username.
    bridge_ref = _to_tilde_path(memory_dir / "session_bridge.md")
    checkpoint_ref = _to_tilde_path(Path.home() / ".claude" / "checkpoint.md")

    return f"""\
---
type: continuity-pre-compact
session_id: {session_id}
timestamp_utc: {timestamp}
cwd: {cwd_safe}
tokens_used: {tokens_used}
tokens_max: {tokens_max}
percent_used: {percent_used:.4f}
model: {model}
bridge_entry_count: {bridge_entry_count}
---

# Continuity Pre-Compact Snapshot

**Captured at:** {timestamp}
**Session ID:** {session_id}
**Working directory:** {cwd_safe}

## Decisions (this session)
<!-- Max 10 entries. Source: session_bridge.md decision entries. -->
{decisions_lines}

## Open Threads
<!-- Source: session_bridge.md thread entries with status=open. -->
{threads_lines}

## In-Flight State
<!-- Source: session_bridge.md inflight entry (latest only). -->
{inflight_lines}

## Voice Signals (metadata-only)
<!-- Source: session_bridge.md voice entries. NO message body content. -->
{voice_lines}

## Persona Deltas (this session)
<!-- Observations approaching or crossing 3-occurrence threshold. -->
{persona_lines}

## Cross-References
- checkpoint: {checkpoint_ref}
- recent-commits:
{git_section}
- active-plans:
{plans_section}
- bridge-journal: {bridge_ref}
"""
