"""Tests for continuity_dump.py — TDD-first (RED before GREEN).

All tests use real filesystem via tempfile.TemporaryDirectory — no mocks as
deliverables per CLAUDE.md rule 7. Unittest idiom matches test_ingest_markdown.py.
"""

from __future__ import annotations

import fcntl
import os
import sys
import tempfile
import threading
import time
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

# Resolve memory-mcp directory so imports work both from repo root and from the
# tests/ subdirectory, matching the pattern in test_ingest_markdown.py.
SCRIPTS_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPTS_DIR))

from continuity_dump import append_bridge_entry, write_continuity_snapshot  # noqa: E402


# ---------------------------------------------------------------------------
# Helper: synthetic session_bridge.md content
# ---------------------------------------------------------------------------

_SYNTHETIC_BRIDGE = """\
[2026-04-28T14:00:00Z] [DECISION] use cursor pagination | WHY: offset breaks on inserts | REJECTED: offset
[2026-04-28T14:10:00Z] [THREAD-OPEN] a3f9c100 | voice-signal extraction approach
[2026-04-28T14:20:00Z] [INFLIGHT] task=implement continuity_dump | step=write tests | next=write impl
[2026-04-28T14:30:00Z] [VOICE] energy=high | signal=build-on | ref=tdd-cycle
[2026-04-28T14:40:00Z] [PERSONA] count=3 | category=decision-style | obs=prefers options upfront
[2026-04-28T14:50:00Z] [THREAD-CLOSE] a3f9c100
"""


def _write_bridge(memory_dir: Path, content: str = _SYNTHETIC_BRIDGE) -> Path:
    bridge = memory_dir / "session_bridge.md"
    bridge.write_text(content, encoding="utf-8")
    return bridge


# ---------------------------------------------------------------------------
# 1. File path
# ---------------------------------------------------------------------------

class TestWritesFileAtExpectedPath(unittest.TestCase):
    def test_writes_file_at_expected_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            mem = Path(tmp)
            _write_bridge(mem)
            session_id = "test_abc123"
            result = write_continuity_snapshot(session_id, "/fake/cwd", mem)
            self.assertTrue(result)
            expected = mem / f"continuity_pre_compact_{session_id}.md"
            self.assertTrue(expected.exists(), f"Expected {expected} to exist")


# ---------------------------------------------------------------------------
# 2. Frontmatter required fields
# ---------------------------------------------------------------------------

class TestFrontmatterRequiredFields(unittest.TestCase):
    def test_frontmatter_required_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            mem = Path(tmp)
            _write_bridge(mem)
            write_continuity_snapshot("sess42", "/project/cwd", mem)
            content = (mem / "continuity_pre_compact_sess42.md").read_text()

            required = [
                "session_id",
                "timestamp_utc",
                "cwd",
                "tokens_used",
                "tokens_max",
                "percent_used",
                "model",
                "bridge_entry_count",
            ]
            for field in required:
                self.assertIn(
                    field, content,
                    f"Frontmatter missing required field: {field}",
                )


# ---------------------------------------------------------------------------
# 3. Body must not contain verbatim user/assistant text
# ---------------------------------------------------------------------------

class TestBodyMetadataOnly(unittest.TestCase):
    def test_body_metadata_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            mem = Path(tmp)
            # Bridge entries are structural metadata only — put fake user/assistant
            # text in the bridge as the payload to be sure we don't echo it verbatim.
            bridge_content = """\
[2026-04-28T10:00:00Z] [DECISION] do not echo | WHY: privacy | REJECTED: nope
"""
            _write_bridge(mem, bridge_content)
            write_continuity_snapshot("privacy_test", "/cwd", mem)
            output = (mem / "continuity_pre_compact_privacy_test.md").read_text()

            # These strings simulate verbatim message-body content that must NEVER appear.
            forbidden = [
                "USER: hello world",
                "ASSISTANT: response text",
                "Human: private message",
                "Assistant: private reply",
            ]
            for substring in forbidden:
                self.assertNotIn(
                    substring, output,
                    f"Output must not contain verbatim message body: {substring!r}",
                )


# ---------------------------------------------------------------------------
# 4. Privacy: no .jsonl reads
# ---------------------------------------------------------------------------

class TestNoTranscriptReads(unittest.TestCase):
    def test_no_transcript_reads(self):
        """Patching Path.read_text to raise on .jsonl paths proves no JSONL access."""
        with tempfile.TemporaryDirectory() as tmp:
            mem = Path(tmp)
            _write_bridge(mem)

            original_read_text = Path.read_text

            def _guarded_read_text(self_path, *args, **kwargs):
                if str(self_path).endswith(".jsonl"):
                    raise AssertionError(
                        f"Privacy violation: attempted to read .jsonl file: {self_path}"
                    )
                return original_read_text(self_path, *args, **kwargs)

            with patch.object(Path, "read_text", _guarded_read_text):
                result = write_continuity_snapshot("no_jsonl", "/cwd", mem)

            # Must succeed (True) despite the guard — no .jsonl was touched.
            self.assertTrue(result)


# ---------------------------------------------------------------------------
# 5. Atomic write — .tmp appears mid-write, gone after success
# ---------------------------------------------------------------------------

class TestAtomicWrite(unittest.TestCase):
    def test_atomic_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            mem = Path(tmp)
            _write_bridge(mem)
            session_id = "atomic_test"

            tmp_path_seen: list[bool] = []
            final_path_seen_before_replace: list[bool] = []

            original_replace = os.replace

            def _spy_replace(src, dst):
                # Before the replace: .tmp should exist, final should not yet
                tmp_path_seen.append(Path(src).exists())
                final_path_seen_before_replace.append(
                    (mem / f"continuity_pre_compact_{session_id}.md").exists()
                )
                original_replace(src, dst)

            with patch("os.replace", side_effect=_spy_replace):
                write_continuity_snapshot(session_id, "/cwd", mem)

            # os.replace was called
            self.assertTrue(tmp_path_seen, "os.replace was never called")
            # .tmp existed when os.replace was called
            self.assertTrue(tmp_path_seen[0], ".tmp sibling did not exist before os.replace")
            # After success, .tmp is gone
            tmp_leftover = mem / f"continuity_pre_compact_{session_id}.md.tmp"
            self.assertFalse(tmp_leftover.exists(), ".tmp orphan left after successful write")


# ---------------------------------------------------------------------------
# 6. Missing session_bridge.md → returns False, no output, no raise
# ---------------------------------------------------------------------------

class TestReturnsFalseOnMissingBridge(unittest.TestCase):
    def test_returns_false_on_missing_bridge(self):
        with tempfile.TemporaryDirectory() as tmp:
            mem = Path(tmp)
            # No session_bridge.md written
            result = write_continuity_snapshot("no_bridge", "/cwd", mem)
            self.assertFalse(result)
            output = mem / "continuity_pre_compact_no_bridge.md"
            self.assertFalse(output.exists(), "Output file must not be created when bridge is missing")


# ---------------------------------------------------------------------------
# 7. Disk error → returns False, never raises
# ---------------------------------------------------------------------------

class TestReturnsFalseOnDiskError(unittest.TestCase):
    def test_returns_false_on_disk_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            mem = Path(tmp)
            _write_bridge(mem)

            original_write_text = Path.write_text

            def _failing_write_text(self_path, *args, **kwargs):
                # Only fail the .tmp write, not bridge reads
                if str(self_path).endswith(".tmp"):
                    raise OSError("Simulated disk full error")
                return original_write_text(self_path, *args, **kwargs)

            with patch.object(Path, "write_text", _failing_write_text):
                result = write_continuity_snapshot("disk_error", "/cwd", mem)

            self.assertFalse(result)


# ---------------------------------------------------------------------------
# 8. Idempotent: two invocations → same path overwritten, no orphans
# ---------------------------------------------------------------------------

class TestIdempotentWithinSession(unittest.TestCase):
    def test_idempotent_within_session(self):
        with tempfile.TemporaryDirectory() as tmp:
            mem = Path(tmp)
            _write_bridge(mem)
            session_id = "idem_test"

            r1 = write_continuity_snapshot(session_id, "/cwd", mem)
            r2 = write_continuity_snapshot(session_id, "/cwd", mem)

            self.assertTrue(r1)
            self.assertTrue(r2)

            # Exactly one output file — no orphans
            outputs = list(mem.glob(f"continuity_pre_compact_{session_id}*"))
            self.assertEqual(len(outputs), 1, f"Expected 1 output file, got: {outputs}")


# ---------------------------------------------------------------------------
# 9. append_bridge_entry — correct format
# ---------------------------------------------------------------------------

class TestAppendBridgeEntryFormat(unittest.TestCase):
    def test_append_bridge_entry_appends_correct_format(self):
        with tempfile.TemporaryDirectory() as tmp:
            mem = Path(tmp)
            bridge = mem / "session_bridge.md"
            self.assertFalse(bridge.exists())  # file absent — should be created

            result = append_bridge_entry(mem, "DECISION", "use TDD | WHY: quality | REJECTED: skip")
            self.assertTrue(result)
            self.assertTrue(bridge.exists(), "session_bridge.md should be created")

            content = bridge.read_text(encoding="utf-8")
            self.assertIn("DECISION", content)
            self.assertIn("use TDD | WHY: quality | REJECTED: skip", content)

            # Should end with newline
            self.assertTrue(content.endswith("\n"), "Entry must end with newline")

            # Timestamp format check: line starts with [YYYY-MM-DDTHH:MM:SSZ]
            line = content.strip().splitlines()[-1]
            self.assertTrue(
                line.startswith("[20"),
                f"Line should start with ISO timestamp: {line!r}",
            )
            self.assertIn("] [DECISION] ", line)


# ---------------------------------------------------------------------------
# 10. append_bridge_entry — atomic (concurrent appends don't interleave)
# ---------------------------------------------------------------------------

class TestAppendBridgeEntryAtomic(unittest.TestCase):
    def test_append_bridge_entry_atomic(self):
        with tempfile.TemporaryDirectory() as tmp:
            mem = Path(tmp)
            n_threads = 20
            results: list[bool] = []
            lock = threading.Lock()

            def _do_append(i: int):
                r = append_bridge_entry(mem, "INFLIGHT", f"task=thread-{i} | step=test | next=done")
                with lock:
                    results.append(r)

            threads = [threading.Thread(target=_do_append, args=(i,)) for i in range(n_threads)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()

            self.assertEqual(len(results), n_threads)
            self.assertTrue(all(results), "All concurrent appends must succeed")

            content = (mem / "session_bridge.md").read_text(encoding="utf-8")
            lines = [ln for ln in content.splitlines() if ln.strip()]
            self.assertEqual(
                len(lines), n_threads,
                f"Expected {n_threads} lines, got {len(lines)} — possible interleave",
            )
            # Each line is self-contained (no merged lines)
            for line in lines:
                self.assertIn("[INFLIGHT]", line)


# ---------------------------------------------------------------------------
# 11. append_bridge_entry — validates entry_type
# ---------------------------------------------------------------------------

class TestAppendBridgeEntryValidatesType(unittest.TestCase):
    def test_append_bridge_entry_validates_entry_type(self):
        with tempfile.TemporaryDirectory() as tmp:
            mem = Path(tmp)
            bridge = mem / "session_bridge.md"

            result = append_bridge_entry(mem, "INVALID_TYPE", "some payload")
            self.assertFalse(result, "Unknown entry_type must return False")
            self.assertFalse(bridge.exists(), "Bridge must not be created on invalid type")

    def test_valid_types_accepted(self):
        with tempfile.TemporaryDirectory() as tmp:
            mem = Path(tmp)
            valid_types = ["DECISION", "THREAD-OPEN", "THREAD-CLOSE", "INFLIGHT", "VOICE", "PERSONA"]
            for entry_type in valid_types:
                r = append_bridge_entry(mem, entry_type, f"payload for {entry_type}")
                self.assertTrue(r, f"Valid type {entry_type!r} must return True")


# ---------------------------------------------------------------------------
# 12. session_threads table migration
# ---------------------------------------------------------------------------

class TestSessionThreadsTableCreated(unittest.TestCase):
    def test_session_threads_table_created(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = str(Path(tmp) / "test_threads.db")
            from db import MemoryDB
            db = MemoryDB(db_path)

            # Verify session_threads table exists
            tables = [
                row[0]
                for row in db.conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            ]
            self.assertIn("session_threads", tables, "session_threads table must exist after migration")

            # Verify expected columns via PRAGMA
            cols = {
                row[1]: row  # col_name → full row
                for row in db.conn.execute("PRAGMA table_info(session_threads)").fetchall()
            }
            # Per CONTINUITY-SCHEMA.md: closed_at + project are deliberately omitted
            # (closed_at derivable from flat-file THREAD-CLOSE; project redundant with
            # per-project memory dir scope).
            expected_cols = ["id", "session_id", "description", "status", "opened_at"]
            for col in expected_cols:
                self.assertIn(col, cols, f"Column '{col}' missing from session_threads")
            for col in ("closed_at", "project"):
                self.assertNotIn(col, cols, f"Column '{col}' must be excluded per CONTINUITY-SCHEMA.md")

            # Verify indexes exist
            indexes = [
                row[1]
                for row in db.conn.execute(
                    "SELECT * FROM sqlite_master WHERE type='index' AND tbl_name='session_threads'"
                ).fetchall()
            ]
            self.assertIn("idx_threads_session", indexes)
            self.assertIn("idx_threads_status", indexes)

            db.close()

    def test_session_threads_insert_and_query(self):
        """Smoke test: can insert a row and query it back."""
        with tempfile.TemporaryDirectory() as tmp:
            db_path = str(Path(tmp) / "test_threads_insert.db")
            from db import MemoryDB
            db = MemoryDB(db_path)

            db.conn.execute(
                "INSERT INTO session_threads (id, session_id, description, status) VALUES (?, ?, ?, ?)",
                ("a3f9c100", "sess_abc", "open question: approach A vs B", "open"),
            )
            db.conn.commit()

            row = db.conn.execute(
                "SELECT id, session_id, status FROM session_threads WHERE id=?",
                ("a3f9c100",),
            ).fetchone()
            self.assertIsNotNone(row)
            self.assertEqual(row[0], "a3f9c100")
            self.assertEqual(row[1], "sess_abc")
            self.assertEqual(row[2], "open")

            db.close()


# ---------------------------------------------------------------------------
# 13. append_bridge_entry — payload length cap + newline strip
# ---------------------------------------------------------------------------

class TestAppendBridgeEntryPayloadCap(unittest.TestCase):
    def test_payload_truncated_at_500_chars(self):
        with tempfile.TemporaryDirectory() as tmp:
            mem = Path(tmp)
            long_payload = "x" * 2000
            result = append_bridge_entry(mem, "DECISION", long_payload)
            self.assertTrue(result)
            line = (mem / "session_bridge.md").read_text(encoding="utf-8").strip().splitlines()[-1]
            # Strip the timestamp+type prefix; what's left is the payload.
            payload_in_file = line.split("] ", 2)[-1]
            self.assertLessEqual(
                len(payload_in_file), 500,
                f"Payload should be capped at 500 chars, got {len(payload_in_file)}",
            )

    def test_payload_strips_newlines(self):
        with tempfile.TemporaryDirectory() as tmp:
            mem = Path(tmp)
            payload_with_breaks = "first line\nsecond line\rthird line"
            result = append_bridge_entry(mem, "INFLIGHT", payload_with_breaks)
            self.assertTrue(result)
            content = (mem / "session_bridge.md").read_text(encoding="utf-8")
            # Exactly one entry line (plus trailing newline) — no embedded breaks.
            non_empty_lines = [ln for ln in content.splitlines() if ln.strip()]
            self.assertEqual(len(non_empty_lines), 1, "Newlines in payload must be stripped")
            self.assertNotIn("\nsecond line", content)


# ---------------------------------------------------------------------------
# 14. write_continuity_snapshot — orphan .tmp from prior crashed write is cleaned
# ---------------------------------------------------------------------------

class TestOrphanTmpCleanup(unittest.TestCase):
    def test_orphan_tmp_cleaned_before_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            mem = Path(tmp)
            _write_bridge(mem)
            session_id = "orphan_test"

            # Simulate prior crashed write: an orphan .tmp file exists.
            orphan = mem / f"continuity_pre_compact_{session_id}.md.tmp"
            orphan.write_text("STALE ORPHAN CONTENT", encoding="utf-8")

            result = write_continuity_snapshot(session_id, "/cwd", mem)
            self.assertTrue(result)

            # After successful write, only the final .md remains; no .tmp orphan.
            self.assertFalse(orphan.exists(), "Orphan .tmp must be cleaned up")
            output = mem / f"continuity_pre_compact_{session_id}.md"
            self.assertTrue(output.exists())
            # Content is fresh — orphan content did not leak in.
            self.assertNotIn("STALE ORPHAN CONTENT", output.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# 15. Privacy: plan files use basename, not absolute path
# ---------------------------------------------------------------------------

class TestPlanFilesUseBasename(unittest.TestCase):
    def test_plan_files_use_basename_not_absolute_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            mem = Path(tmp)
            _write_bridge(mem)

            # Create a synthetic plans dir with a recognizable filename, then
            # patch Path.home() so the writer reads from it.
            fake_home = Path(tmp) / "fake_home"
            fake_plans = fake_home / ".claude" / "plans"
            fake_plans.mkdir(parents=True)
            plan_file = fake_plans / "uniquely-named-plan-7a3.md"
            plan_file.write_text("plan content", encoding="utf-8")

            with patch("continuity_dump.Path.home", return_value=fake_home):
                write_continuity_snapshot("basename_test", "/cwd", mem)

            output = (mem / "continuity_pre_compact_basename_test.md").read_text(encoding="utf-8")

            # The basename should appear...
            self.assertIn("uniquely-named-plan-7a3.md", output)
            # ...but the absolute path (with tmp/fake_home prefix) must not.
            self.assertNotIn(str(plan_file), output)
            self.assertNotIn(str(fake_home), output)


if __name__ == "__main__":
    unittest.main()
