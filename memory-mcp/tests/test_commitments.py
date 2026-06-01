#!/usr/bin/env python3
"""TDD for commitments.py — Phase 0, commitment provenance (RED: module absent).

The gate has no fuel unless we define where its commitments come from. This
module is the single source of truth: a "commitment" is an operator rule/pattern
memory in the live store, confidence-scored. Convention confirmed at
feedback_violations.py:108-112 (category IN ('rule','pattern')).

The gate, the override-review CLI, and the block digest must all read commitments
from HERE so the three can't drift apart. `commitment_tags` reproduces the inline
`_commitment_tags` in commitment_gate_hook.py so adoption is a trivial later swap.
"""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPTS_DIR))

from db import MemoryDB  # noqa: E402
from commitments import load_commitments, commitment_tags  # noqa: E402  (RED: absent)


def _db(tmp: str) -> MemoryDB:
    return MemoryDB(str(Path(tmp) / "m.db"))


class TestLoadCommitments(unittest.TestCase):

    def test_loads_rule_and_pattern_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = _db(tmp)
            try:
                db.save(content="Never force-push to main.", category="rule", tags=["git"])
                db.save(content="Prefer Ruff for linting.", category="pattern", tags=["python"])
                db.save(content="The dashboard defaults to dark theme.", category="context", tags=["ci"])
                got = load_commitments(db)
            finally:
                db.close()
            cats = sorted(c["category"] for c in got)
            self.assertEqual(cats, ["pattern", "rule"])  # context excluded

    def test_each_commitment_carries_gate_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = _db(tmp)
            try:
                db.save(content="Never deploy on Friday.", category="rule",
                        tags=["deploy", "prod"], confidence=0.9)
                (c,) = load_commitments(db)
            finally:
                db.close()
            self.assertEqual(
                set(c.keys()), {"id", "content", "confidence", "tags", "category"})
            self.assertEqual(c["tags"], ["deploy", "prod"])  # parsed to list, not JSON str
            self.assertAlmostEqual(c["confidence"], 0.9)

    def test_min_confidence_filter(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = _db(tmp)
            try:
                db.save(content="Load-bearing rule.", category="rule", tags=["a"], confidence=0.9)
                db.save(content="Weak hunch.", category="rule", tags=["b"], confidence=0.5)
                strong = load_commitments(db, min_confidence=0.8)
            finally:
                db.close()
            self.assertEqual([c["confidence"] for c in strong], [0.9])

    def test_project_filter(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = _db(tmp)
            try:
                db.save(content="Repo-A rule.", category="rule", tags=["x"], project="A")
                db.save(content="Global rule.", category="rule", tags=["x"])
                only_a = load_commitments(db, project="A")
            finally:
                db.close()
            self.assertEqual([c["content"] for c in only_a], ["Repo-A rule."])

    def test_empty_store_returns_empty_list(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = _db(tmp)
            try:
                self.assertEqual(load_commitments(db), [])
            finally:
                db.close()


class TestCommitmentTags(unittest.TestCase):

    def test_sorted_distinct_tags_across_commitments(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = _db(tmp)
            try:
                db.save(content="r1", category="rule", tags=["git", "deploy"])
                db.save(content="r2", category="pattern", tags=["deploy", "python"])
                tags = commitment_tags(load_commitments(db))
            finally:
                db.close()
            self.assertEqual(tags, ["deploy", "git", "python"])  # sorted, deduped

    def test_empty_commitments_yield_no_tags(self):
        self.assertEqual(commitment_tags([]), [])


if __name__ == "__main__":
    unittest.main()
