"""Health-check pass over the auto-memory + audit-log layers.

Concept inspired by Andrej Karpathy's April 2026 LLM Wiki gist
(https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) which proposes
ingest/query/lint operations over a personal knowledge layer. This is an
*independent implementation* tailored to our memory architecture (markdown
auto-memory + sqlite + audit-log + frontmatter-typed files); the checks below
are specific to our layout, not a fork of his code.

v0.1 — five checks (no LLM calls, deterministic):
  1. dead-paths        — file:line refs in memory files where the path doesn't exist
  2. orphan-files      — topic files not linked in MEMORY.md index
  3. broken-index      — MEMORY.md links to files that don't exist
  4. stale-patterns    — configurable substrings (e.g. obsolete repo names)
  5. audit-log-schema  — learning_audit.tsv column-count violations

Out of scope (v0.2+): semantic contradiction detection, persona drift, auto-fix.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

def _project_slug(path: Path | None = None) -> str:
    """Claude Code derives its per-project memory dir by replacing '/' with '-'
    in the absolute path. Reproduce that mapping for the current cwd so the
    linter points at the right `~/.claude/projects/<slug>/memory/` directory
    on any user's machine."""
    p = (path or Path.cwd()).resolve()
    return str(p).replace("/", "-")


DEFAULT_MEMORY_DIR = Path.home() / ".claude" / "projects" / _project_slug() / "memory"
DEFAULT_AUDIT_LOG = DEFAULT_MEMORY_DIR / "learning_audit.tsv"
DEFAULT_STALE_PATTERNS = [
    "~/Projects/old-project/",
    "deprecated-toolkit",
    "Old Toolkit Name",
]
# Project-specific patterns (private identities, prior org names, deprecated handles)
# should be loaded from a user-controlled file at:
#   ~/.claude/leak-patterns.txt   (one pattern per line; not tracked by git)
# This keeps the public default list free of personal/internal references.
EXPECTED_AUDIT_COLS = 9

# Regex for path:line references. Requires an extension (so we don't match
# arbitrary `/words/here.` at sentence boundaries). Excludes URLs and md-link parens.
_PATH_LINE_RE = re.compile(
    r"(?<![\w:/])(~?/[\w./\-_~]+\.\w+)(?::(\d+))?\b"
)
# Markdown link: [text](filename.md) — capture the filename
_MD_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+\.md)\)")


@dataclass
class Finding:
    kind: str
    file: str
    detail: str

    def __str__(self) -> str:  # pragma: no cover — trivial
        return f"[{self.kind}] {self.file}: {self.detail}"


def _expand(p: str) -> Path:
    return Path(os.path.expanduser(p))


def check_dead_paths(memory_dir: Path) -> list[Finding]:
    """Find file:line references where the file doesn't exist."""
    findings: list[Finding] = []
    if not memory_dir.is_dir():
        return findings
    for md in sorted(memory_dir.glob("*.md")):
        try:
            text = md.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for match in _PATH_LINE_RE.finditer(text):
            raw = match.group(1)
            line = match.group(2)
            # Skip very short paths and obvious non-paths
            if len(raw) < 4 or raw in ("/.", "//"):
                continue
            resolved = _expand(raw)
            if not resolved.exists():
                detail = f"missing {raw}" + (f":{line}" if line else "")
                findings.append(Finding("dead-path", md.name, detail))
    return findings


def _index_links(memory_dir: Path) -> set[str]:
    """Filenames mentioned as markdown links in MEMORY.md."""
    idx = memory_dir / "MEMORY.md"
    if not idx.exists():
        return set()
    text = idx.read_text(encoding="utf-8")
    return {m.group(2) for m in _MD_LINK_RE.finditer(text)}


def check_orphan_files(memory_dir: Path) -> list[Finding]:
    """*.md files in memory_dir not linked from MEMORY.md."""
    findings: list[Finding] = []
    if not memory_dir.is_dir():
        return findings
    indexed = _index_links(memory_dir)
    for md in sorted(memory_dir.glob("*.md")):
        if md.name == "MEMORY.md":
            continue
        if md.name not in indexed:
            findings.append(
                Finding("orphan-file", md.name, f"{md.name} not linked from MEMORY.md")
            )
    return findings


def check_broken_index_links(memory_dir: Path) -> list[Finding]:
    """MEMORY.md links pointing at files that don't exist."""
    findings: list[Finding] = []
    idx = memory_dir / "MEMORY.md"
    if not idx.exists():
        return findings
    for ref in _index_links(memory_dir):
        # Resolve relative to memory_dir
        target = memory_dir / ref
        if not target.exists():
            findings.append(
                Finding("broken-index", "MEMORY.md", f"link target missing: {ref}")
            )
    return findings


def check_stale_patterns(memory_dir: Path, patterns: Iterable[str]) -> list[Finding]:
    """Substring scan against an obsolete-strings list."""
    findings: list[Finding] = []
    if not memory_dir.is_dir():
        return findings
    pats = list(patterns)
    for md in sorted(memory_dir.glob("*.md")):
        try:
            text = md.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for pat in pats:
            if pat in text:
                findings.append(
                    Finding("stale-pattern", md.name, f"contains obsolete: {pat!r}")
                )
    return findings


def check_audit_log_schema(audit_log_path: Path, expected_cols: int) -> list[Finding]:
    """TSV row column-count check against the schema header."""
    findings: list[Finding] = []
    if not audit_log_path.exists():
        return findings
    try:
        lines = audit_log_path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError):
        return findings
    for i, line in enumerate(lines, start=1):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        cols = line.split("\t")
        if len(cols) != expected_cols:
            findings.append(
                Finding(
                    "audit-log-schema",
                    audit_log_path.name,
                    f"line {i}: {len(cols)} cols, expected {expected_cols}",
                )
            )
    return findings


def run_lint(
    memory_dir: Path,
    audit_log_path: Path,
    stale_patterns: list[str],
    expected_audit_cols: int = EXPECTED_AUDIT_COLS,
) -> list[Finding]:
    out: list[Finding] = []
    out.extend(check_dead_paths(memory_dir))
    out.extend(check_orphan_files(memory_dir))
    out.extend(check_broken_index_links(memory_dir))
    out.extend(check_stale_patterns(memory_dir, stale_patterns))
    out.extend(check_audit_log_schema(audit_log_path, expected_audit_cols))
    return out


def _format_report(findings: list[Finding], memory_dir: Path) -> str:
    if not findings:
        return f"✅ memory layer clean: {memory_dir}\n"
    lines = [f"🔍 memory lint — {len(findings)} finding(s) in {memory_dir}\n"]
    by_kind: dict[str, list[Finding]] = {}
    for f in findings:
        by_kind.setdefault(f.kind, []).append(f)
    for kind in sorted(by_kind):
        lines.append(f"\n## {kind} ({len(by_kind[kind])})")
        for f in by_kind[kind]:
            lines.append(f"  - {f.file}: {f.detail}")
    lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description="Health-check pass over auto-memory + audit-log."
    )
    p.add_argument("--memory-dir", default=str(DEFAULT_MEMORY_DIR))
    p.add_argument("--audit-log", default=str(DEFAULT_AUDIT_LOG))
    p.add_argument(
        "--patterns",
        default=None,
        help="Optional path to a newline-separated file of stale patterns; "
        "default: built-in list of obsolete strings",
    )
    p.add_argument("--quiet", action="store_true", help="Print nothing if clean")
    p.add_argument(
        "--exit-on-finding",
        action="store_true",
        help="Exit 1 if any findings (default: exit 0 always)",
    )
    args = p.parse_args(argv)

    memory_dir = _expand(args.memory_dir)
    audit_log = _expand(args.audit_log)

    if args.patterns:
        patterns = [
            line.strip()
            for line in Path(args.patterns).read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        ]
    else:
        patterns = list(DEFAULT_STALE_PATTERNS)

    findings = run_lint(memory_dir, audit_log, patterns)

    if findings or not args.quiet:
        print(_format_report(findings, memory_dir))

    if findings and args.exit_on_finding:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
