"""Sync markdown auto-memory → sqlite-vec memory.db.

Closes the gap where today's markdown writes aren't queryable via /recall.
Walks ~/.claude/projects/<slug>/memory/*.md, parses YAML
frontmatter, maps type → category, content-hash dedups against existing
DB rows, inserts/updates.

Designed to run as:
  - SessionStart hook (silent, fast — only writes new content)
  - Manual `/ingest` skill invocation
  - Direct CLI (--dry-run by default; --apply to write)

Exit 0 always (won't block hook firing). Reuses MemoryDB.save from db.py.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

MEMORY_MCP_DIR = Path.home() / ".claude" / "memory-mcp"
sys.path.insert(0, str(MEMORY_MCP_DIR))
from db import MemoryDB  # noqa: E402

DEFAULT_MEMORY_DIR = (
    Path.home() / ".claude" / "projects" / "<slug>" / "memory"
)
DEFAULT_DB_PATH = Path.home() / ".claude" / "memory" / "memory.db"
DEFAULT_REPORT_PATH = Path.home() / ".claude" / "plans" / "ingest-dryrun-report.md"

_TYPE_TO_CATEGORY = {
    "user": "persona",
    "project": "context",
    "feedback": "pattern",
    "reference": "context",
    "learning": "learning",
}

# Match a YAML-style frontmatter block bounded by --- lines at file start
_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n(.*)\Z", re.DOTALL)
# Naive YAML-ish line parser — handles `key: value` lines only (sufficient for our format)
_KV_RE = re.compile(r"^([A-Za-z_][\w\-]*)\s*:\s*(.*)$")


def category_for_type(type_value: str) -> str:
    """Map frontmatter `type` field → memory category. Default 'context'."""
    return _TYPE_TO_CATEGORY.get((type_value or "").strip().lower(), "context")


def parse_frontmatter(text: str) -> tuple[dict, str]:
    """Parse `---\\n key: value...\\n---\\nbody`. Returns (meta dict, body string).

    On no frontmatter or parse failure: returns ({}, original-text).
    """
    m = _FRONTMATTER_RE.match(text)
    if not m:
        return {}, text
    raw_meta, body = m.group(1), m.group(2)
    meta: dict[str, str] = {}
    try:
        for line in raw_meta.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            mm = _KV_RE.match(line)
            if mm:
                key, val = mm.group(1), mm.group(2).strip()
                # Strip wrapping quotes if present
                if val and val[0] == val[-1] and val[0] in ('"', "'"):
                    val = val[1:-1]
                meta[key] = val
    except Exception:  # noqa: BLE001 — never crash the ingest
        return {}, text
    return meta, body


def normalized_hash(content: str) -> str:
    """sha256 of whitespace-normalized content; for dedup."""
    return hashlib.sha256(re.sub(r"\s+", " ", content).strip().encode("utf-8")).hexdigest()


def first_summary(meta: dict, body: str, limit: int = 200) -> str:
    """Prefer frontmatter `name`. Fallback to first H1 or first non-empty line."""
    if meta.get("name"):
        return meta["name"][:limit]
    for raw in body.split("\n"):
        line = raw.strip()
        if not line:
            continue
        if line.startswith("# "):
            return line[2:].strip()[:limit]
        return line[:limit]
    return ""


def build_record(file_path: Path) -> dict:
    """Read a memory file → dict ready for MemoryDB.save."""
    text = file_path.read_text(encoding="utf-8")
    meta, body = parse_frontmatter(text)
    type_field = meta.get("type", "")
    category = category_for_type(type_field)
    mtime = datetime.fromtimestamp(file_path.stat().st_mtime, tz=timezone.utc)
    return {
        "content": text,
        "summary": first_summary(meta, body),
        "category": category,
        "project": None,  # Auto-memory is global
        "tags": ["auto-memory", file_path.name],
        "source": "auto-memory-sync",
        "importance": 7,  # Auto-memory entries are user-curated; treat as high
        "created_at": mtime.isoformat(),
        "updated_at": mtime.isoformat(),
        "content_hash": normalized_hash(text),
        "source_path": str(file_path),
    }


def discover_files(memory_dir: Path) -> list[Path]:
    """Yield *.md files in memory_dir; skip MEMORY.md (it's the index)."""
    if not memory_dir.is_dir():
        return []
    return sorted(p for p in memory_dir.glob("*.md") if p.name != "MEMORY.md")


def classify_action(record: dict, db: MemoryDB) -> tuple[str, str]:
    """Decide insert | update | skip based on existing DB rows.

    Returns (action, reason).
    """
    # 1) Exact content-hash match → skip
    rows = db.conn.execute("SELECT id, content FROM memories").fetchall()
    for row in rows:
        if normalized_hash(row[1]) == record["content_hash"]:
            return ("skip", f"exact-hash-match with id={row[0]}")

    # 2) Same source-filename tag in DB → compare timestamps (newer-wins)
    source_filename = record["tags"][1]
    candidates = db.conn.execute(
        "SELECT id, tags, updated_at FROM memories WHERE tags LIKE ?",
        (f'%"{source_filename}"%',),
    ).fetchall()
    for cand in candidates:
        cand_tags = json.loads(cand[1]) if cand[1] else []
        if source_filename not in cand_tags:
            continue
        existing_updated = cand[2] or ""
        if existing_updated and existing_updated > record["updated_at"]:
            return ("skip", f"existing-newer (id={cand[0]})")
        return ("update", f"db-record-older (id={cand[0]})")

    return ("insert", "no collision")


def render_entry(record: dict, action: str, reason: str) -> str:
    return (
        f"### {record['source_path']}\n"
        f"- action: {action}\n"
        f"- reason: {reason}\n"
        f"- category: {record['category']}\n"
        f"- summary: {record['summary']}\n"
    )


def run(
    memory_dir: Path,
    db_path: Path,
    report_path: Path,
    apply: bool,
) -> dict:
    db = MemoryDB(str(db_path))
    files = discover_files(memory_dir)
    actions: dict[str, list[dict]] = {"insert": [], "update": [], "skip": []}

    for file_path in files:
        try:
            record = build_record(file_path)
        except (OSError, UnicodeDecodeError) as e:
            print(f"[WARN] failed to read {file_path}: {e}", file=sys.stderr)
            continue

        action, reason = classify_action(record, db)
        actions[action].append({"record": record, "reason": reason})

        if apply and action == "insert":
            db.save(
                content=record["content"],
                category=record["category"],
                summary=record["summary"],
                tags=record["tags"],
                project=record["project"],
                importance=record["importance"],
                source=record["source"],
            )
        elif apply and action == "update":
            # Skip in-place update for now; flag for next run
            print(
                f"[NOTE] update flagged (manual handling needed): {file_path}",
                file=sys.stderr,
            )

    # Report
    title = "Apply" if apply else "Dry-Run"
    lines: list[str] = [
        f"# Markdown→sqlite Ingest {title} Report",
        "",
        f"- **Generated:** {datetime.now(timezone.utc).isoformat()}",
        f"- **Memory dir:** `{memory_dir}`",
        f"- **DB:** `{db_path}`",
        f"- **Files scanned:** {len(files)}",
        f"- **Insert{'ed' if apply else 's (planned)'}:** {len(actions['insert'])}",
        f"- **Update{'s flagged' if apply else 's (planned)'}:** {len(actions['update'])}",
        f"- **Skipped:** {len(actions['skip'])}",
        "",
        "## Inserts",
        "",
    ]
    for entry in actions["insert"]:
        lines.append(render_entry(entry["record"], "insert", entry["reason"]))
    if actions["update"]:
        lines.append("\n## Updates (flagged for manual review)\n")
        for entry in actions["update"]:
            lines.append(render_entry(entry["record"], "update", entry["reason"]))
    if actions["skip"]:
        lines.append("\n## Skipped\n")
        for entry in actions["skip"]:
            lines.append(render_entry(entry["record"], "skip", entry["reason"]))

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines), encoding="utf-8")
    db.close()
    return {
        "counts": {k: len(v) for k, v in actions.items()},
        "report_path": str(report_path),
    }


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Sync markdown auto-memory → sqlite memory.db (dry-run by default)."
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Actually write to memory.db (default is dry-run)",
    )
    parser.add_argument("--memory-dir", default=str(DEFAULT_MEMORY_DIR))
    parser.add_argument("--db-path", default=str(DEFAULT_DB_PATH))
    parser.add_argument("--report-path", default=str(DEFAULT_REPORT_PATH))
    parser.add_argument(
        "--quiet", action="store_true", help="Print nothing on success"
    )
    args = parser.parse_args(argv)

    try:
        result = run(
            memory_dir=Path(args.memory_dir),
            db_path=Path(args.db_path),
            report_path=Path(args.report_path),
            apply=args.apply,
        )
    except Exception as e:  # noqa: BLE001 — exit 0 always
        if not args.quiet:
            print(f"[ingest] error: {e}", file=sys.stderr)
        return 0

    if not args.quiet:
        print(f"counts: {result['counts']}")
        print(f"report: {result['report_path']}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except BaseException:  # noqa: BLE001 — never block hook firing
        sys.exit(0)
