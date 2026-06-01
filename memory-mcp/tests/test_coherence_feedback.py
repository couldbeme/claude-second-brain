"""TDD for coherence_feedback.py — the action-gate feedback edge.

Two functions, deliberately split (corrected from decay-on-block):
  - record_block(db, blocking_contradiction, *, session_id, action_hash) -> bool
        Fires on EVERY gate block. DIAGNOSTIC ONLY: records a violation row so
        CY-behavior moves. NEVER mutates confidence. Fail-open.
  - apply_override_decay(db, commitment_id, *, decay, min_confidence, reason) -> float
        The ONLY path that lowers a commitment's confidence. Human-gated
        (a person judged a logged block a false positive). NOT in the hot path.

Validated un-redundant vs native 2026: Auto-Dream resolves memory-vs-memory
contradictions retroactively; this is action-vs-commitment feedback at action-time.

ASSUMPTIONS to confirm against the live module (flagged, not asserted as fact):
  - table `memories` has a `confidence` column; violations land in `feedback_violations`
  - db.save(...) returns the new memory id
  - a blocking_contradiction is a dict carrying at least {"id", "confidence"}
"""
from __future__ import annotations

import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPTS_DIR))

from db import MemoryDB  # noqa: E402
from coherence_feedback import record_block, apply_override_decay  # noqa: E402


def _seed_commitment(dbp: str, content: str, conf: float = 0.9):
    db = MemoryDB(dbp)
    try:
        return db.save(content=content, category="rule", tags=["git"], confidence=conf)
    finally:
        db.close()


def _confidence_of(dbp: str, mem_id):
    con = sqlite3.connect(dbp)
    try:
        row = con.execute("SELECT confidence FROM memories WHERE id=?", (mem_id,)).fetchone()
        return row[0] if row else None
    finally:
        con.close()


def _violation_count(dbp: str):
    con = sqlite3.connect(dbp)
    try:
        return con.execute("SELECT COUNT(*) FROM feedback_violations").fetchone()[0]
    finally:
        con.close()


class TestRecordBlock(unittest.TestCase):

    def test_block_records_violation_but_does_not_touch_confidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            dbp = str(Path(tmp) / "m.db")
            cid = _seed_commitment(dbp, "Never force-push to main.", 0.9)
            bc = {"id": cid, "confidence": 0.9}
            db = MemoryDB(dbp)
            try:
                self.assertTrue(record_block(db, bc, session_id="s1", action_hash="a1"))
            finally:
                db.close()
            self.assertEqual(_violation_count(dbp), 1)          # CY-behavior moves
            self.assertEqual(_confidence_of(dbp, cid), 0.9)     # belief untouched

    def test_persistence_does_NOT_erode_the_guardrail(self):
        # THE regression test for the corrected design: retrying a blocked action
        # any number of times must never lower the commitment's confidence.
        with tempfile.TemporaryDirectory() as tmp:
            dbp = str(Path(tmp) / "m.db")
            cid = _seed_commitment(dbp, "Never force-push to main.", 0.9)
            db = MemoryDB(dbp)
            try:
                for i in range(5):
                    record_block(db, {"id": cid, "confidence": 0.9},
                                 session_id=f"s{i}", action_hash="same-act")
            finally:
                db.close()
            self.assertEqual(_confidence_of(dbp, cid), 0.9)     # still 0.9 after 5 blocks

    def test_dedupes_same_action_within_session(self):
        with tempfile.TemporaryDirectory() as tmp:
            dbp = str(Path(tmp) / "m.db")
            cid = _seed_commitment(dbp, "Never force-push to main.", 0.9)
            db = MemoryDB(dbp)
            try:
                record_block(db, {"id": cid, "confidence": 0.9}, session_id="s1", action_hash="a1")
                record_block(db, {"id": cid, "confidence": 0.9}, session_id="s1", action_hash="a1")
            finally:
                db.close()
            self.assertEqual(_violation_count(dbp), 1)          # one row, not two

    def test_fail_open_on_bad_contradiction(self):
        # A malformed bc (no id) must not raise — the block decision is already made.
        with tempfile.TemporaryDirectory() as tmp:
            dbp = str(Path(tmp) / "m.db")
            db = MemoryDB(dbp)
            try:
                self.assertFalse(record_block(db, {"confidence": 0.9}, session_id="s1", action_hash="a1"))
            finally:
                db.close()


class TestApplyOverrideDecay(unittest.TestCase):

    def test_lowers_by_fixed_step(self):
        with tempfile.TemporaryDirectory() as tmp:
            dbp = str(Path(tmp) / "m.db")
            cid = _seed_commitment(dbp, "Never force-push to main.", 0.9)
            db = MemoryDB(dbp)
            try:
                new = apply_override_decay(db, cid, decay=0.1, min_confidence=0.5,
                                           reason="reviewed: rule too strict for this repo")
            finally:
                db.close()
            self.assertAlmostEqual(new, 0.8)
            self.assertAlmostEqual(_confidence_of(dbp, cid), 0.8)

    def test_clamps_at_floor_never_below(self):
        with tempfile.TemporaryDirectory() as tmp:
            dbp = str(Path(tmp) / "m.db")
            cid = _seed_commitment(dbp, "Never force-push to main.", 0.55)
            db = MemoryDB(dbp)
            try:
                a = apply_override_decay(db, cid, decay=0.1, min_confidence=0.5, reason="r")
                b = apply_override_decay(db, cid, decay=0.1, min_confidence=0.5, reason="r")
            finally:
                db.close()
            self.assertAlmostEqual(a, 0.5)   # 0.55-0.10 clamped to floor
            self.assertAlmostEqual(b, 0.5)   # stays at floor, never 0

    def test_requires_nonempty_reason(self):
        with tempfile.TemporaryDirectory() as tmp:
            dbp = str(Path(tmp) / "m.db")
            cid = _seed_commitment(dbp, "Never force-push to main.", 0.9)
            db = MemoryDB(dbp)
            try:
                with self.assertRaises(ValueError):
                    apply_override_decay(db, cid, decay=0.1, min_confidence=0.5, reason="")
                self.assertAlmostEqual(_confidence_of(dbp, cid), 0.9)  # unchanged on refusal
            finally:
                db.close()

    def test_below_gate_floor_is_human_reachable_only(self):
        # Two human overrides take it under the 0.8 gate floor — the ONLY route there.
        with tempfile.TemporaryDirectory() as tmp:
            dbp = str(Path(tmp) / "m.db")
            cid = _seed_commitment(dbp, "Never force-push to main.", 0.9)
            db = MemoryDB(dbp)
            try:
                apply_override_decay(db, cid, decay=0.1, min_confidence=0.5, reason="r1")
                apply_override_decay(db, cid, decay=0.1, min_confidence=0.5, reason="r2")
            finally:
                db.close()
            self.assertAlmostEqual(_confidence_of(dbp, cid), 0.7)  # 0.9 -> 0.8 -> 0.7 < gate floor


if __name__ == "__main__":
    unittest.main()
