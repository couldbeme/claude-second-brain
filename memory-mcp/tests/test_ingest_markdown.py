"""Tests for ingest_markdown.py — TDD-first."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

# Add memory-mcp/ for both module under test and MemoryDB
SCRIPTS_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPTS_DIR))

MEMORY_MCP_DIR = Path.home() / ".claude" / "memory-mcp"
sys.path.insert(0, str(MEMORY_MCP_DIR))

from ingest_markdown import (  # noqa: E402
    build_record,
    category_for_type,
    discover_files,
    parse_frontmatter,
    run,
)
from db import MemoryDB  # noqa: E402


class TestTypeToCategory(unittest.TestCase):
    def test_user_to_persona(self):
        self.assertEqual(category_for_type("user"), "persona")

    def test_project_to_context(self):
        self.assertEqual(category_for_type("project"), "context")

    def test_feedback_to_pattern(self):
        self.assertEqual(category_for_type("feedback"), "pattern")

    def test_reference_to_context(self):
        self.assertEqual(category_for_type("reference"), "context")

    def test_learning_to_learning(self):
        self.assertEqual(category_for_type("learning"), "learning")

    def test_unknown_to_context_default(self):
        self.assertEqual(category_for_type(""), "context")
        self.assertEqual(category_for_type("nonsense"), "context")


class TestFrontmatterParse(unittest.TestCase):
    def test_full_frontmatter(self):
        text = "---\nname: X\ndescription: Y\ntype: user\n---\nbody"
        meta, body = parse_frontmatter(text)
        self.assertEqual(meta.get("type"), "user")
        self.assertEqual(meta.get("name"), "X")
        self.assertEqual(body.strip(), "body")

    def test_no_frontmatter(self):
        text = "no frontmatter, just body"
        meta, body = parse_frontmatter(text)
        self.assertEqual(meta, {})
        self.assertEqual(body, text)

    def test_malformed_frontmatter_treated_as_body(self):
        text = "---\nbroken yaml: : :\nbody"
        meta, body = parse_frontmatter(text)
        # Either the malformed frontmatter is empty meta or it's still readable;
        # the script must not crash. Body must be preserved.
        self.assertIn("body", body)


class TestDiscoverFiles(unittest.TestCase):
    def test_skips_memory_md(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_p = Path(tmp)
            (tmp_p / "MEMORY.md").write_text("- [x](y.md) — index\n")
            (tmp_p / "topic.md").write_text("---\nname: T\ntype: learning\n---\nbody")
            files = discover_files(tmp_p)
            names = [p.name for p in files]
            self.assertIn("topic.md", names)
            self.assertNotIn("MEMORY.md", names)


class TestBuildRecord(unittest.TestCase):
    def test_record_assembled_correctly(self):
        with tempfile.TemporaryDirectory() as tmp:
            md = Path(tmp) / "feedback_test.md"
            md.write_text(
                "---\n"
                "name: Test Feedback\n"
                "description: A test\n"
                "type: feedback\n"
                "---\n"
                "Body content here."
            )
            rec = build_record(md)
            self.assertEqual(rec["category"], "pattern")  # feedback → pattern
            self.assertEqual(rec["summary"], "Test Feedback")  # from name field
            self.assertIn("auto-memory", rec["tags"])
            self.assertIn("feedback_test.md", rec["tags"])
            self.assertEqual(rec["source"], "auto-memory-sync")


class TestRunIdempotent(unittest.TestCase):
    def test_apply_twice_no_duplicate_rows(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_p = Path(tmp)
            db_path = tmp_p / "test.db"
            mem_dir = tmp_p / "mem"
            mem_dir.mkdir()
            (mem_dir / "MEMORY.md").write_text("")
            (mem_dir / "feedback_a.md").write_text(
                "---\nname: Feedback A\ntype: feedback\n---\nbody A"
            )
            report_path = tmp_p / "report.md"

            # First apply
            r1 = run(
                memory_dir=mem_dir, db_path=db_path, report_path=report_path, apply=True
            )
            self.assertEqual(r1["counts"]["insert"], 1)

            # Second apply — idempotent (hash-dedup)
            r2 = run(
                memory_dir=mem_dir, db_path=db_path, report_path=report_path, apply=True
            )
            self.assertEqual(r2["counts"]["insert"], 0)
            self.assertGreaterEqual(r2["counts"]["skip"], 1)

            # Verify no duplicate rows in DB
            db = MemoryDB(str(db_path))
            rows = db.conn.execute(
                "SELECT COUNT(*) FROM memories WHERE tags LIKE ?",
                ('%"feedback_a.md"%',),
            ).fetchone()[0]
            db.close()
            self.assertEqual(rows, 1)


class TestRunDryRun(unittest.TestCase):
    def test_dry_run_writes_no_db_rows(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_p = Path(tmp)
            db_path = tmp_p / "test.db"
            mem_dir = tmp_p / "mem"
            mem_dir.mkdir()
            (mem_dir / "MEMORY.md").write_text("")
            (mem_dir / "topic.md").write_text(
                "---\nname: Topic\ntype: learning\n---\nbody"
            )
            report_path = tmp_p / "report.md"

            r = run(
                memory_dir=mem_dir,
                db_path=db_path,
                report_path=report_path,
                apply=False,
            )
            self.assertEqual(r["counts"]["insert"], 1)  # would insert

            # No actual rows
            db = MemoryDB(str(db_path))
            rows = db.conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
            db.close()
            self.assertEqual(rows, 0)


if __name__ == "__main__":
    unittest.main()
