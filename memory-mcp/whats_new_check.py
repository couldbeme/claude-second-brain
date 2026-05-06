"""Surface new Claude Code platform features since last local check.

Source: https://api.github.com/repos/anthropics/claude-code/releases
Stdlib only — urllib + json + re. Mirrors self_audit.py zero-deps stance.

Public API:
    ReleaseEntry, State, FetchResult, DiffReport — dataclasses
    load_state, save_state, fetch_releases, diff_releases, categorize_bullet,
    format_text, format_markdown, format_json, main

Design: docs/WHATS-NEW-DESIGN.md
Recon:  ~/.claude/projects/-Users-macbook-Dev-claude-second-brain/memory/launch_archive/whats-new-recon-2026-05-06.md
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
import urllib.error
import urllib.request
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

SCHEMA_VERSION = 1
DEFAULT_USER_AGENT = "claude-second-brain-whats-new/0.1"
DEFAULT_API_URL = "https://api.github.com/repos/anthropics/claude-code/releases?per_page=20"
DEFAULT_TIMEOUT = 10
SEEN_RELEASES_CAP = 200

DEFAULT_STATE_PATH = (
    Path.home()
    / ".claude"
    / "projects"
    / "-Users-macbook-Dev"
    / "memory"
    / "whats_new_state.json"
)


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class ReleaseEntry:
    tag: str
    published_at: str
    body: str = ""
    html_url: str = ""


@dataclass
class State:
    schema_version: int = SCHEMA_VERSION
    last_checked_at: str = ""
    last_checked_version: str = ""
    last_etag: str = ""
    seen_releases: list[dict] = field(default_factory=list)


@dataclass
class FetchResult:
    releases: list[ReleaseEntry] = field(default_factory=list)
    etag: str = ""
    status: str = "ok"   # ok | not_modified | offline | rate_limited | upstream_error
    detail: str = ""     # human-readable note for offline/error states


@dataclass
class DiffReport:
    new_releases: list[ReleaseEntry] = field(default_factory=list)
    buckets: dict[str, list[str]] = field(default_factory=dict)
    skipped: list[str] = field(default_factory=list)
    fetch_status: str = "ok"
    fetch_detail: str = ""


# ---------------------------------------------------------------------------
# Categorization
# ---------------------------------------------------------------------------

# Order matters: first match wins. Misc catches unmatched.
BUCKET_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("Hooks", re.compile(
        r"\b(hook|PreCompact|PostToolUse|UserPromptSubmit|SessionStart|Stop hook)\b",
        re.IGNORECASE,
    )),
    ("Skills", re.compile(r"\b(skill|SKILL\.md)\b", re.IGNORECASE)),
    ("MCP", re.compile(r"\b(mcp server|mcp__|mcp\b)", re.IGNORECASE)),
    ("Slash Commands", re.compile(
        r"(slash command|/[a-z][a-z0-9-]+\s+command|\bcommand:\s)",
        re.IGNORECASE,
    )),
    ("Settings", re.compile(
        r"\b(settings\.json|settings file|config flag|setting:)\b",
        re.IGNORECASE,
    )),
    ("Model", re.compile(
        r"\b(opus|sonnet|haiku|claude-(?:opus|sonnet|haiku)-\d|model:\s)",
        re.IGNORECASE,
    )),
    ("CLI", re.compile(r"(--[a-z][a-z0-9-]+\b|\bclaude --)", re.IGNORECASE)),
]


def categorize_bullet(text: str) -> str:
    """Return the bucket name for a release-body bullet. Misc if no match."""
    for bucket, pattern in BUCKET_PATTERNS:
        if pattern.search(text):
            return bucket
    return "Misc"


_BULLET_RE = re.compile(r"^\s*[-*]\s+(.+?)\s*$", re.MULTILINE)


def extract_bullets(body: str) -> list[str]:
    """Extract markdown bullets from a release body. Empty list if none."""
    if not body:
        return []
    return [m.group(1) for m in _BULLET_RE.finditer(body)]


# ---------------------------------------------------------------------------
# State file
# ---------------------------------------------------------------------------

def load_state(path: Path) -> State:
    """Load state from disk. Returns default State if missing.

    Raises ValueError if the file exists but is malformed JSON — never
    silently overwrites corrupt state.
    """
    if not path.exists():
        return State()
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise ValueError(f"state file corrupt at {path}: {e}") from e

    return State(
        schema_version=int(raw.get("schema_version", SCHEMA_VERSION)),
        last_checked_at=str(raw.get("last_checked_at", "")),
        last_checked_version=str(raw.get("last_checked_version", "")),
        last_etag=str(raw.get("last_etag", "")),
        seen_releases=list(raw.get("seen_releases", [])),
    )


def save_state(path: Path, state: State) -> None:
    """Atomic write: temp-file + os.replace."""
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = asdict(state)
    # FIFO rotation
    if len(payload["seen_releases"]) > SEEN_RELEASES_CAP:
        payload["seen_releases"] = payload["seen_releases"][-SEEN_RELEASES_CAP:]
    fd, tmp_path = tempfile.mkstemp(
        prefix=path.name + ".",
        suffix=".tmp",
        dir=str(path.parent),
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, sort_keys=True)
        os.replace(tmp_path, path)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


# ---------------------------------------------------------------------------
# Fetch
# ---------------------------------------------------------------------------

def fetch_releases(
    url: str = DEFAULT_API_URL,
    etag: str = "",
    timeout: int = DEFAULT_TIMEOUT,
    user_agent: str = DEFAULT_USER_AGENT,
    opener: Any = None,
) -> FetchResult:
    """GET releases from GitHub. Returns FetchResult.

    `opener` is for tests — pass a mock callable that takes (Request, timeout)
    and returns a urlopen-like context manager. Defaults to urllib.request.urlopen.
    """
    if opener is None:
        opener = urllib.request.urlopen

    headers = {"User-Agent": user_agent, "Accept": "application/vnd.github+json"}
    if etag:
        headers["If-None-Match"] = etag

    req = urllib.request.Request(url, headers=headers)

    try:
        with opener(req, timeout=timeout) as resp:
            status = getattr(resp, "status", 200)
            if status == 304:
                return FetchResult(status="not_modified")
            data = resp.read()
            new_etag = resp.headers.get("ETag", "") if hasattr(resp, "headers") else ""
    except urllib.error.HTTPError as e:
        if e.code == 304:
            return FetchResult(status="not_modified")
        if e.code == 403:
            reset = ""
            if hasattr(e, "headers") and e.headers is not None:
                reset = e.headers.get("X-RateLimit-Reset", "") or ""
            return FetchResult(status="rate_limited", detail=f"reset at {reset}")
        if 500 <= e.code < 600:
            return FetchResult(status="upstream_error", detail=f"HTTP {e.code}")
        return FetchResult(status="upstream_error", detail=f"HTTP {e.code}")
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        return FetchResult(status="offline", detail=str(e))

    try:
        payload = json.loads(data)
    except json.JSONDecodeError as e:
        return FetchResult(status="upstream_error", detail=f"malformed JSON: {e}")

    if not isinstance(payload, list):
        return FetchResult(status="upstream_error", detail="expected array, got object")

    releases = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        tag = item.get("tag_name") or item.get("name") or ""
        if not tag:
            continue
        releases.append(ReleaseEntry(
            tag=tag,
            published_at=str(item.get("published_at", "")),
            body=str(item.get("body", "") or ""),
            html_url=str(item.get("html_url", "")),
        ))

    return FetchResult(releases=releases, etag=new_etag, status="ok")


# ---------------------------------------------------------------------------
# Diff
# ---------------------------------------------------------------------------

def diff_releases(state: State, fetched: list[ReleaseEntry]) -> list[ReleaseEntry]:
    """Return releases in `fetched` whose tag is not in state.seen_releases.

    Result is sorted by published_at descending (most recent first).
    """
    seen = {r.get("tag") for r in state.seen_releases if isinstance(r, dict)}
    new = [r for r in fetched if r.tag not in seen]
    new.sort(key=lambda r: r.published_at, reverse=True)
    return new


def build_buckets(releases: list[ReleaseEntry]) -> dict[str, list[str]]:
    """Group bullets across releases into buckets. Misc collects unmatched."""
    buckets: dict[str, list[str]] = {}
    for release in releases:
        for bullet in extract_bullets(release.body):
            bucket = categorize_bullet(bullet)
            line = f"[{release.tag}] {bullet}"
            buckets.setdefault(bucket, []).append(line)
    return buckets


# ---------------------------------------------------------------------------
# Format
# ---------------------------------------------------------------------------

# Stable order for output sections. Misc always last.
BUCKET_ORDER = ["Hooks", "Skills", "MCP", "Slash Commands", "Settings", "Model", "CLI", "Misc"]


def format_text(report: DiffReport) -> str:
    lines: list[str] = []
    if report.fetch_status != "ok":
        lines.append(f"[{report.fetch_status.upper()}] {report.fetch_detail}".strip())
    if not report.new_releases:
        if not lines:
            lines.append("No new releases.")
        return "\n".join(lines) + "\n"

    lines.append(f"{len(report.new_releases)} new release(s):")
    for r in report.new_releases:
        lines.append(f"  {r.tag}  ({r.published_at})")
    lines.append("")

    for bucket in BUCKET_ORDER:
        bullets = report.buckets.get(bucket)
        if not bullets:
            continue
        lines.append(f"== {bucket} ==")
        for b in bullets:
            lines.append(f"  - {b}")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def format_markdown(report: DiffReport) -> str:
    lines: list[str] = []
    if report.fetch_status != "ok":
        lines.append(f"> **{report.fetch_status.replace('_', ' ').title()}** — {report.fetch_detail}".strip())
        lines.append("")
    if not report.new_releases:
        if len(lines) <= 1:
            lines.append("No new releases.")
        return "\n".join(lines) + "\n"

    lines.append(f"## What's new ({len(report.new_releases)} release{'s' if len(report.new_releases) != 1 else ''})")
    lines.append("")
    for r in report.new_releases:
        lines.append(f"- **{r.tag}** ({r.published_at})")
    lines.append("")

    for bucket in BUCKET_ORDER:
        bullets = report.buckets.get(bucket)
        if not bullets:
            continue
        lines.append(f"### {bucket}")
        lines.append("")
        for b in bullets:
            lines.append(f"- {b}")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def format_json(report: DiffReport) -> str:
    payload = {
        "new_releases": [asdict(r) for r in report.new_releases],
        "buckets": {k: report.buckets.get(k, []) for k in BUCKET_ORDER if report.buckets.get(k)},
        "fetch_status": report.fetch_status,
        "fetch_detail": report.fetch_detail,
        "skipped": report.skipped,
    }
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

def build_report(
    state_path: Path,
    no_network: bool = False,
    since: str = "",
    api_url: str = DEFAULT_API_URL,
    opener: Any = None,
) -> tuple[DiffReport, State]:
    """Load state, fetch (unless --no-network), diff, build report.

    Returns (report, new_state). Caller decides whether to persist new_state.
    """
    state = load_state(state_path)

    if no_network:
        return (
            DiffReport(
                fetch_status="offline",
                fetch_detail=f"--no-network; cached state from {state.last_checked_at or 'never'}",
            ),
            state,
        )

    fetch = fetch_releases(url=api_url, etag=state.last_etag, opener=opener)

    if fetch.status == "not_modified":
        return (
            DiffReport(
                fetch_status="not_modified",
                fetch_detail=f"no new releases since {state.last_checked_version or 'unknown'}",
            ),
            state,
        )

    if fetch.status != "ok":
        return (
            DiffReport(fetch_status=fetch.status, fetch_detail=fetch.detail),
            state,
        )

    if since:
        new_releases = [r for r in fetch.releases if r.tag > since]
        new_releases.sort(key=lambda r: r.published_at, reverse=True)
    else:
        new_releases = diff_releases(state, fetch.releases)

    buckets = build_buckets(new_releases)
    report = DiffReport(
        new_releases=new_releases,
        buckets=buckets,
        fetch_status="ok",
    )

    # Build new state (caller persists)
    new_state = State(
        schema_version=SCHEMA_VERSION,
        last_checked_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        last_checked_version=fetch.releases[0].tag if fetch.releases else state.last_checked_version,
        last_etag=fetch.etag or state.last_etag,
        seen_releases=state.seen_releases + [
            {"tag": r.tag, "published_at": r.published_at} for r in new_releases
        ],
    )

    return report, new_state


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="whats-new",
        description="Surface new Claude Code platform features since last local check.",
    )
    p.add_argument("--format", choices=["text", "markdown", "json"], default="text")
    p.add_argument("--since", default="", help="List releases after this tag (ignores state)")
    p.add_argument("--no-network", action="store_true", help="Replay cached state without fetching")
    p.add_argument("--state-file", default="", help="Override state-file path (testing)")
    p.add_argument("--quiet", action="store_true", help="Suppress informational lines on no-op")
    return p


def main(argv: Optional[list[str]] = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    state_path = Path(args.state_file) if args.state_file else DEFAULT_STATE_PATH

    try:
        report, new_state = build_report(
            state_path=state_path,
            no_network=args.no_network,
            since=args.since,
        )
    except ValueError as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        return 1

    if args.format == "json":
        out = format_json(report)
    elif args.format == "markdown":
        out = format_markdown(report)
    else:
        out = format_text(report)

    if args.quiet and not report.new_releases and report.fetch_status == "ok":
        return 0

    sys.stdout.write(out)

    # Persist updated state if we successfully fetched and there are new releases
    if report.fetch_status == "ok" and (report.new_releases or not state_path.exists()):
        try:
            save_state(state_path, new_state)
        except OSError as e:
            print(f"[WARN] could not save state: {e}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
