"""README auto-stamp block updater.

Edits ONLY the delimited region between `<!-- AUTO-STAMP:START -->` and
`<!-- AUTO-STAMP:END -->` in README.md. Inserts the block after the H1 if the
delimiters are absent. Never touches prose outside the block.
"""

from __future__ import annotations

import argparse
import datetime as dt
import re
import subprocess
import sys
from pathlib import Path

from secret_scan import scan

START = "<!-- AUTO-STAMP:START -->"
END = "<!-- AUTO-STAMP:END -->"
BLOCK_RE = re.compile(re.escape(START) + r".*?" + re.escape(END), re.DOTALL)


def repo_root() -> Path:
    out = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True, check=True
    )
    return Path(out.stdout.strip())


def count_markdown(dir_path: Path) -> int:
    if not dir_path.is_dir():
        return 0
    if (dir_path / "SKILL.md").exists():
        return 1  # caller passed an individual skill dir
    # Count immediate-child .md files OR child dirs containing SKILL.md.
    n = 0
    for entry in dir_path.iterdir():
        if entry.is_file() and entry.suffix == ".md":
            n += 1
        elif entry.is_dir() and (entry / "SKILL.md").exists():
            n += 1
    return n


def recent_commit_subjects(cwd: Path, limit: int = 3) -> list[str]:
    out = subprocess.run(
        [
            "git",
            "log",
            "--no-merges",
            "--pretty=format:%s",
            "-n",
            str(limit * 4),  # over-fetch so we can filter auto-syncs
        ],
        capture_output=True,
        text=True,
        cwd=cwd,
        check=True,
    )
    subjects = [
        s
        for s in out.stdout.splitlines()
        if s and not s.startswith("chore(docs): auto-sync")
    ]
    return subjects[:limit]


def build_block(today: str, skills: int, commands: int, recent: list[str]) -> str:
    safe_recent = [scan(s).safe for s in recent]
    lines = [
        START,
        f"_Last auto-stamped: {today} · Skills: {skills} · Commands: {commands}_",
        "",
        "**Recent commits**",
    ]
    for s in safe_recent:
        lines.append(f"- {s}")
    lines.append(END)
    return "\n".join(lines)


def insert_or_replace(content: str, block: str) -> str:
    if BLOCK_RE.search(content):
        return BLOCK_RE.sub(block, content, count=1)
    # Insert after first H1 (or at top if none).
    m = re.search(r"^# .+\n", content, re.MULTILINE)
    if m:
        idx = m.end()
        return content[:idx] + "\n" + block + "\n" + content[idx:]
    return block + "\n\n" + content


def stamp(cwd: Path | None = None, today: str | None = None) -> tuple[Path, bool]:
    cwd = cwd or repo_root()
    readme = cwd / "README.md"
    if not readme.exists():
        readme.write_text("# Project\n")
    today = today or dt.date.today().isoformat()
    skills = count_markdown(cwd / "skills")
    commands = count_markdown(cwd / "commands")
    recent = recent_commit_subjects(cwd)
    block = build_block(today, skills, commands, recent)
    existing = readme.read_text()
    updated = insert_or_replace(existing, block)
    changed = updated != existing
    if changed:
        readme.write_text(updated)
    return readme, changed


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repo", type=Path, default=None)
    args = p.parse_args()
    path, changed = stamp(args.repo)
    sys.stdout.write(f"{path}: {'updated' if changed else 'no-change'}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
