"""Tests for lint_memory.py — TDD-first.

Six checks defined in the v0.1 scope (see ~/.claude/plans/oss-launch-phase-1-implement.md):
- dead-paths, orphan-files, broken-index, stale-patterns, audit-log-schema
- plus: clean dir passes
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

# Add parent dir (memory-mcp/) to sys.path so we can import lint_memory
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lint_memory import (  # noqa: E402
    Finding,
    check_audit_log_schema,
    check_broken_index_links,
    check_dead_paths,
    check_orphan_files,
    check_stale_patterns,
    run_lint,
)


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


class TestDeadPaths(unittest.TestCase):
    def test_flags_nonexistent_file_reference(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_p = Path(tmp)
            _write(tmp_p / "MEMORY.md", "")
            _write(
                tmp_p / "topic.md",
                "Some content with a dead ref: /nonexistent/path/file.py:42 here.",
            )
            findings = check_dead_paths(tmp_p)
            self.assertTrue(any(f.kind == "dead-path" for f in findings))
            self.assertTrue(
                any("nonexistent" in f.detail for f in findings),
                f"got: {[f.detail for f in findings]}",
            )

    def test_real_path_not_flagged(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_p = Path(tmp)
            real = tmp_p / "real_file.py"
            real.write_text("# real")
            _write(tmp_p / "MEMORY.md", "")
            _write(
                tmp_p / "topic.md",
                f"Reference to a real file: {real}:1",
            )
            findings = check_dead_paths(tmp_p)
            dead = [f for f in findings if f.kind == "dead-path"]
            self.assertEqual(dead, [])


class TestOrphanFiles(unittest.TestCase):
    def test_flags_unindexed_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_p = Path(tmp)
            _write(tmp_p / "MEMORY.md", "- [Indexed](indexed.md) — yep\n")
            _write(tmp_p / "indexed.md", "indexed content")
            _write(tmp_p / "orphan.md", "not indexed anywhere")
            findings = check_orphan_files(tmp_p)
            self.assertTrue(any(f.kind == "orphan-file" and "orphan.md" in f.detail for f in findings))

    def test_indexed_file_not_flagged(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_p = Path(tmp)
            _write(tmp_p / "MEMORY.md", "- [Indexed](indexed.md) — yep\n")
            _write(tmp_p / "indexed.md", "indexed content")
            findings = check_orphan_files(tmp_p)
            orphans = [f for f in findings if f.kind == "orphan-file"]
            self.assertEqual(orphans, [])


class TestBrokenIndex(unittest.TestCase):
    def test_flags_link_to_missing_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_p = Path(tmp)
            _write(tmp_p / "MEMORY.md", "- [Missing](missing.md) — gone\n")
            findings = check_broken_index_links(tmp_p)
            self.assertTrue(
                any(f.kind == "broken-index" and "missing.md" in f.detail for f in findings)
            )

    def test_existing_file_link_not_flagged(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_p = Path(tmp)
            _write(tmp_p / "MEMORY.md", "- [Existing](existing.md) — here\n")
            _write(tmp_p / "existing.md", "ok")
            findings = check_broken_index_links(tmp_p)
            broken = [f for f in findings if f.kind == "broken-index"]
            self.assertEqual(broken, [])


class TestStalePatterns(unittest.TestCase):
    def test_flags_known_obsolete_string(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_p = Path(tmp)
            _write(tmp_p / "MEMORY.md", "")
            _write(tmp_p / "topic.md", "Some old reference to ~/Dev/work/foo here.")
            patterns = ["~/Dev/work/", "claude-code-team-toolkit"]
            findings = check_stale_patterns(tmp_p, patterns)
            self.assertTrue(any(f.kind == "stale-pattern" for f in findings))
            self.assertTrue(any("~/Dev/work/" in f.detail for f in findings))

    def test_clean_content_not_flagged(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_p = Path(tmp)
            _write(tmp_p / "MEMORY.md", "")
            _write(tmp_p / "topic.md", "Modern reference: ~/Dev/claude-second-brain/")
            patterns = ["~/Dev/work/", "claude-code-team-toolkit"]
            findings = check_stale_patterns(tmp_p, patterns)
            stale = [f for f in findings if f.kind == "stale-pattern"]
            self.assertEqual(stale, [])


class TestAuditLogSchema(unittest.TestCase):
    EXPECTED_COLS = 9

    def test_flags_short_row(self):
        with tempfile.TemporaryDirectory() as tmp:
            tsv = Path(tmp) / "learning_audit.tsv"
            tsv.write_text(
                "# schema_version=1  cols=9\n"
                "session_date\tsession_id\ttags_in_chat\ttags_saved\tl2_fired\tl2_saved\tl2_fp\tcontradictions_flagged\tflush_source\n"
                "2026-04-27\tabc\t1\t1\t0\t0\t0\t0\n"  # only 8 fields
            )
            findings = check_audit_log_schema(tsv, self.EXPECTED_COLS)
            self.assertTrue(any(f.kind == "audit-log-schema" for f in findings))

    def test_correct_row_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            tsv = Path(tmp) / "learning_audit.tsv"
            tsv.write_text(
                "# schema_version=1  cols=9\n"
                "session_date\tsession_id\ttags_in_chat\ttags_saved\tl2_fired\tl2_saved\tl2_fp\tcontradictions_flagged\tflush_source\n"
                "2026-04-27\tabc\t1\t1\t0\t0\t0\t0\tinline\n"
            )
            findings = check_audit_log_schema(tsv, self.EXPECTED_COLS)
            self.assertEqual([f for f in findings if f.kind == "audit-log-schema"], [])

    def test_missing_audit_log_silently_ok(self):
        # No audit log = nothing to check; no findings
        findings = check_audit_log_schema(Path("/nonexistent/audit.tsv"), self.EXPECTED_COLS)
        self.assertEqual(findings, [])


class TestCleanDirPasses(unittest.TestCase):
    def test_well_formed_dir_no_findings(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_p = Path(tmp)
            real = tmp_p / "real.py"
            real.write_text("# real")
            _write(
                tmp_p / "MEMORY.md",
                "- [Topic](topic.md) — clean ref\n",
            )
            _write(
                tmp_p / "topic.md",
                f"Clean reference: {real}:1, no obsolete patterns here.",
            )
            findings = run_lint(
                memory_dir=tmp_p,
                audit_log_path=tmp_p / "no_audit.tsv",
                stale_patterns=["~/Dev/work/", "claude-code-team-toolkit"],
            )
            self.assertEqual(findings, [], f"unexpected findings: {findings}")


class TestFindingDataclass(unittest.TestCase):
    def test_finding_str_format(self):
        f = Finding(kind="dead-path", file="topic.md", detail="missing /tmp/x.py:1")
        s = str(f)
        self.assertIn("dead-path", s)
        self.assertIn("topic.md", s)


if __name__ == "__main__":
    unittest.main()
