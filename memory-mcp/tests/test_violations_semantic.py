"""Tests for judge-backed feedback-violation detection (P2.5).

P1 proved the keyword matcher in feedback_violations.extract_trigger_patterns is a
toy (30% recall, 0% paraphrase). This wires the proven entailment judge in as the
detector. The judge is INJECTABLE (judge_fn) so these tests run with a fake judge
and need no model endpoint — only the deterministic wiring is unit-tested.

Connection (insight, 2026-06-01): feedback memories ARE persistent commitments;
detecting an action that violates one is the SAME entailment as commitment-drift.
"""
from __future__ import annotations

import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPTS_DIR))

import unittest
from db import MemoryDB  # noqa: E402
from violations_semantic import detect_violations_semantic  # noqa: E402


def _db(tmp):
    return MemoryDB(str(Path(tmp) / "m.db"))


def _seed_rule(db, content):
    return db.save(content=content, category="rule", tags=["rule"], confidence=0.9)


class TestDetectViolationsSemantic(unittest.TestCase):
    def test_flags_action_that_violates_a_rule(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            db = _db(tmp)
            try:
                rid = _seed_rule(db, "Never force-push to main.")
                # fake judge: violates iff the action paraphrases a force-push
                def fake_judge(commitment, action):
                    if "force" in action.lower() or "-f " in action.lower():
                        return {"violates": True, "why": "force-push"}
                    return {"violates": False, "why": "ok"}
                v = detect_violations_semantic(
                    db, ["git push -f origin HEAD:main"], judge_fn=fake_judge)
                self.assertEqual(len(v), 1)
                self.assertEqual(v[0]["feedback_memory_id"], rid)
                self.assertIn("force", v[0]["why"])
            finally:
                db.close()

    def test_clean_action_no_violation(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            db = _db(tmp)
            try:
                _seed_rule(db, "Never force-push to main.")
                v = detect_violations_semantic(
                    db, ["git status"], judge_fn=lambda c, a: {"violates": False, "why": "ok"})
                self.assertEqual(v, [])
            finally:
                db.close()

    def test_abstain_is_not_a_violation(self):
        # judge returns None (unparseable) -> must NOT be counted as a violation
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            db = _db(tmp)
            try:
                _seed_rule(db, "Never delete user records.")
                v = detect_violations_semantic(
                    db, ["DROP TABLE users"], judge_fn=lambda c, a: None)
                self.assertEqual(v, [])
            finally:
                db.close()

    def test_records_to_table_when_record_true(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            db = _db(tmp)
            try:
                _seed_rule(db, "Never commit secrets.")
                detect_violations_semantic(
                    db, ["git add .env && commit secrets"],
                    judge_fn=lambda c, a: {"violates": True, "why": "secret commit"},
                    record=True)
                n = db.conn.execute("SELECT COUNT(*) FROM feedback_violations").fetchone()[0]
                self.assertEqual(n, 1)
            finally:
                db.close()

    def test_no_double_count_same_pair(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            db = _db(tmp)
            try:
                _seed_rule(db, "Never force-push to main.")
                v = detect_violations_semantic(
                    db, ["git push --force main", "git push --force main"],
                    judge_fn=lambda c, a: {"violates": True, "why": "x"})
                # same (rule, action) text appears twice -> dedupe to 1
                self.assertEqual(len(v), 1)
            finally:
                db.close()


if __name__ == "__main__":
    unittest.main()
