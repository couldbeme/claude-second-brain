"""coherence_feedback.py — the action-gate LEARN edge (Phase 1a, v2-corrected).

Two functions, deliberately split so a gate BLOCK can never erode the very
commitment it just enforced (the v1 decay-on-block vuln: retrying a blocked
action ~3x dropped the commitment under the 0.8 gate floor and let persistence
defeat the gate):

  record_block         fires on EVERY block. DIAGNOSTIC ONLY: writes a
                       feedback_violations row so CY-behavior moves. NEVER
                       touches confidence. Fail-OPEN. Deduped one row per
                       (commitment_id, session_id, action_hash).
  apply_override_decay the ONLY path that lowers a commitment's confidence.
                       Human-gated (a person judged a logged block a false
                       positive), OFF the hot path. Symmetric with the existing
                       human update() restore path.

Rails (do not regress):
  1. A block must NEVER lower confidence — it's the gate working, not evidence
     the commitment is wrong. (persistence test is the regression guard.)
  2. Lowering confidence is human-only (apply_override_decay, requires a reason).

Reuses, verified against live db.py (no new table/column):
  - feedback_violations.record_violation (feedback_violations.py:140)
  - db.update(...) confidence setter, clamps to [0,1] (db.py:456-458)
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from feedback_violations import record_violation

if TYPE_CHECKING:
    from db import MemoryDB


def record_block(
    db: "MemoryDB",
    blocking_contradiction: dict,
    *,
    session_id: Optional[str] = None,
    action_hash: Optional[str] = None,
) -> bool:
    """Record a gate block as a feedback_violations row. DIAGNOSTIC ONLY.

    NEVER mutates confidence. Deduped one row per (commitment_id, session_id,
    action_hash) — distinct sessions with the same action_hash are NOT
    duplicates. Fail-OPEN: any error (incl. a bc with no "id") returns False and
    never raises — the gate's block decision is already made and must be
    unaffected. Returns True iff a new row was written.
    """
    try:
        commitment_id = blocking_contradiction["id"]
    except (KeyError, TypeError):
        return False  # malformed contradiction -> fail-open, no row

    try:
        # feedback_violations has no action_hash column (and matched_pattern is
        # NOT NULL), so the action_hash is the dedup key carried in
        # matched_pattern; matched_text carries the event label.
        ah = action_hash if action_hash is not None else "unknown-action"

        already = db.conn.execute(
            """SELECT 1 FROM feedback_violations
               WHERE feedback_memory_id = ?
                 AND session_id IS ?
                 AND matched_pattern = ?
               LIMIT 1""",
            (commitment_id, session_id, ah),
        ).fetchone()
        if already is not None:
            return False  # this exact block already recorded; not a new row

        record_violation(
            db,
            feedback_memory_id=commitment_id,
            matched_text="gate-block",
            matched_pattern=ah,
            session_id=session_id,
        )
        return True
    except Exception:
        return False  # fail-open: diagnostics must never break the gate


def apply_override_decay(
    db: "MemoryDB",
    commitment_id: str,
    *,
    decay: float = 0.1,
    min_confidence: float = 0.5,
    reason: str,
) -> float:
    """Lower a commitment's confidence — the ONLY path that does so.

    Human-gated: called when a person reviews a logged block and judges the
    commitment a false positive. NOT on the hot path. Fixed linear step, clamped
    at min_confidence (never 0). Requires a non-empty `reason`; on an empty
    reason it raises ValueError and leaves confidence UNCHANGED. Returns the new
    confidence.
    """
    if not reason or not reason.strip():
        raise ValueError("apply_override_decay requires a non-empty reason")

    row = db.conn.execute(
        "SELECT confidence FROM memories WHERE id = ?", (commitment_id,)
    ).fetchone()
    if row is None:
        raise KeyError(f"no commitment with id {commitment_id!r}")
    old = row[0] if row[0] is not None else 0.75

    new = max(min_confidence, old - decay)
    db.update(commitment_id, confidence=new)
    return new
