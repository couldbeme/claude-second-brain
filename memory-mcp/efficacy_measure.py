"""Coherence Yield (CY) — reference implementation.

Computes CY(T) = (1 - C(T)) / (1 + λ · Δ_drift(T) · (1 - R_conf(T)))

contradictions table DDL (db.py:98-108):
    CREATE TABLE IF NOT EXISTS contradictions (
        id TEXT PRIMARY KEY,
        memory_a_id TEXT NOT NULL,
        memory_b_id TEXT NOT NULL,
        detected_at TEXT DEFAULT (datetime('now')),
        resolution TEXT DEFAULT 'unresolved',
        FOREIGN KEY (memory_a_id) REFERENCES memories(id),
        FOREIGN KEY (memory_b_id) REFERENCES memories(id)
    )

F3 fix: harness calls db._detect_contradictions() directly on each memory
in the windowed corpus — bypasses the pre-stored contradictions table so the
"never run detector" gaming attack (empty table → CY=1.0) is defeated.

F6 fix: all time-dependent computation uses the injected `now` parameter.
          datetime.utcnow() / datetime.now() are NEVER called inside this module.

F4 fix: Wilson 95% CI on CY emitted alongside the scalar (stdlib only).
"""

from __future__ import annotations

import json
import math
from datetime import datetime, timedelta
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from db import MemoryDB


def _wilson_ci(p: float, n: int, z: float = 1.96) -> tuple[float, float]:
    """Wilson score interval for a proportion p with sample size n."""
    if n == 0:
        return (0.0, 1.0)
    centre = (p + z * z / (2 * n)) / (1 + z * z / n)
    margin = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return (max(0.0, centre - margin), min(1.0, centre + margin))


def coherence_yield(
    db: "MemoryDB",
    window_days: int = 30,
    lambda_drift: float = 2.0,
    now: Optional[datetime] = None,
) -> dict:
    """
    Compute Coherence Yield CY(T) = (1 - C(T)) / (1 + λ · Δ_drift(T) · (1 - R_conf(T)))

    F3 fix: contradictions are detected by calling db._detect_contradictions()
    directly on the windowed corpus — the pre-stored contradictions table is
    NOT used as the primary contradiction source, closing the gaming attack where
    a system suppresses the detector and scores CY=1.0 on an empty table.

    F6 fix: `now` is required for deterministic output. Defaults to
    datetime(2026, 1, 1) only in the absence of a caller-supplied value — pass
    `now` explicitly in all production calls.

    Returns: {
        "cy": float,                    # the score
        "c": float,                     # pairwise contradiction rate
        "delta_drift": float,           # unresolved-contradiction fraction
        "r_conf": float,                # mean write-time confidence
        "n_pairs": int,                 # denominator for diagnostics
        "ci_95": tuple[float, float],   # Wilson 95% CI on CY (F4 fix)
        "window": tuple[datetime, datetime],
    }
    """
    if now is None:
        now = datetime(2026, 1, 1, 0, 0, 0)

    cutoff: datetime = now - timedelta(days=window_days)
    cutoff_iso: str = cutoff.isoformat()

    # --- Fetch windowed memories ---
    rows = db.conn.execute(
        """SELECT id, content, project, tags, confidence
           FROM memories
           WHERE created_at >= ?""",
        (cutoff_iso,),
    ).fetchall()

    if not rows:
        r_conf = 0.75
        return {
            "cy": 1.0,
            "c": 0.0,
            "delta_drift": 0.0,
            "r_conf": r_conf,
            "n_pairs": 0,
            "ci_95": (1.0, 1.0),
            "window": (cutoff, now),
        }

    # --- R_conf(T): mean confidence in window ---
    confidences = [
        (row[4] if row[4] is not None else 0.75) for row in rows
    ]
    r_conf = sum(confidences) / len(confidences)

    # --- n_pairs: pairs sharing >=1 tag (denominator for C(T)) ---
    n_pairs = db.conn.execute(
        """
        SELECT COUNT(*) FROM (
            SELECT a.id, b.id FROM memories a, memories b
            WHERE a.id < b.id
              AND a.created_at >= ? AND b.created_at >= ?
              AND EXISTS (
                  SELECT 1 FROM json_each(a.tags) ja
                  JOIN json_each(b.tags) jb ON ja.value = jb.value
              )
        )
        """,
        (cutoff_iso, cutoff_iso),
    ).fetchone()[0]

    # --- F3 fix: live contradiction detection via _detect_contradictions() ---
    # Call the detector on each memory in the window; collect unique conflict pairs.
    # This defeats the gaming attack of emptying the contradictions table.
    live_pairs: set[frozenset[str]] = set()
    for (mem_id, content, project, tags_json, _conf) in rows:
        tags = json.loads(tags_json) if tags_json else []
        if not tags:
            continue
        conflict_ids = db._detect_contradictions(mem_id, content, project, tags)
        for cid in conflict_ids:
            live_pairs.add(frozenset((mem_id, cid)))

    n_live = len(live_pairs)

    # --- C(T): pairwise contradiction rate ---
    c_t = n_live / max(n_pairs, 1)
    c_t = min(c_t, 1.0)

    # --- Δ_drift(T): unresolved fraction ---
    # For live contradictions we check the contradictions table resolution column.
    # We count the live pairs as unresolved unless a table entry marks them resolved.
    if n_live == 0:
        delta_drift = 0.0
    else:
        n_unresolved = 0
        for pair in live_pairs:
            pair_list = list(pair)
            if len(pair_list) == 2:
                a_id, b_id = pair_list[0], pair_list[1]
            else:
                # frozenset with one element means self-contradiction (shouldn't happen)
                a_id = b_id = pair_list[0]
            row = db.conn.execute(
                """SELECT resolution FROM contradictions
                   WHERE (memory_a_id = ? AND memory_b_id = ?)
                      OR (memory_a_id = ? AND memory_b_id = ?)
                   LIMIT 1""",
                (a_id, b_id, b_id, a_id),
            ).fetchone()
            if row is None or row[0] == "unresolved":
                n_unresolved += 1
        delta_drift = n_unresolved / n_live

    # --- CY ---
    cy = (1.0 - c_t) / (1.0 + lambda_drift * delta_drift * (1.0 - r_conf))

    # --- F4 fix: Wilson 95% CI on CY ---
    # Treat CY as a proportion over n_pairs for CI purposes.
    ci_lo, ci_hi = _wilson_ci(cy, max(n_pairs, 1))

    return {
        "cy": cy,
        "c": c_t,
        "delta_drift": delta_drift,
        "r_conf": r_conf,
        "n_pairs": n_pairs,
        "ci_95": (ci_lo, ci_hi),
        "window": (cutoff, now),
    }
