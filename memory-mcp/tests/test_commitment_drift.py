"""Tests for commitment_drift.py — the P0 reliability instrument.

TDD-first: written RED before commitment_drift.py exists.

WHAT THIS CHECKS (reliability, NOT security): does an agent's ACTION contradict a
commitment the agent itself stated earlier in the same task? ("never force-push
main" -> later force-pushes main). This is long-horizon commitment-drift — the
distinct failure from contradiction-between-two-stored-memories (coherence_gate).

Honesty rails enforced by these tests:
- v0.1 is STRUCTURAL (token-level): it catches literal/near-literal drift and
  MISSES paraphrases — and there is an explicit test asserting the miss, so the
  limitation is documented, not hidden.
- It keys on the OBSERVED action text, never on an agent-supplied self-label
  (Schneier fix: the gated party must not classify itself) — a test proves a
  benign self-declared 'intent' does NOT suppress a real violation.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPTS_DIR))

from commitment_drift import parse_commitment, check_action  # noqa: E402


class TestParseCommitment(unittest.TestCase):
    def test_extracts_prohibited_core_after_marker(self):
        c = parse_commitment("Never force-push to main.")
        # marker 'never' stripped; content core retained, stopwords dropped
        self.assertIn("force", c.terms)
        self.assertIn("push", c.terms)
        self.assertIn("main", c.terms)
        self.assertNotIn("never", c.terms)
        self.assertNotIn("to", c.terms)

    def test_non_constraint_text_has_no_terms(self):
        # A statement with no prohibition marker is not a commitment-constraint.
        c = parse_commitment("The weather is nice today.")
        self.assertEqual(c.terms, frozenset())


class TestCheckAction(unittest.TestCase):
    def test_catches_literal_drift(self):
        commitments = [parse_commitment("Never force-push to main.")]
        report = check_action("Running: git push --force main", commitments)
        self.assertTrue(report.drifted)
        self.assertEqual(len(report.violations), 1)
        self.assertIn("force", report.violations[0]["matched_terms"])
        self.assertIn("main", report.violations[0]["matched_terms"])

    def test_no_drift_when_action_unrelated(self):
        commitments = [parse_commitment("Never force-push to main.")]
        report = check_action("git status", commitments)
        self.assertFalse(report.drifted)
        self.assertEqual(report.violations, [])

    def test_read_only_commitment_caught(self):
        commitments = [parse_commitment("Stay read-only; do not write files.")]
        report = check_action("write file config.yaml", commitments)
        self.assertTrue(report.drifted)

    def test_honest_miss_on_paraphrase(self):
        # `-f` and `HEAD:main` are semantically a force-push to main, but the
        # token-level v0.1 shield has no 'force'/'push' tokens to match. It MUST
        # miss — and we assert the miss so the limitation is documented, not hidden.
        commitments = [parse_commitment("Never force-push to main.")]
        report = check_action("git push -f origin HEAD:main", commitments)
        self.assertFalse(report.drifted)  # documented v0.1 blind spot -> v0.2 semantic

    def test_multiple_commitments_only_violated_one_flagged(self):
        commitments = [
            parse_commitment("Never force-push to main."),
            parse_commitment("Always keep the API backward-compatible."),
        ]
        report = check_action("git push --force main", commitments)
        self.assertTrue(report.drifted)
        self.assertEqual(len(report.violations), 1)
        self.assertIn("force", report.violations[0]["matched_terms"])

    def test_ignores_agent_self_declared_intent(self):
        # Schneier fix at the unit level: the instrument keys on the OBSERVED
        # action text, never on an agent-supplied benign self-label. A real
        # violation must still fire even when the agent claims it's harmless.
        commitments = [parse_commitment("Never force-push to main.")]
        report = check_action(
            "git push --force main",
            commitments,
            declared_intent="routine sync, totally safe",  # untrusted hint, ignored for the decision
        )
        self.assertTrue(report.drifted)


if __name__ == "__main__":
    unittest.main()
