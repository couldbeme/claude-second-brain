"""Tests for coherence_gate.py — the coherence-gated write path.

TDD-first: written RED before coherence_gate.py / db.find_conflicts() exist.

The gate is the missing piece an Amodei-style review names: csb MEASURES coherence
(CY) but the measurement gated nothing. This wires measure -> threshold -> gate at
the write path. A *fresh* candidate belief that inverts a *load-bearing* existing
belief (confidence >= floor) is BLOCKED from being written until resolved, instead
of silently saved.

Uses in-memory MemoryDB instances — NEVER touches the live ~/.claude memory.db.
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPTS_DIR))

from db import MemoryDB  # noqa: E402
from coherence_gate import evaluate_gate, gated_save  # noqa: E402


def _db(tmp: str) -> MemoryDB:
    return MemoryDB(str(Path(tmp) / "mem.db"))


class TestFindConflicts(unittest.TestCase):
    """db.find_conflicts() — read-only candidate-vs-existing detection."""

    def test_finds_inversion_with_confidence_and_does_not_mutate(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = _db(tmp)
            try:
                db.save(content="Slack deploy notifications are enabled for prod.",
                        category="fact", tags=["slack", "notifications"], confidence=0.9)
                mem_before = db.conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
                contra_before = db.conn.execute("SELECT COUNT(*) FROM contradictions").fetchone()[0]

                conflicts = db.find_conflicts(
                    content="Deploy notifications are disabled to cut noise.",
                    tags=["slack", "notifications"], project=None)

                self.assertEqual(len(conflicts), 1)
                self.assertAlmostEqual(conflicts[0]["confidence"], 0.9)
                self.assertIn("enabled", conflicts[0]["content"])

                # PURE READ: candidate not inserted, no contradiction row written.
                mem_after = db.conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
                contra_after = db.conn.execute("SELECT COUNT(*) FROM contradictions").fetchone()[0]
                self.assertEqual(mem_before, mem_after)
                self.assertEqual(contra_before, contra_after)
            finally:
                db.close()

    def test_no_conflict_returns_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = _db(tmp)
            try:
                db.save(content="Alice prefers tea in the morning.",
                        category="fact", tags=["alice"], confidence=0.9)
                conflicts = db.find_conflicts(
                    content="Bob works remotely on Tuesdays.",
                    tags=["bob"], project=None)
                self.assertEqual(conflicts, [])
            finally:
                db.close()


class TestEvaluateGate(unittest.TestCase):
    """evaluate_gate() — confidence-floor threshold over find_conflicts."""

    def test_blocks_on_load_bearing_contradiction(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = _db(tmp)
            try:
                db.save(content="The staging API key is required for deploys.",
                        category="fact", tags=["deploy", "config"], confidence=0.9)
                decision = evaluate_gate(
                    db, content="The staging API key is optional now we use OIDC.",
                    tags=["deploy", "config"], project=None, confidence_floor=0.8)
                self.assertTrue(decision["blocked"])
                self.assertEqual(decision["decision"], "block")
                self.assertEqual(len(decision["blocking_contradictions"]), 1)
                self.assertIn("required", decision["blocking_contradictions"][0]["content"])
            finally:
                db.close()

    def test_allows_when_contradiction_below_floor(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = _db(tmp)
            try:
                # Existing belief is weak (0.5) — not load-bearing.
                db.save(content="Standup is always at 9am for the user.",
                        category="fact", tags=["standup"], confidence=0.5)
                decision = evaluate_gate(
                    db, content="Standup is never at 9am anymore.",
                    tags=["standup"], project=None, confidence_floor=0.8)
                self.assertFalse(decision["blocked"])
                self.assertEqual(decision["decision"], "allow")
                # The contradiction is still surfaced as advisory, just not blocking.
                self.assertEqual(len(decision["contradictions"]), 1)
                self.assertEqual(decision["blocking_contradictions"], [])
            finally:
                db.close()

    def test_allows_when_no_contradiction(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = _db(tmp)
            try:
                db.save(content="The project deadline is end of May.",
                        category="fact", tags=["project"], confidence=0.9)
                decision = evaluate_gate(
                    db, content="The team uses Python for the backend.",
                    tags=["stack"], project=None, confidence_floor=0.8)
                self.assertFalse(decision["blocked"])
                self.assertEqual(decision["decision"], "allow")
                self.assertEqual(decision["contradictions"], [])
            finally:
                db.close()


class TestGatedSave(unittest.TestCase):
    """gated_save() — the wired control: blocks the write on a load-bearing clash."""

    def test_blocked_write_is_not_persisted(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = _db(tmp)
            try:
                db.save(content="Deploy notifications are enabled for prod.",
                        category="fact", tags=["slack", "notifications"], confidence=0.9)
                result = gated_save(
                    db, content="Deploy notifications are disabled to cut noise.",
                    category="fact", tags=["slack", "notifications"], confidence=0.85,
                    confidence_floor=0.8)
                self.assertFalse(result["saved"])
                self.assertIsNone(result["mem_id"])
                self.assertTrue(result["gate"]["blocked"])
                # The contradicting belief was NOT written.
                n = db.conn.execute(
                    "SELECT COUNT(*) FROM memories WHERE content LIKE '%disabled%'"
                ).fetchone()[0]
                self.assertEqual(n, 0)
            finally:
                db.close()

    def test_clean_write_is_persisted(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = _db(tmp)
            try:
                result = gated_save(
                    db, content="The team uses Python for the backend.",
                    category="fact", tags=["stack"], confidence=0.9,
                    confidence_floor=0.8)
                self.assertTrue(result["saved"])
                self.assertIsNotNone(result["mem_id"])
                self.assertFalse(result["gate"]["blocked"])
                got = db.get(result["mem_id"])
                self.assertIsNotNone(got)
            finally:
                db.close()


if __name__ == "__main__":
    unittest.main()
