"""Conventional-Commits → CHANGELOG.md generator.

Walks git log since the last release tag (or first commit if untagged), groups
commits by CC type, and replaces the `## [Unreleased]` block in CHANGELOG.md.
Idempotent: re-running with the same commit range produces no diff.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

from secret_scan import scan

CC_RE = re.compile(
    r"^(?P<type>feat|fix|docs|chore|refactor|test|ci|perf|build|style)"
    r"(?:\((?P<scope>[^)]+)\))?(?P<bang>!)?: (?P<subject>.+)$"
)

GROUP_TITLES = {
    "feat": "Added",
    "fix": "Fixed",
    "docs": "Documentation",
    "refactor": "Changed",
    "perf": "Performance",
    "test": "Tests",
    "build": "Build",
    "ci": "CI",
    "chore": "Chore",
    "style": "Style",
    "other": "Other",
}

# Order of groups in the rendered Unreleased block.
GROUP_ORDER = ["feat", "fix", "perf", "refactor", "docs", "test", "build", "ci", "chore", "style", "other"]

HEADER = (
    "# Changelog\n\n"
    "All notable changes to this project are documented here.\n"
    "Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/); "
    "versioning follows [SemVer](https://semver.org/).\n"
)

UNRELEASED_HEADING = "## [Unreleased]"


def repo_root() -> Path:
    out = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True, check=True
    )
    return Path(out.stdout.strip())


def last_tag(cwd: Path) -> str | None:
    out = subprocess.run(
        ["git", "describe", "--tags", "--abbrev=0"], capture_output=True, text=True, cwd=cwd
    )
    return out.stdout.strip() if out.returncode == 0 and out.stdout.strip() else None


def commit_subjects(cwd: Path, since: str | None) -> list[str]:
    args = ["git", "log", "--no-merges", "--pretty=format:%s"]
    if since:
        args.append(f"{since}..HEAD")
    out = subprocess.run(args, capture_output=True, text=True, cwd=cwd, check=True)
    return [line for line in out.stdout.splitlines() if line.strip()]


def classify(subjects: list[str]) -> dict[str, list[str]]:
    """Group commit subjects by CC type. Non-CC subjects go to 'other'."""
    groups: dict[str, list[str]] = {k: [] for k in GROUP_ORDER}
    for s in subjects:
        # Skip the auto-docs commits themselves to avoid loop noise.
        if s.startswith("chore(docs): auto-sync"):
            continue
        m = CC_RE.match(s)
        kind = m.group("type") if m else "other"
        rendered = m.group("subject") if m else s
        scope = m.group("scope") if m and m.group("scope") else None
        prefix = f"**{scope}**: " if scope else ""
        safe = scan(prefix + rendered).safe
        groups[kind].append(safe)
    return groups


def render_unreleased(groups: dict[str, list[str]]) -> str:
    lines = [UNRELEASED_HEADING, ""]
    any_content = False
    for kind in GROUP_ORDER:
        items = groups.get(kind, [])
        if not items:
            continue
        any_content = True
        lines.append(f"### {GROUP_TITLES[kind]}")
        for item in items:
            lines.append(f"- {item}")
        lines.append("")
    if not any_content:
        lines.append("_No changes since last release._")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def replace_unreleased(existing: str, new_block: str) -> str:
    """Replace the existing `## [Unreleased]` section with new_block.

    The section spans from the `## [Unreleased]` heading until the next `## ` heading
    or end-of-file. If the section is absent, the new block is inserted after the
    file header (before the first `## ` heading) or appended to the header.
    """
    pattern = re.compile(
        r"^## \[Unreleased\].*?(?=^## |\Z)", re.MULTILINE | re.DOTALL
    )
    if pattern.search(existing):
        return pattern.sub(new_block + "\n", existing, count=1)
    # No unreleased section yet — insert before first release heading, or append.
    release_match = re.search(r"^## \[", existing, re.MULTILINE)
    if release_match:
        idx = release_match.start()
        return existing[:idx] + new_block + "\n" + existing[idx:]
    return existing.rstrip() + "\n\n" + new_block


def generate(cwd: Path | None = None) -> tuple[Path, bool]:
    """Generate/update CHANGELOG.md. Returns (path, changed)."""
    cwd = cwd or repo_root()
    changelog = cwd / "CHANGELOG.md"
    tag = last_tag(cwd)
    subjects = commit_subjects(cwd, tag)
    groups = classify(subjects)
    new_block = render_unreleased(groups)

    existing = changelog.read_text() if changelog.exists() else HEADER + "\n" + UNRELEASED_HEADING + "\n"
    updated = replace_unreleased(existing, new_block)
    if not updated.startswith("# Changelog"):
        updated = HEADER + "\n" + updated
    changed = updated != existing
    if changed:
        changelog.write_text(updated)
    return changelog, changed


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repo", type=Path, default=None, help="Repo root (default: git toplevel)")
    args = p.parse_args()
    path, changed = generate(args.repo)
    sys.stdout.write(f"{path}: {'updated' if changed else 'no-change'}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
