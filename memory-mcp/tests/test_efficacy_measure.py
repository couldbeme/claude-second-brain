"""Tests for efficacy_measure.py — Coherence Yield (CY) implementation.

TDD-first: all tests written RED before efficacy_measure.py exists.

Fixture corpus: 5-10 hand-curated memories with known contradictions and
precomputed expected CY values. Uses in-memory MemoryDB instances — NEVER
touches the live ~/.claude/memory/memory.db.

contradictions table DDL (from db.py:98-108):
    CREATE TABLE IF NOT EXISTS contradictions (
        id TEXT PRIMARY KEY,
        memory_a_id TEXT NOT NULL,
        memory_b_id TEXT NOT NULL,
        detected_at TEXT DEFAULT (datetime('now')),
        resolution TEXT DEFAULT 'unresolved',
        FOREIGN KEY (memory_a_id) REFERENCES memories(id),
        FOREIGN KEY (memory_b_id) REFERENCES memories(id)
    )
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

# Add memory-mcp/ to sys.path
SCRIPTS_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPTS_DIR))

from db import MemoryDB  # noqa: E402
from efficacy_measure import coherence_yield  # noqa: E402

# Fixed reference timestamp — all tests use this so results are deterministic (F6 fix).
_NOW = datetime(2026, 4, 27, 12, 0, 0)
_WINDOW = 30


def _db(tmp: str) -> MemoryDB:
    """Open a fresh in-process MemoryDB in the given tmp dir."""
    return MemoryDB(str(Path(tmp) / "mem.db"))


def _age(db: MemoryDB, mem_id: str, days: int) -> None:
    """Back-date transaction_time and created_at for a memory by `days` days."""
    ts = (datetime(2026, 4, 27, 12, 0, 0) - timedelta(days=days)).isoformat()
    db.conn.execute(
        "UPDATE memories SET transaction_time = ?, created_at = ? WHERE id = ?",
        (ts, ts, mem_id),
    )
    db.conn.commit()


# ---------------------------------------------------------------------------
# Fixture: known-answer hand-curated corpus
# ---------------------------------------------------------------------------

def _build_zero_contradiction_corpus(db: MemoryDB) -> None:
    """5 memories with no inversion-pair contradictions; expected CY = 1.0."""
    contents = [
        ("Alice prefers tea in the morning", ["alice", "preference"]),
        ("Alice works remotely on Tuesdays", ["alice", "schedule"]),
        ("Bob is always punctual for meetings", ["bob", "meetings"]),
        ("The standup happens at 10am daily", ["standup", "schedule"]),
        ("The project deadline is end of May", ["project", "deadline"]),
    ]
    for content, tags in contents:
        db.save(content=content, category="context", tags=tags, confidence=0.8)


def _build_one_contradiction_resolved(db: MemoryDB) -> tuple[str, str]:
    """
    One contradiction pair, resolution = 'a-supersedes-b'.
    Δ_drift = 0 (fully resolved).
    Expected CY ≈ 1 - C(T) because denominator ≈ 1.
    Returns (id_a, id_b).
    """
    id_a = db.save(
        content="feature X is always available",
        category="context",
        project="proj",
        tags=["feature"],
        confidence=0.8,
    )
    id_b = db.save(
        content="feature X is never available",
        category="context",
        project="proj",
        tags=["feature"],
        confidence=0.8,
    )
    # Mark the auto-detected contradiction as resolved
    db.conn.execute(
        "UPDATE contradictions SET resolution = 'a-supersedes-b' WHERE 1=1"
    )
    db.conn.commit()
    return id_a, id_b


def _build_one_contradiction_unresolved(db: MemoryDB) -> tuple[str, str]:
    """
    One contradiction pair, resolution = 'unresolved' (default).
    Δ_drift = 1.0; full penalty applies.
    """
    id_a = db.save(
        content="feature Y is always enabled",
        category="context",
        project="proj2",
        tags=["featurey"],
        confidence=0.8,
    )
    id_b = db.save(
        content="feature Y is never enabled",
        category="context",
        project="proj2",
        tags=["featurey"],
        confidence=0.8,
    )
    return id_a, id_b


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestZeroContradictions(unittest.TestCase):
    """Fixture with 5 non-contradicting memories → CY = 1.0 (within float tol)."""

    def test_zero_contradictions(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = _db(tmp)
            try:
                _build_zero_contradiction_corpus(db)
                result = coherence_yield(db, window_days=_WINDOW, now=_NOW)
            finally:
                db.close()

        self.assertAlmostEqual(result["cy"], 1.0, places=6,
                               msg=f"Expected CY=1.0 with no contradictions, got {result}")
        self.assertEqual(result["c"], 0.0, msg="Contradiction rate must be 0")
        self.assertEqual(result["delta_drift"], 0.0)
        self.assertIn("ci_95", result)
        self.assertIn("window", result)
        self.assertIn("n_pairs", result)


class TestOneContradictionResolved(unittest.TestCase):
    """1 contradiction marked resolved → Δ_drift=0, CY ≈ 1 - C(T)."""

    def test_resolved_contradiction(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = _db(tmp)
            try:
                _build_one_contradiction_resolved(db)
                result = coherence_yield(db, window_days=_WINDOW, now=_NOW)
            finally:
                db.close()

        # Δ_drift = 0 → denominator = 1 → CY = 1 - C
        self.assertAlmostEqual(result["delta_drift"], 0.0, places=6,
                               msg="Resolved contradiction must have Δ_drift=0")
        # CY must equal 1 - C when drift is 0
        expected_cy = 1.0 - result["c"]
        self.assertAlmostEqual(result["cy"], expected_cy, places=6,
                               msg=f"CY must equal 1-C when Δ_drift=0; got {result}")
        # Must actually have detected a contradiction (c > 0)
        self.assertGreater(result["c"], 0.0,
                           msg="There IS a contradiction — C must be > 0")


class TestOneContradictionUnresolved(unittest.TestCase):
    """1 unresolved contradiction → Δ_drift=1, full penalty in denominator."""

    def test_unresolved_contradiction(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = _db(tmp)
            try:
                _build_one_contradiction_unresolved(db)
                result = coherence_yield(db, window_days=_WINDOW, now=_NOW)
            finally:
                db.close()

        self.assertAlmostEqual(result["delta_drift"], 1.0, places=6,
                               msg="Single unresolved contradiction → Δ_drift=1")
        # CY < 1-C because denominator > 1
        expected_max_cy = 1.0 - result["c"]
        self.assertLess(result["cy"], expected_max_cy + 1e-9,
                        msg="Unresolved drift must reduce CY below 1-C")
        # Verify formula: CY = (1-C) / (1 + λ*1*(1 - R_conf))
        lam = 2.0
        expected = (1 - result["c"]) / (1 + lam * 1.0 * (1 - result["r_conf"]))
        self.assertAlmostEqual(result["cy"], expected, places=6)


class TestGameabilityEmptyTable(unittest.TestCase):
    """F3 fix: harness calls _detect_contradictions directly, not table-read.

    Even with the contradictions table cleared, the harness must still detect
    contradictions by calling _detect_contradictions() on the corpus.
    """

    def test_detects_contradictions_with_empty_table(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = _db(tmp)
            try:
                # Save contradicting memories (auto-detection fires and writes table)
                db.save(
                    content="feature Z is always on",
                    category="context",
                    project="proj3",
                    tags=["featurez"],
                    confidence=0.8,
                )
                db.save(
                    content="feature Z is never on",
                    category="context",
                    project="proj3",
                    tags=["featurez"],
                    confidence=0.8,
                )
                # WIPE the contradictions table — simulating the gaming attack
                db.conn.execute("DELETE FROM contradictions")
                db.conn.commit()

                # Verify table is empty
                n_in_table = db.conn.execute(
                    "SELECT COUNT(*) FROM contradictions"
                ).fetchone()[0]
                self.assertEqual(n_in_table, 0, "Table must be wiped before measuring")

                result = coherence_yield(db, window_days=_WINDOW, now=_NOW)
            finally:
                db.close()

        # Harness must have found the contradiction via direct _detect_contradictions call
        self.assertGreater(result["c"], 0.0,
                           msg="F3: harness must detect contradictions even when table is empty; "
                               f"got c={result['c']}")


class TestDeterministic(unittest.TestCase):
    """F6 fix: same `now` parameter → identical output across two runs."""

    def test_deterministic_with_fixed_now(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = _db(tmp)
            try:
                _build_one_contradiction_unresolved(db)
                result_1 = coherence_yield(db, window_days=_WINDOW, now=_NOW)
                result_2 = coherence_yield(db, window_days=_WINDOW, now=_NOW)
            finally:
                db.close()

        self.assertEqual(result_1["cy"], result_2["cy"],
                         "F6: identical now → identical CY")
        self.assertEqual(result_1["c"], result_2["c"])
        self.assertEqual(result_1["delta_drift"], result_2["delta_drift"])
        self.assertEqual(result_1["window"], result_2["window"])


class TestConfidenceInflationPenalty(unittest.TestCase):
    """High R_conf with active unresolved contradictions still produces penalty.

    Confidence inflation (R_conf → 1.0) alone must not make CY → 1.0
    when there are real unresolved contradictions.
    """

    def test_high_confidence_does_not_cancel_drift_penalty_completely(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = _db(tmp)
            try:
                # Save contradicting pair with confidence=1.0 (inflation attack)
                db.save(
                    content="service A is always running",
                    category="context",
                    project="proj4",
                    tags=["service"],
                    confidence=1.0,
                )
                db.save(
                    content="service A is never running",
                    category="context",
                    project="proj4",
                    tags=["service"],
                    confidence=1.0,
                )
                result = coherence_yield(db, window_days=_WINDOW, lambda_drift=2.0, now=_NOW)
            finally:
                db.close()

        # When R_conf=1.0, denominator = 1 + λ*Δ_drift*(1-1.0) = 1 + 0 = 1
        # So CY = 1 - C(T), which is < 1.0 when there IS a contradiction
        # The contradiction IS penalized through C(T) even if drift term vanishes
        self.assertLess(result["cy"], 1.0,
                        msg="Contradiction must reduce CY even when confidence=1.0 via C(T)")
        # Verify: contradiction is still detected (the C term carries the penalty)
        self.assertGreater(result["c"], 0.0,
                           msg="Contradiction must be detected even with inflated confidence")


class TestReturnStructure(unittest.TestCase):
    """coherence_yield must return all required keys per the public API contract."""

    def test_return_keys(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = _db(tmp)
            try:
                _build_zero_contradiction_corpus(db)
                result = coherence_yield(db, window_days=_WINDOW, now=_NOW)
            finally:
                db.close()

        required_keys = {"cy", "c", "delta_drift", "r_conf", "n_pairs", "ci_95", "window"}
        self.assertTrue(required_keys.issubset(result.keys()),
                        f"Missing keys: {required_keys - result.keys()}")
        lo, hi = result["ci_95"]
        self.assertLessEqual(lo, result["cy"])
        self.assertLessEqual(result["cy"], hi + 1e-9)
        w_start, w_end = result["window"]
        self.assertIsInstance(w_start, datetime)
        self.assertIsInstance(w_end, datetime)


if __name__ == "__main__":
    unittest.main()
