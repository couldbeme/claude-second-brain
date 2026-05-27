"""Orchestrator: run all auto-docs generators with a no-loop guard.

Returns nonzero only on real failure. Used by `.githooks/pre-push` and by
`.github/workflows/auto-docs.yml`.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

import changelog
import readme_stamp
import sync_indexes

AUTO_PATHS = {
    "CHANGELOG.md",
    "README.md",
    "docs/SKILLS.md",
    "examples/README.md",
}


def repo_root() -> Path:
    out = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True, check=True
    )
    return Path(out.stdout.strip())


def head_subject(cwd: Path) -> str:
    out = subprocess.run(
        ["git", "log", "-1", "--pretty=format:%s"], capture_output=True, text=True, cwd=cwd, check=True
    )
    return out.stdout.strip()


def head_changed_paths(cwd: Path) -> set[str]:
    """Files modified by HEAD commit (relative to repo root)."""
    out = subprocess.run(
        ["git", "diff-tree", "--no-commit-id", "--name-only", "-r", "HEAD"],
        capture_output=True,
        text=True,
        cwd=cwd,
        check=True,
    )
    return {line.strip() for line in out.stdout.splitlines() if line.strip()}


def should_skip(cwd: Path) -> tuple[bool, str]:
    """No-loop guard. Skip when HEAD is itself an auto-docs commit."""
    subject = head_subject(cwd)
    if subject.startswith("chore(docs): auto-sync") or "[skip auto-docs]" in subject:
        return True, f"skip: HEAD subject is auto-sync ({subject!r})"
    changed = head_changed_paths(cwd)
    if changed and changed.issubset(AUTO_PATHS):
        return True, f"skip: HEAD changes only auto-paths ({sorted(changed)})"
    return False, ""


def run(cwd: Path | None = None) -> dict[str, bool]:
    cwd = cwd or repo_root()
    results: dict[str, bool] = {}
    _, results["CHANGELOG.md"] = changelog.generate(cwd)
    _, results["README.md"] = readme_stamp.stamp(cwd)
    sync_results = sync_indexes.sync(cwd)
    for path, changed in sync_results.items():
        results[str(path.relative_to(cwd))] = changed
    return results


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repo", type=Path, default=None)
    p.add_argument("--force", action="store_true", help="Skip the no-loop guard")
    args = p.parse_args()
    cwd = args.repo or repo_root()
    if not args.force:
        skip, reason = should_skip(cwd)
        if skip:
            sys.stdout.write(f"auto-docs: {reason}\n")
            return 0
    results = run(cwd)
    any_changed = any(results.values())
    for path, changed in results.items():
        sys.stdout.write(f"  {path}: {'updated' if changed else 'no-change'}\n")
    sys.stdout.write(f"auto-docs: {'changes pending' if any_changed else 'no diff'}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
