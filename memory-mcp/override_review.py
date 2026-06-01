#!/usr/bin/env python3
"""override_review.py — the human override surface for the commitment gate.

The gate is honest because **only a human softens a commitment**. A gate-block
NEVER lowers a commitment's confidence (that would let an agent defeat the gate by
persistence — retry until it drops under the floor). This CLI is the human's
surface for the only legitimate confidence-lowering path:

  1. `list`     — review what the gate flagged (gate-blocks recorded in
                  feedback_violations), grouped by commitment with block counts.
  2. `override` — deliberately lower ONE commitment's confidence via
                  coherence_feedback.apply_override_decay (reason required).

This closes the demo's second half: *the gate holds under persistence; only a
human, here, softens it.*

    python override_review.py list   [--db PATH]
    python override_review.py override --id <commitment_id> --reason "..." \
                                       [--decay 0.1] [--min 0.5] [--db PATH]

Honesty rail: a read+human-write surface over records. `list` asserts nothing about
truth — it reports which commitments the gate flagged and how often.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


def review(db) -> list[dict]:
    """Commitments the gate has flagged, with block counts. Read-only.

    Joins feedback_violations (where record_block writes feedback_memory_id =
    the contradicted commitment's id) back to the commitment memory.
    Returns [{id, content, confidence, n_blocks, last_detected}], most-blocked first.
    """
    rows = db.conn.execute(
        """SELECT m.id, m.content, m.confidence,
                  COUNT(v.id) AS n_blocks, MAX(v.detected_at) AS last_detected
           FROM feedback_violations v
           JOIN memories m ON m.id = v.feedback_memory_id
           GROUP BY m.id, m.content, m.confidence
           ORDER BY n_blocks DESC, last_detected DESC"""
    ).fetchall()
    return [
        {"id": r[0], "content": r[1], "confidence": r[2],
         "n_blocks": r[3], "last_detected": r[4]}
        for r in rows
    ]


def apply_override(db, commitment_id: str, *, decay: float = 0.1,
                   min_confidence: float = 0.5, reason: str) -> float:
    """Lower a commitment's confidence — the ONLY such path, human-gated.

    Thin seam over coherence_feedback.apply_override_decay, lazy-imported so this
    CLI loads and `list` works even while that module is still in-flight.
    """
    from coherence_feedback import apply_override_decay  # lazy: in-flight dependency
    return apply_override_decay(
        db, commitment_id, decay=decay, min_confidence=min_confidence, reason=reason)


def _db_path(arg: str | None = None) -> str:
    return arg or os.environ.get("MEMORY_DB") or str(
        Path.home() / ".claude" / "memory" / "memory.db")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="override_review", description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)

    pl = sub.add_parser("list", help="review commitments the gate has flagged")
    pl.add_argument("--db")

    po = sub.add_parser("override", help="human-soften one commitment (reason required)")
    po.add_argument("--id", required=True)
    po.add_argument("--reason", required=True)
    po.add_argument("--decay", type=float, default=0.1)
    po.add_argument("--min", dest="min_confidence", type=float, default=0.5)
    po.add_argument("--db")

    args = ap.parse_args(argv)

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from db import MemoryDB
    db = MemoryDB(_db_path(args.db))
    try:
        if args.cmd == "list":
            rows = review(db)
            if not rows:
                print("No gate blocks recorded.")
                return 0
            for r in rows:
                conf = r["confidence"] if r["confidence"] is not None else 0.75
                print(f"{r['id']}  conf={conf:.2f}  blocks={r['n_blocks']}  "
                      f"last={r['last_detected']}")
                print(f"    {r['content']}")
            return 0

        if args.cmd == "override":
            try:
                new = apply_override(
                    db, args.id, decay=args.decay,
                    min_confidence=args.min_confidence, reason=args.reason)
            except ValueError as e:
                sys.stderr.write(f"refused: {e}\n")
                return 2
            print(f"{args.id}: confidence -> {new:.2f}  (reason: {args.reason})")
            return 0
    finally:
        db.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
