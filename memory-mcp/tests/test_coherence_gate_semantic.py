"""Tests for the tiered (structural + semantic) coherence gate.

TDD-first. The semantic tier escalates to an entailment judge for paraphrase
clashes the structural tier misses. The judge is INJECTABLE (judge_fn) so these
tests use a fake and need no model endpoint.

Tiering rationale (latency): Tier-0 structural blocks obvious cases synchronously
with NO judge call; Tier-2 semantic only runs on the survivors. Same abstain-not-
guess rail as the rest of the stack.
"""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPTS_DIR))

from db import MemoryDB  # noqa: E402
from coherence_gate import evaluate_gate_tiered  # noqa: E402


def _db(tmp):
    return MemoryDB(str(Path(tmp) / "m.db"))


class _SpyJudge:
    """Fake judge: records calls; says violates iff `needle` in the action."""
    def __init__(self, needle="force"):
        self.calls = []
        self.needle = needle

    def __call__(self, commitment, action):
        self.calls.append((commitment, action))
        if self.needle in action.lower():
            return {"violates": True, "why": f"semantic match on {self.needle}"}
        return {"violates": False, "why": "ok"}


class TestTieredGate(unittest.TestCase):

    def test_structural_block_does_not_call_judge(self):
        # A literal inversion is caught at Tier-0; the judge must NOT be invoked
        # (fast path — clear cases never pay LLM latency).
        with tempfile.TemporaryDirectory() as tmp:
            db = _db(tmp)
            try:
                db.save(content="Deploy notifications are enabled for prod.",
                        category="fact", tags=["slack"], confidence=0.9)
                spy = _SpyJudge()
                d = evaluate_gate_tiered(
                    db, "Deploy notifications are disabled to cut noise.",
                    ["slack"], judge_fn=spy)
                self.assertTrue(d["blocked"])
                self.assertEqual(d["tier"], "structural")
                self.assertEqual(spy.calls, [])  # judge never called
            finally:
                db.close()

    def test_semantic_tier_catches_paraphrase_structural_misses(self):
        # "git push -f origin HEAD:main" has no inversion tokens vs "never
        # force-push to main" -> Tier-0 allows; the semantic judge catches it.
        with tempfile.TemporaryDirectory() as tmp:
            db = _db(tmp)
            try:
                db.save(content="Never force-push to main.",
                        category="rule", tags=["git"], confidence=0.9)
                spy = _SpyJudge(needle="-f ")
                d = evaluate_gate_tiered(
                    db, "git push -f origin HEAD:main", ["git"], judge_fn=spy)
                self.assertTrue(d["blocked"])
                self.assertEqual(d["tier"], "semantic")
                self.assertTrue(spy.calls)  # judge WAS consulted
            finally:
                db.close()

    def test_semantic_clash_below_floor_not_blocking(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = _db(tmp)
            try:
                db.save(content="Prefer force-push to main.",  # weak prior
                        category="rule", tags=["git"], confidence=0.4)
                spy = _SpyJudge(needle="-f ")
                d = evaluate_gate_tiered(
                    db, "git push -f origin HEAD:main", ["git"],
                    judge_fn=spy, confidence_floor=0.8)
                self.assertFalse(d["blocked"])     # below floor -> advisory
                self.assertEqual(d["decision"], "allow")
            finally:
                db.close()

    def test_judge_abstain_is_not_a_block(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = _db(tmp)
            try:
                db.save(content="Never delete the production database.",
                        category="rule", tags=["db"], confidence=0.9)
                d = evaluate_gate_tiered(
                    db, "DROP TABLE users", ["db"], judge_fn=lambda c, a: None)
                self.assertFalse(d["blocked"])
                self.assertEqual(d["decision"], "allow")
            finally:
                db.close()

    def test_escalate_false_is_pure_structural(self):
        # With escalate=False, behaves like v0.1 evaluate_gate: paraphrase allowed,
        # judge never touched.
        with tempfile.TemporaryDirectory() as tmp:
            db = _db(tmp)
            try:
                db.save(content="Never force-push to main.",
                        category="rule", tags=["git"], confidence=0.9)
                spy = _SpyJudge(needle="-f ")
                d = evaluate_gate_tiered(
                    db, "git push -f origin HEAD:main", ["git"],
                    judge_fn=spy, escalate=False)
                self.assertFalse(d["blocked"])
                self.assertEqual(spy.calls, [])
            finally:
                db.close()

    def test_no_tag_neighbors_no_judge_call(self):
        # Nothing shares a tag -> no candidates -> judge not called, allow.
        with tempfile.TemporaryDirectory() as tmp:
            db = _db(tmp)
            try:
                db.save(content="Never force-push to main.",
                        category="rule", tags=["git"], confidence=0.9)
                spy = _SpyJudge(needle="-f ")
                d = evaluate_gate_tiered(
                    db, "send the report to finance", ["email"], judge_fn=spy)
                self.assertFalse(d["blocked"])
                self.assertEqual(spy.calls, [])
            finally:
                db.close()

    def test_no_judge_fn_falls_back_to_structural(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = _db(tmp)
            try:
                db.save(content="Never force-push to main.",
                        category="rule", tags=["git"], confidence=0.9)
                d = evaluate_gate_tiered(
                    db, "git push -f origin HEAD:main", ["git"], judge_fn=None)
                self.assertFalse(d["blocked"])  # no judge -> structural only
                self.assertEqual(d["tier"], "structural")
            finally:
                db.close()


if __name__ == "__main__":
    unittest.main()
