"""Tests for MYTHOS-SUBSTRATE Phase 1: feedback-violation detector.

TDD — RED before any implementation. Test classes:
- TestFeedbackViolationsSchema: schema migration safety + idempotency
- TestPatternExtraction: extract trigger patterns from feedback memory content
- TestViolationDetection: matches known triggers, no false positives on neutral text
- TestRecordAndQuery: insert violation row, query back
- TestCYBehavior: empty violations → CY-behavior=1.0; many violations → lower
- TestCYTotal: weighted combination of CY-memory + CY-behavior
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPTS_DIR))

from db import MemoryDB  # noqa: E402
from efficacy_measure import coherence_yield, coherence_yield_behavior, coherence_yield_total  # noqa: E402
from feedback_violations import (  # noqa: E402
    extract_trigger_patterns,
    detect_violations,
    record_violation,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_db_with_feedback(tmpdir: Path) -> MemoryDB:
    """Create a fresh DB and seed it with two feedback memories."""
    db = MemoryDB(str(tmpdir / "test.db"))
    db.save(
        content=(
            "Rule: never re-read unchanged files.\n\n"
            "**Why:** re-reads burn tokens.\n"
            "**How to apply:** before any Read tool call, ask if the file was "
            "already read this conversation."
        ),
        category="pattern",
        summary="Never re-read unchanged files",
        importance=10,
        confidence=0.95,
        tags=["feedback", "tokens"],
    )
    db.save(
        content=(
            "Rule: stop summarizing what you just did at the end of every response.\n\n"
            "**Why:** the user can read the diff.\n"
            "**How to apply:** when a response ends with a recap of work just done, cut it."
        ),
        category="pattern",
        summary="No trailing summaries",
        importance=8,
        confidence=0.85,
        tags=["feedback", "verbosity"],
    )
    return db


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

class TestFeedbackViolationsSchema(unittest.TestCase):
    def test_table_created_on_init(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = MemoryDB(str(Path(tmp) / "t.db"))
            cols = db.conn.execute("PRAGMA table_info(feedback_violations)").fetchall()
            self.assertGreater(len(cols), 0, "feedback_violations table must exist")
            col_names = {c[1] for c in cols}
            for required in ("id", "feedback_memory_id", "matched_text", "matched_pattern", "detected_at", "resolution"):
                self.assertIn(required, col_names)

    def test_init_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = str(Path(tmp) / "t.db")
            MemoryDB(path)
            MemoryDB(path)  # second open must not error


# ---------------------------------------------------------------------------
# Pattern extraction
# ---------------------------------------------------------------------------

class TestPatternExtraction(unittest.TestCase):
    def test_extract_from_how_to_apply_section(self):
        content = (
            "Rule: don't push article files publicly.\n\n"
            "**How to apply:** if any output is article-shaped (essay, draft, post), "
            "default destination is private archive."
        )
        patterns = extract_trigger_patterns(content)
        self.assertTrue(any("article" in p.lower() for p in patterns))

    def test_extract_returns_list_of_strings(self):
        patterns = extract_trigger_patterns("Rule: always verify before asserting.")
        self.assertIsInstance(patterns, list)
        self.assertTrue(all(isinstance(p, str) for p in patterns))

    def test_extract_from_empty_content(self):
        # Empty content should return empty list, not crash
        self.assertEqual(extract_trigger_patterns(""), [])
        self.assertEqual(extract_trigger_patterns("   \n  "), [])


# ---------------------------------------------------------------------------
# Violation detection
# ---------------------------------------------------------------------------

class TestViolationDetection(unittest.TestCase):
    def test_detects_match_against_feedback_memory(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = _make_db_with_feedback(Path(tmp))
            # Session text echoes a re-read pattern
            session_text = (
                "Let me re-read unchanged files to make sure I have the latest content."
            )
            violations = detect_violations(db, session_text)
            self.assertGreaterEqual(len(violations), 1, "should detect re-read pattern")
            v = violations[0]
            self.assertIn("feedback_memory_id", v)
            self.assertIn("matched_text", v)
            self.assertIn("matched_pattern", v)

    def test_no_false_positive_on_neutral_text(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = _make_db_with_feedback(Path(tmp))
            session_text = "Implementing the user authentication endpoint with JWT tokens."
            violations = detect_violations(db, session_text)
            self.assertEqual(len(violations), 0)

    def test_detects_multiple_distinct_violations(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = _make_db_with_feedback(Path(tmp))
            session_text = (
                "Let me re-read unchanged files. "
                "And here's a summary of what I just did at the end of this response."
            )
            violations = detect_violations(db, session_text)
            distinct_memories = {v["feedback_memory_id"] for v in violations}
            self.assertGreaterEqual(len(distinct_memories), 1)


# ---------------------------------------------------------------------------
# Record and query
# ---------------------------------------------------------------------------

class TestRecordAndQuery(unittest.TestCase):
    def test_record_violation_returns_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = _make_db_with_feedback(Path(tmp))
            mem_id = db.list_memories()[0]["id"]
            vid = record_violation(db, mem_id, "matched snippet", "trigger pattern", session_id="s-1")
            self.assertIsInstance(vid, str)
            self.assertGreater(len(vid), 0)

    def test_recorded_row_persisted(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = _make_db_with_feedback(Path(tmp))
            mem_id = db.list_memories()[0]["id"]
            vid = record_violation(db, mem_id, "snippet", "pattern", session_id="s-1")
            row = db.conn.execute(
                "SELECT id, feedback_memory_id, matched_text, resolution FROM feedback_violations WHERE id = ?",
                (vid,),
            ).fetchone()
            self.assertIsNotNone(row)
            self.assertEqual(row[1], mem_id)
            self.assertEqual(row[3], "unresolved")


# ---------------------------------------------------------------------------
# CY-behavior + CY-total
# ---------------------------------------------------------------------------

class TestCYBehavior(unittest.TestCase):
    NOW = datetime(2026, 4, 29, 12, 0, 0)

    def test_empty_violations_yields_one(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = MemoryDB(str(Path(tmp) / "t.db"))
            result = coherence_yield_behavior(db, window_days=30, now=self.NOW)
            self.assertAlmostEqual(result["cy_behavior"], 1.0)
            self.assertEqual(result["n_violations"], 0)

    def test_violations_lower_cy_behavior(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = _make_db_with_feedback(Path(tmp))
            mem_id = db.list_memories()[0]["id"]
            for i in range(5):
                record_violation(db, mem_id, f"snippet-{i}", "pat", session_id="s-1")
            result = coherence_yield_behavior(db, window_days=30, now=self.NOW)
            self.assertLess(result["cy_behavior"], 1.0)
            self.assertEqual(result["n_violations"], 5)

    def test_resolved_violations_dont_penalize_as_much(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = _make_db_with_feedback(Path(tmp))
            mem_id = db.list_memories()[0]["id"]
            for i in range(3):
                vid = record_violation(db, mem_id, f"s-{i}", "p", session_id="s-1")
                db.conn.execute(
                    "UPDATE feedback_violations SET resolution = 'fixed' WHERE id = ?",
                    (vid,),
                )
            db.conn.commit()
            result = coherence_yield_behavior(db, window_days=30, now=self.NOW)
            # 3 fixed / 0 unresolved → drift = 0, so cy_behavior closer to 1
            self.assertGreater(result["cy_behavior"], 0.5)


class TestCYTotal(unittest.TestCase):
    NOW = datetime(2026, 4, 29, 12, 0, 0)

    def test_combines_memory_and_behavior_weighted(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = _make_db_with_feedback(Path(tmp))
            result = coherence_yield_total(db, alpha=0.7, window_days=30, now=self.NOW)
            self.assertIn("cy_total", result)
            self.assertIn("cy_memory", result)
            self.assertIn("cy_behavior", result)
            # Weighted combo: alpha * cy_memory + (1-alpha) * cy_behavior
            expected = 0.7 * result["cy_memory"] + 0.3 * result["cy_behavior"]
            self.assertAlmostEqual(result["cy_total"], expected, places=6)

    def test_alpha_bounds_validated(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = MemoryDB(str(Path(tmp) / "t.db"))
            with self.assertRaises(ValueError):
                coherence_yield_total(db, alpha=1.5, now=self.NOW)
            with self.assertRaises(ValueError):
                coherence_yield_total(db, alpha=-0.1, now=self.NOW)


if __name__ == "__main__":
    unittest.main()
