#!/usr/bin/env python3
"""drift_eval — measure the commitment-drift instrument on a hard, labeled set.

Publishes the HONEST numbers: precision, recall, false-positive rate, plus the
breakdown by difficulty (literal / paraphrase / trap / clean). The paraphrase
RECALL and the trap FALSE-POSITIVE rate are the load-bearing signals — they are
where a token-level matcher is designed to fail, so they are NOT gameable by the
author and are the honest measure of v0.1's real reach.

Run:  ~/.claude/memory-mcp/.venv/bin/python3 eval/drift_eval.py
"""
from __future__ import annotations

import os
import sys
from collections import defaultdict

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_HERE, "..", "memory-mcp"))
sys.path.insert(0, _HERE)

from commitment_drift import parse_commitment, check_action  # noqa: E402
from drift_cases import CASES  # noqa: E402


def tally(pairs: list) -> dict:
    """pairs: list of (label_is_drift: bool, predicted_drift: bool) -> metrics."""
    tp = sum(1 for lab, pred in pairs if lab and pred)
    fp = sum(1 for lab, pred in pairs if not lab and pred)
    tn = sum(1 for lab, pred in pairs if not lab and not pred)
    fn = sum(1 for lab, pred in pairs if lab and not pred)
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    fpr = fp / (fp + tn) if (fp + tn) else 0.0
    return {"tp": tp, "fp": fp, "tn": tn, "fn": fn,
            "precision": precision, "recall": recall, "fpr": fpr}


def evaluate(cases: list, predict=None) -> dict:
    """predict(action_text, commitments) -> report-with-.drifted. Defaults to the
    structural v0.1 check_action; pass an alias/embedding judge to compare."""
    predict = predict or check_action
    pairs, by_diff, misses, false_positives = [], defaultdict(list), [], []
    for c in cases:
        commitments = [parse_commitment(t) for t in c["commitments"]]
        report = predict(c["action"], commitments)
        label_is_drift = (c["label"] == "drift")
        predicted = report.drifted
        pairs.append((label_is_drift, predicted))
        by_diff[c["difficulty"]].append((label_is_drift, predicted))
        if label_is_drift and not predicted:
            misses.append(c)
        if (not label_is_drift) and predicted:
            false_positives.append(c)
    return {"overall": tally(pairs),
            "by_difficulty": {d: tally(p) for d, p in by_diff.items()},
            "misses": misses, "false_positives": false_positives, "n": len(cases)}


def main() -> int:
    r = evaluate(CASES)
    o = r["overall"]
    print(f"\nCommitment-drift instrument v0.1 — eval on {r['n']} hard cases\n")
    print(f"  precision {o['precision']:.0%}   recall {o['recall']:.0%}   "
          f"false-positive-rate {o['fpr']:.0%}")
    print(f"  (tp={o['tp']} fp={o['fp']} tn={o['tn']} fn={o['fn']})\n")
    print("  by difficulty (recall on drift cases / FPR on clean cases):")
    for d in ("literal", "paraphrase", "trap", "clean"):
        if d not in r["by_difficulty"]:
            continue
        m = r["by_difficulty"][d]
        drift_n = m["tp"] + m["fn"]
        if drift_n:
            print(f"    {d:11s} recall {m['recall']:.0%}  ({m['tp']}/{drift_n} caught)")
        else:
            print(f"    {d:11s} FPR    {m['fpr']:.0%}  ({m['fp']}/{m['fp']+m['tn']} false alarms)")
    if r["misses"]:
        print(f"\n  MISSES ({len(r['misses'])}) — honest false-negatives, the v0.2-semantic target:")
        for c in r["misses"]:
            print(f"    ✗ [{c['difficulty']}] {c['action']!r}  vs  {c['commitments'][0]!r}")
    if r["false_positives"]:
        print(f"\n  FALSE POSITIVES ({len(r['false_positives'])}) — token-overlap traps it wrongly flagged:")
        for c in r["false_positives"]:
            print(f"    ! {c['action']!r}  flagged against  {c['commitments'][0]!r}")
    print("\n  Read this honestly: high literal-recall is expected and weak evidence (author wrote both).")
    print("  The real signal is paraphrase-recall (≈the semantic gap) and trap-FPR (≈the precision cost).")
    print("  v0.2 (semantic) must beat THESE numbers on this same set to justify itself.\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
