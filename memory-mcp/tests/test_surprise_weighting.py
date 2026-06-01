"""Tests for surprise-weighting at write-time (gate-1 of the mechanical cognition path).

A new memory's salience should reflect how much it DIVERGED from what the store
already holds — contradicting a high-confidence prior is surprising; a familiar,
uncontested fact is not. This is the prediction-ish half the corpus audit found
absent (importance was a manual constant). v0.1 is a deterministic heuristic over
records — a salience signal, NOT a claim the system "is surprised" (Weizenbaum).

Honesty rails under test:
- surprise is a SEPARATE column; it does NOT overwrite the operator's manual importance.
- first-of-its-kind (no prior to diverge from) is surprise≈0, not high (documented choice).
- clamped [0,1]; migration is additive + idempotent.
"""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPTS_DIR))

from db import MemoryDB  # noqa: E402


def _db(tmp):
    return MemoryDB(str(Path(tmp) / "m.db"))


def _surprise(db, mem_id):
    row = db.conn.execute("SELECT surprise FROM memories WHERE id = ?", (mem_id,)).fetchone()
    return row[0] if row else None


class TestSurpriseColumn(unittest.TestCase):
    def test_column_exists_and_defaults_zero(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = _db(tmp)
            try:
                mid = db.save(content="The team uses Python.", category="fact",
                              tags=["stack"], confidence=0.8)
                self.assertIsNotNone(_surprise(db, mid))
            finally:
                db.close()


class TestSurpriseComputation(unittest.TestCase):
    def test_first_of_its_kind_is_low_surprise(self):
        # Nothing to diverge from -> not surprising under this heuristic.
        with tempfile.TemporaryDirectory() as tmp:
            db = _db(tmp)
            try:
                mid = db.save(content="Standup is always at 9am.", category="fact",
                              tags=["standup"], confidence=0.8)
                self.assertLess(_surprise(db, mid), 0.3)
            finally:
                db.close()

    def test_contradicting_high_confidence_prior_is_high_surprise(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = _db(tmp)
            try:
                db.save(content="Slack deploy notifications are enabled for prod.",
                        category="fact", tags=["slack"], confidence=0.95)
                mid = db.save(content="Deploy notifications are disabled to cut noise.",
                              category="fact", tags=["slack"], confidence=0.7)
                self.assertGreater(_surprise(db, mid), 0.5)
            finally:
                db.close()

    def test_contradicting_low_confidence_prior_is_low_surprise(self):
        # Contradicting something the store wasn't sure of isn't surprising.
        with tempfile.TemporaryDirectory() as tmp:
            db = _db(tmp)
            try:
                db.save(content="Deploy notifications are enabled for prod.",
                        category="fact", tags=["slack"], confidence=0.3)
                mid = db.save(content="Deploy notifications are disabled to cut noise.",
                              category="fact", tags=["slack"], confidence=0.7)
                self.assertLess(_surprise(db, mid), 0.5)
            finally:
                db.close()

    def test_clamped_0_1(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = _db(tmp)
            try:
                db.save(content="Standup is always at 9am.", category="fact",
                        tags=["standup", "schedule"], confidence=1.0)
                mid = db.save(content="Standup is never at 9am anymore.",
                              category="fact", tags=["standup", "schedule"], confidence=0.9)
                s = _surprise(db, mid)
                self.assertGreaterEqual(s, 0.0)
                self.assertLessEqual(s, 1.0)
            finally:
                db.close()


class TestSurpriseDoesNotOverwriteImportance(unittest.TestCase):
    def test_manual_importance_unchanged_by_surprise(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = _db(tmp)
            try:
                db.save(content="Never force-push to main.", category="rule",
                        tags=["git"], confidence=0.95)
                mid = db.save(content="Force-push to main is fine now.", category="rule",
                              tags=["git"], confidence=0.7, importance=3)
                imp = db.conn.execute(
                    "SELECT importance FROM memories WHERE id = ?", (mid,)).fetchone()[0]
                self.assertEqual(imp, 3)  # surprise is separate; importance untouched
            finally:
                db.close()


class TestMigrationIdempotent(unittest.TestCase):
    def test_reopen_does_not_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = str(Path(tmp) / "m.db")
            db1 = MemoryDB(p); db1.save(content="x", category="fact", tags=["a"]); db1.close()
            db2 = MemoryDB(p)  # second open must not error on the surprise column
            try:
                cols = [r[1] for r in db2.conn.execute("PRAGMA table_info(memories)").fetchall()]
                self.assertIn("surprise", cols)
            finally:
                db2.close()


if __name__ == "__main__":
    unittest.main()
