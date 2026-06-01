"""Tests for the inter-rater agreement scorer (Cohen's kappa).

The methodology bar (Anthropic 'Demystifying evals'): a good eval task is one where
two independent raters reach the same verdict. We measure that with Cohen's kappa,
which corrects for chance agreement (raw % does not). Only the math is unit-tested;
the live two-model rating is exercised by the runner (needs endpoints).
"""
from __future__ import annotations

import sys
from pathlib import Path

WORKTREE = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(WORKTREE / "eval"))

import unittest
from interrater import cohen_kappa, agreement_stats  # noqa: E402


class TestCohenKappa(unittest.TestCase):
    def test_perfect_agreement_is_one(self):
        a = [True, True, False, False, True]
        b = [True, True, False, False, True]
        self.assertAlmostEqual(cohen_kappa(a, b), 1.0)

    def test_systematic_disagreement_is_negative(self):
        # Both raters use both classes (variance exists) but disagree more than
        # chance -> genuinely negative kappa. (All-yes vs all-no has no variance,
        # so pe=1 and kappa is 0/undefined — that's correct, not negative.)
        a = [True, False, True, False]
        b = [False, True, False, True]
        self.assertLess(cohen_kappa(a, b), 0.0)

    def test_chance_level_is_near_zero(self):
        # raters independent + balanced -> kappa ~ 0 even with ~50% raw agreement
        a = [True, False, True, False, True, False, True, False]
        b = [True, True, False, False, True, True, False, False]
        k = cohen_kappa(a, b)
        self.assertLess(abs(k), 0.5)  # near chance, not high

    def test_known_value(self):
        # 2x2: both-yes=20, both-no=15, a-yes-b-no=5, a-no-b-yes=10  (n=50)
        # po=(20+15)/50=0.70; pa_yes=25/50*30/50=0.30; pa_no=25/50*20/50=0.20; pe=0.50
        # kappa=(0.70-0.50)/(1-0.50)=0.40
        a = [True]*20 + [True]*5 + [False]*10 + [False]*15
        b = [True]*20 + [False]*5 + [True]*10 + [False]*15
        self.assertAlmostEqual(cohen_kappa(a, b), 0.40, places=2)

    def test_empty_safe(self):
        self.assertEqual(cohen_kappa([], []), 0.0)

    def test_single_class_no_variance(self):
        # both raters say True on everything -> perfect raw agreement; kappa
        # undefined (pe=1) -> convention: return 1.0 when po==1, else 0.0
        self.assertEqual(cohen_kappa([True, True], [True, True]), 1.0)


class TestAgreementStats(unittest.TestCase):
    def test_stats_shape_and_counts(self):
        a = [True, True, False, False]
        b = [True, False, False, False]
        s = agreement_stats(a, b)
        self.assertEqual(s["n"], 4)
        self.assertAlmostEqual(s["raw_agreement"], 0.75)  # 3/4
        self.assertEqual(s["both_yes"], 1)
        self.assertEqual(s["both_no"], 2)
        self.assertEqual(s["disagree"], 1)
        self.assertIn("kappa", s)

    def test_abstains_excluded(self):
        # None (abstain) from either rater drops the pair from the agreement calc,
        # and is counted separately — never guessed into agree/disagree.
        a = [True, None, False, True]
        b = [True, False, None, True]
        s = agreement_stats(a, b)
        self.assertEqual(s["n"], 2)          # only the 2 fully-rated pairs
        self.assertEqual(s["n_abstain"], 2)  # the 2 with a None


if __name__ == "__main__":
    unittest.main()
