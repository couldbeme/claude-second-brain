"""Tests for Phase 5 Track A: drift detection + save-time confidence.

TDD — written RED before any implementation changes.

Test classes:
- TestBackwardsCompat (3 tests): migration safety + legacy-schema compat
- TestConfidencePropagation (4 tests): save/update/get/hybrid-search confidence
- TestContradictionDetection (4 tests): keyword-inversion detector
"""

from __future__ import annotations

import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

# Add memory-mcp/ to sys.path so we can import db and hybrid_search
SCRIPTS_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPTS_DIR))

from db import MemoryDB  # noqa: E402
from hybrid_search import hybrid_search  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_legacy_db(path: str) -> None:
    """Create a SQLite DB with the OLD schema (no valid_time, transaction_time,
    contradictions table, or confidence).  Inserts one row so we can test
    read-back after migration."""
    conn = sqlite3.connect(path)
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS memories (
            id TEXT PRIMARY KEY,
            content TEXT NOT NULL,
            summary TEXT,
            category TEXT NOT NULL,
            project TEXT,
            tags TEXT DEFAULT '[]',
            source TEXT DEFAULT 'manual',
            session_id TEXT,
            importance INTEGER DEFAULT 5,
            access_count INTEGER DEFAULT 0,
            visibility TEXT NOT NULL DEFAULT 'personal',
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now')),
            expires_at TEXT,
            superseded_by TEXT
        );
        CREATE VIRTUAL TABLE IF NOT EXISTS memory_fts USING fts5(
            content, summary, tags, category,
            content='memories',
            content_rowid='rowid'
        );
    """)
    conn.execute(
        "INSERT INTO memories (id, content, category) VALUES ('legacy-1', 'legacy content', 'context')"
    )
    conn.execute(
        "INSERT INTO memory_fts(rowid, content, summary, tags, category) "
        "VALUES (1, 'legacy content', '', '[]', 'context')"
    )
    conn.commit()
    conn.close()


def _make_legacy_db_5rows(path: str) -> None:
    """Pre-populate a legacy DB with 5 rows."""
    conn = sqlite3.connect(path)
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS memories (
            id TEXT PRIMARY KEY,
            content TEXT NOT NULL,
            summary TEXT,
            category TEXT NOT NULL,
            project TEXT,
            tags TEXT DEFAULT '[]',
            source TEXT DEFAULT 'manual',
            session_id TEXT,
            importance INTEGER DEFAULT 5,
            access_count INTEGER DEFAULT 0,
            visibility TEXT NOT NULL DEFAULT 'personal',
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now')),
            expires_at TEXT,
            superseded_by TEXT
        );
        CREATE VIRTUAL TABLE IF NOT EXISTS memory_fts USING fts5(
            content, summary, tags, category,
            content='memories',
            content_rowid='rowid'
        );
    """)
    for i in range(1, 6):
        conn.execute(
            "INSERT INTO memories (id, content, category) VALUES (?, ?, 'context')",
            (f"row-{i}", f"content {i}"),
        )
        conn.execute(
            "INSERT INTO memory_fts(rowid, content, summary, tags, category) VALUES (?, ?, '', '[]', 'context')",
            (i, f"content {i}"),
        )
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# TestBackwardsCompat
# ---------------------------------------------------------------------------

class TestBackwardsCompat(unittest.TestCase):
    """Migration safety: old schemas must open cleanly and keep all rows."""

    def test_legacy_db_opens_cleanly(self):
        """A DB with the old schema (no valid_time/transaction_time/contradictions/confidence)
        opens without error after MemoryDB migration, and the legacy row is still readable."""
        with tempfile.TemporaryDirectory() as tmp:
            db_path = str(Path(tmp) / "legacy.db")
            _make_legacy_db(db_path)

            # Open with MemoryDB — migration should run without raising
            db = MemoryDB(db_path)
            try:
                result = db.get("legacy-1")
            finally:
                db.close()

            self.assertIsNotNone(result, "Legacy row must still be readable after migration")
            self.assertEqual(result["content"], "legacy content")

    def test_null_confidence_treated_as_default(self):
        """A row inserted with confidence=NULL should be treated as 0.75 by hybrid_search."""
        with tempfile.TemporaryDirectory() as tmp:
            db_path = str(Path(tmp) / "nullconf.db")
            db = MemoryDB(db_path)
            try:
                # Save normally (gets default confidence)
                normal_id = db.save(
                    content="alpha bravo charlie keyword",
                    category="context",
                    importance=5,
                    confidence=0.75,
                )
                # Manually set the confidence to NULL via raw SQL to simulate legacy
                db.conn.execute(
                    "UPDATE memories SET confidence = NULL WHERE id = ?", (normal_id,)
                )
                db.conn.commit()

                # get() should return the row (not crash)
                row = db.get(normal_id)
                self.assertIsNotNone(row)
                # confidence key should be present; NULL → default 0.75
                self.assertIn("confidence", row)
                conf = row["confidence"]
                if conf is None:
                    conf = 0.75
                self.assertAlmostEqual(conf, 0.75, places=5)

                # hybrid_search must not crash and must score it as if confidence=0.75
                results = hybrid_search(db, "alpha bravo charlie keyword", None)
                # Row must appear in results; check confidence key present
                matching = [r for r in results if r["id"] == normal_id]
                self.assertTrue(len(matching) > 0, "NULL-confidence row must appear in search results")
                self.assertIn("confidence", matching[0])
                self.assertAlmostEqual(matching[0]["confidence"], 0.75, places=5)
            finally:
                db.close()

    def test_existing_row_count_preserved(self):
        """Opening a 5-row legacy DB with MemoryDB must not lose any rows."""
        with tempfile.TemporaryDirectory() as tmp:
            db_path = str(Path(tmp) / "five.db")
            _make_legacy_db_5rows(db_path)

            db = MemoryDB(db_path)
            try:
                count = db.conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
            finally:
                db.close()

            self.assertEqual(count, 5, "All 5 pre-existing rows must survive migration")


# ---------------------------------------------------------------------------
# TestConfidencePropagation
# ---------------------------------------------------------------------------

class TestConfidencePropagation(unittest.TestCase):
    """Confidence flows through save → DB → get / list / search / hybrid."""

    def _fresh_db(self, tmp: str) -> MemoryDB:
        return MemoryDB(str(Path(tmp) / "mem.db"))

    def test_save_default_confidence_075(self):
        """Save without explicit confidence → DB stores 0.75."""
        with tempfile.TemporaryDirectory() as tmp:
            db = self._fresh_db(tmp)
            try:
                mem_id = db.save(content="default confidence test", category="context")
                row = db.conn.execute(
                    "SELECT confidence FROM memories WHERE id = ?", (mem_id,)
                ).fetchone()
            finally:
                db.close()

            self.assertIsNotNone(row)
            self.assertAlmostEqual(row[0], 0.75, places=5)

    def test_save_explicit_confidence_clamped(self):
        """confidence=1.5 → stored as 1.0; confidence=-0.3 → stored as 0.0."""
        with tempfile.TemporaryDirectory() as tmp:
            db = self._fresh_db(tmp)
            try:
                id_high = db.save(
                    content="high confidence test", category="context", confidence=1.5
                )
                id_low = db.save(
                    content="low confidence test", category="context", confidence=-0.3
                )
                high_row = db.conn.execute(
                    "SELECT confidence FROM memories WHERE id = ?", (id_high,)
                ).fetchone()
                low_row = db.conn.execute(
                    "SELECT confidence FROM memories WHERE id = ?", (id_low,)
                ).fetchone()
            finally:
                db.close()

            self.assertAlmostEqual(high_row[0], 1.0, places=5,
                                   msg="1.5 should be clamped to 1.0")
            self.assertAlmostEqual(low_row[0], 0.0, places=5,
                                   msg="-0.3 should be clamped to 0.0")

    def test_update_confidence(self):
        """update() with confidence=0.95 persists the value; readback confirms."""
        with tempfile.TemporaryDirectory() as tmp:
            db = self._fresh_db(tmp)
            try:
                mem_id = db.save(content="will be updated", category="context", confidence=0.5)
                db.update(mem_id, confidence=0.95)
                result = db.get(mem_id)
            finally:
                db.close()

            self.assertIsNotNone(result)
            self.assertIn("confidence", result)
            self.assertAlmostEqual(result["confidence"], 0.95, places=5)

    def test_hybrid_search_confidence_multiplier(self):
        """Two keyword-matching rows: high-confidence (0.95) must rank above low-confidence (0.30)."""
        with tempfile.TemporaryDirectory() as tmp:
            db = self._fresh_db(tmp)
            try:
                # Both rows have the same content (keyword search will score them equally).
                # Only confidence differs.
                id_high = db.save(
                    content="zeta omega search term identical",
                    category="context",
                    importance=5,
                    confidence=0.95,
                )
                id_low = db.save(
                    content="zeta omega search term identical",
                    category="context",
                    importance=5,
                    confidence=0.30,
                )
                results = hybrid_search(db, "zeta omega search term identical", None)
            finally:
                db.close()

            ids_in_order = [r["id"] for r in results]
            self.assertIn(id_high, ids_in_order)
            self.assertIn(id_low, ids_in_order)
            self.assertLess(
                ids_in_order.index(id_high),
                ids_in_order.index(id_low),
                "High-confidence row must rank before low-confidence row",
            )


# ---------------------------------------------------------------------------
# TestContradictionDetection
# ---------------------------------------------------------------------------

class TestContradictionDetection(unittest.TestCase):
    """Keyword-inversion contradiction detector (v0.1, rule-based)."""

    def _fresh_db(self, tmp: str) -> MemoryDB:
        return MemoryDB(str(Path(tmp) / "contra.db"))

    def test_keyword_inversion_flagged(self):
        """'always' in one row + 'never' in other row → contradiction recorded."""
        with tempfile.TemporaryDirectory() as tmp:
            db = self._fresh_db(tmp)
            try:
                id_a = db.save(
                    content="feature X is always available",
                    category="context",
                    project="proj-p",
                    tags=["x"],
                )
                id_b = db.save(
                    content="feature X is never available",
                    category="context",
                    project="proj-p",
                    tags=["x"],
                )
                conflicts = db.get_contradictions(id_b)
            finally:
                db.close()

            self.assertIn(id_a, conflicts,
                          f"id_a ({id_a}) must appear in contradictions of id_b. Got: {conflicts}")

    def test_no_contradiction_outside_30_days(self):
        """First row's transaction_time is 31 days ago → no contradiction detected."""
        with tempfile.TemporaryDirectory() as tmp:
            db = self._fresh_db(tmp)
            try:
                id_a = db.save(
                    content="feature X is always available",
                    category="context",
                    project="proj-p",
                    tags=["x"],
                )
                # Age the first row's transaction_time to 31 days ago
                db.conn.execute(
                    "UPDATE memories SET transaction_time = datetime('now', '-31 days') WHERE id = ?",
                    (id_a,),
                )
                db.conn.commit()

                id_b = db.save(
                    content="feature X is never available",
                    category="context",
                    project="proj-p",
                    tags=["x"],
                )
                conflicts = db.get_contradictions(id_b)
            finally:
                db.close()

            self.assertNotIn(id_a, conflicts,
                             "Row older than 30 days must not be flagged as contradiction")

    def test_no_contradiction_different_project(self):
        """Same keywords but different projects → no contradiction."""
        with tempfile.TemporaryDirectory() as tmp:
            db = self._fresh_db(tmp)
            try:
                id_a = db.save(
                    content="feature X is always available",
                    category="context",
                    project="project-alpha",
                    tags=["x"],
                )
                id_b = db.save(
                    content="feature X is never available",
                    category="context",
                    project="project-beta",
                    tags=["x"],
                )
                conflicts = db.get_contradictions(id_b)
            finally:
                db.close()

            self.assertNotIn(id_a, conflicts,
                             "Different projects must not produce contradictions")

    def test_soft_contradiction_skipped(self):
        """Qualifier word 'sometimes' in either row → contradiction is skipped."""
        with tempfile.TemporaryDirectory() as tmp:
            db = self._fresh_db(tmp)
            try:
                id_a = db.save(
                    content="feature X is sometimes available",
                    category="context",
                    project="proj-p",
                    tags=["x"],
                )
                id_b = db.save(
                    content="feature X is never available",
                    category="context",
                    project="proj-p",
                    tags=["x"],
                )
                conflicts = db.get_contradictions(id_b)
            finally:
                db.close()

            self.assertNotIn(id_a, conflicts,
                             "Qualifier word 'sometimes' should suppress the contradiction flag")


if __name__ == "__main__":
    unittest.main()
