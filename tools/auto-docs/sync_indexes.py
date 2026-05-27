"""Regenerate docs/SKILLS.md and examples/README.md from source frontmatter.

For each `skills/*/SKILL.md`, extract `name:` and `description:` from frontmatter.
For each `examples/*/` subdir, read its README.md (H1 + first paragraph).
Idempotent: re-running with no source changes produces no diff.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

from secret_scan import scan

FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---", re.DOTALL)
FIELD_RE = re.compile(r"^(?P<k>\w+):\s*(?P<v>.+?)\s*$", re.MULTILINE)


def repo_root() -> Path:
    out = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True, check=True
    )
    return Path(out.stdout.strip())


def parse_frontmatter(text: str) -> dict[str, str]:
    m = FRONTMATTER_RE.search(text)
    if not m:
        return {}
    body = m.group(1)
    return {fm.group("k"): fm.group("v") for fm in FIELD_RE.finditer(body)}


def first_paragraph(text: str) -> str:
    # Skip optional frontmatter, optional H1, return first non-empty prose paragraph.
    body = FRONTMATTER_RE.sub("", text, count=1).strip()
    body = re.sub(r"^# .+\n+", "", body, count=1)
    paras = [p.strip() for p in body.split("\n\n") if p.strip()]
    return paras[0] if paras else ""


def render_skills_index(repo: Path) -> str:
    skills_dir = repo / "skills"
    rows: list[tuple[str, str]] = []
    if skills_dir.is_dir():
        for d in sorted(skills_dir.iterdir()):
            skill_file = d / "SKILL.md"
            if not skill_file.exists():
                continue
            fm = parse_frontmatter(skill_file.read_text())
            name = fm.get("name", d.name)
            desc = fm.get("description", "").strip()
            # Strip surrounding quotes if YAML-style.
            if desc and desc[0] in {'"', "'"} and desc[-1] == desc[0]:
                desc = desc[1:-1]
            rows.append((name, scan(desc).safe))
    lines = [
        "# Skills",
        "",
        "_Auto-generated from `skills/*/SKILL.md` frontmatter. Edit the source, not this file._",
        "",
    ]
    for name, desc in rows:
        lines.append(f"- **`{name}`** — {desc}" if desc else f"- **`{name}`**")
    lines.append("")
    return "\n".join(lines)


def render_examples_index(repo: Path) -> str:
    examples_dir = repo / "examples"
    rows: list[tuple[str, str]] = []
    if examples_dir.is_dir():
        for entry in sorted(examples_dir.iterdir()):
            if entry.name.startswith(".") or entry.name == "README.md":
                continue
            if entry.is_file() and entry.suffix == ".md":
                rows.append((entry.name, scan(first_paragraph(entry.read_text())).safe))
            elif entry.is_dir():
                readme = entry / "README.md"
                desc = ""
                if readme.exists():
                    desc = scan(first_paragraph(readme.read_text())).safe
                rows.append((entry.name + "/", desc))
    lines = [
        "# Examples",
        "",
        "_Auto-generated index. Edit the source files, not this README._",
        "",
    ]
    for name, desc in rows:
        lines.append(f"- **`{name}`** — {desc}" if desc else f"- **`{name}`**")
    lines.append("")
    return "\n".join(lines)


def write_if_changed(path: Path, content: str) -> bool:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.read_text() == content:
        return False
    path.write_text(content)
    return True


def sync(cwd: Path | None = None) -> dict[Path, bool]:
    cwd = cwd or repo_root()
    return {
        cwd / "docs" / "SKILLS.md": write_if_changed(cwd / "docs" / "SKILLS.md", render_skills_index(cwd)),
        cwd / "examples" / "README.md": write_if_changed(
            cwd / "examples" / "README.md", render_examples_index(cwd)
        ),
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repo", type=Path, default=None)
    args = p.parse_args()
    results = sync(args.repo)
    for path, changed in results.items():
        sys.stdout.write(f"{path}: {'updated' if changed else 'no-change'}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
