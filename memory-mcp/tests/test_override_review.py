"""TDD for override_review.py — the human override surface for the commitment gate.

The gate is honest because only a HUMAN softens a commitment. This CLI is that
human's surface: review what the gate flagged (recorded in feedback_violations),
then deliberately lower one commitment's confidence via apply_override_decay.

Split by dependency:
  - review()/`list` read feedback_violations + memories → GREEN now (no dependency
    on the in-flight coherence_feedback module; violations seeded via the existing
    record_violation write path).
  - override()/`override` call coherence_feedback.apply_override_decay → guarded with
    skipUnless so the suite stays green and these activate the moment the module lands.
"""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPTS_DIR))

from db import MemoryDB  # noqa: E402
from feedback_violations import record_violation  # noqa: E402
from override_review import review, apply_override, main  # noqa: E402

try:
    import coherence_feedback  # noqa: F401
    _HAS_CF = True
except Exception:
    _HAS_CF = False


def _db(tmp: str) -> MemoryDB:
    return MemoryDB(str(Path(tmp) / "m.db"))


def _seed_commitment(db: MemoryDB, content="Never force-push to main.", conf=0.9) -> str:
    return db.save(content=content, category="rule", tags=["git"], confidence=conf)


class TestReview(unittest.TestCase):

    def test_lists_blocked_commitments_with_block_counts(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = _db(tmp)
            try:
                cid = _seed_commitment(db)
                record_violation(db, cid, "git push -f origin main",
                                 "commitment-gate-block", session_id="s1")
                record_violation(db, cid, "git push --force",
                                 "commitment-gate-block", session_id="s2")
                rows = review(db)
            finally:
                db.close()
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["id"], cid)
            self.assertEqual(rows[0]["n_blocks"], 2)
            self.assertAlmostEqual(rows[0]["confidence"], 0.9)

    def test_empty_when_no_blocks(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = _db(tmp)
            try:
                _seed_commitment(db)  # a commitment, but never blocked
                self.assertEqual(review(db), [])
            finally:
                db.close()

    def test_list_cli_exit0(self):
        with tempfile.TemporaryDirectory() as tmp:
            dbp = str(Path(tmp) / "m.db")
            db = MemoryDB(dbp)
            try:
                cid = _seed_commitment(db)
                record_violation(db, cid, "git push -f", "commitment-gate-block", "s1")
            finally:
                db.close()
            self.assertEqual(main(["list", "--db", dbp]), 0)


@unittest.skipUnless(_HAS_CF, "coherence_feedback (apply_override_decay) not landed yet")
class TestOverride(unittest.TestCase):

    def test_override_lowers_confidence_by_one_step(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = _db(tmp)
            try:
                cid = _seed_commitment(db, conf=0.9)
                new = apply_override(db, cid, decay=0.1, min_confidence=0.5,
                                     reason="reviewed: rule too strict for this repo")
                row = db.conn.execute(
                    "SELECT confidence FROM memories WHERE id=?", (cid,)).fetchone()
            finally:
                db.close()
            self.assertAlmostEqual(new, 0.8)
            self.assertAlmostEqual(row[0], 0.8)

    def test_override_empty_reason_refused_exit2_confidence_unchanged(self):
        with tempfile.TemporaryDirectory() as tmp:
            dbp = str(Path(tmp) / "m.db")
            db = MemoryDB(dbp)
            try:
                cid = _seed_commitment(db, conf=0.9)
            finally:
                db.close()
            rc = main(["override", "--id", cid, "--reason", "", "--db", dbp])
            db = MemoryDB(dbp)
            try:
                conf = db.conn.execute(
                    "SELECT confidence FROM memories WHERE id=?", (cid,)).fetchone()[0]
            finally:
                db.close()
            self.assertEqual(rc, 2)              # refused
            self.assertAlmostEqual(conf, 0.9)    # belief untouched on refusal


if __name__ == "__main__":
    unittest.main()
