"""Tests for the drift eval scorer — so the published numbers are trustworthy.

TDD-first: the metric math (tally) is tested independently of the dataset, so
precision/recall/false-positive-rate can't be quietly wrong.
"""

from __future__ import annotations

import sys
from pathlib import Path

WORKTREE = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(WORKTREE / "eval"))

import unittest
from drift_eval import tally  # noqa: E402


class TestTally(unittest.TestCase):
    def test_confusion_and_metrics(self):
        # (label_is_drift, predicted_drift)
        pairs = [
            (True, True),    # TP
            (True, False),   # FN (a miss)
            (False, True),   # FP
            (False, False),  # TN
            (True, True),    # TP
        ]
        m = tally(pairs)
        self.assertEqual(m["tp"], 2)
        self.assertEqual(m["fn"], 1)
        self.assertEqual(m["fp"], 1)
        self.assertEqual(m["tn"], 1)
        self.assertAlmostEqual(m["precision"], 2 / 3)   # tp/(tp+fp)
        self.assertAlmostEqual(m["recall"], 2 / 3)      # tp/(tp+fn)
        self.assertAlmostEqual(m["fpr"], 1 / 2)         # fp/(fp+tn)

    def test_empty_is_safe(self):
        m = tally([])
        self.assertEqual((m["tp"], m["fp"], m["tn"], m["fn"]), (0, 0, 0, 0))
        self.assertEqual(m["precision"], 0.0)
        self.assertEqual(m["recall"], 0.0)
        self.assertEqual(m["fpr"], 0.0)

    def test_no_positives_predicted_zero_precision_not_crash(self):
        m = tally([(False, False), (True, False)])  # nothing predicted positive
        self.assertEqual(m["precision"], 0.0)  # 0/0 guarded
        self.assertEqual(m["recall"], 0.0)


if __name__ == "__main__":
    unittest.main()
