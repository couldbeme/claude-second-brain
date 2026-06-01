"""Tests for semantic_drift.py — the P1 judge layer (architecture + lexical judge).

TDD-first. Two things proven here:
  1. The alias normalizer maps known dev/ops surface forms to a canonical term
     (-f -> force, DROP -> delete, ship -> deploy, prod -> production, ...).
  2. check_action_aliased catches a paraphrase the structural v0.1 missed
     (git push -f ... == force-push) BUT still misses a genuinely-semantic case
     (DROP TABLE users vs "delete the production database") — proving aliases are
     a shallow lift, not real semantics. The honest limit is asserted, not hidden.
"""

from __future__ import annotations

import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPTS_DIR))

import unittest
from commitment_drift import parse_commitment  # noqa: E402
from semantic_drift import normalize_tokens, check_action_aliased  # noqa: E402


class TestNormalize(unittest.TestCase):
    def test_aliases_map_to_canonical(self):
        norm = normalize_tokens("git push -f origin HEAD:main")
        self.assertIn("force", norm)   # f -> force
        self.assertIn("push", norm)
        self.assertIn("main", norm)

    def test_domain_aliases(self):
        self.assertIn("delete", normalize_tokens("DROP TABLE users"))      # drop -> delete
        self.assertIn("deploy", normalize_tokens("ship v2 to prod"))        # ship -> deploy
        self.assertIn("production", normalize_tokens("ship v2 to prod"))    # prod -> production
        self.assertIn("secret", normalize_tokens("add credentials.json"))  # credentials -> secret


class TestAliasedCheck(unittest.TestCase):
    def test_catches_paraphrase_the_structural_check_missed(self):
        commitments = [parse_commitment("Never force-push to main.")]
        report = check_action_aliased("git push -f origin HEAD:main", commitments)
        self.assertTrue(report.drifted)  # v0.1 missed this; alias layer catches it

    def test_still_misses_genuinely_semantic_case(self):
        # "DROP TABLE users" IS deleting the production database, but no alias
        # bridges 'users' -> 'production database'. Aliases are shallow; real
        # semantics (embeddings/LLM) are needed. Assert the honest miss.
        commitments = [parse_commitment("Never delete the production database.")]
        report = check_action_aliased("DROP TABLE users", commitments)
        self.assertFalse(report.drifted)

    def test_no_false_positive_on_clean(self):
        commitments = [parse_commitment("Never force-push to main.")]
        report = check_action_aliased("git push origin main", commitments)
        self.assertFalse(report.drifted)  # normal push, no force/-f


if __name__ == "__main__":
    unittest.main()
