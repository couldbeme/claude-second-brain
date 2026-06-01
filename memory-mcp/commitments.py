#!/usr/bin/env python3
"""commitments.py — Phase 0: commitment provenance for the action-gate.

The single source of truth for *what the gate enforces*. The PreToolUse gate, the
human override-review CLI, and the scheduled block-digest must all read commitments
from HERE so the three can't drift apart.

A "commitment" is an operator **rule/pattern memory** in the live store, confidence-
scored. This is the structured, already-existing provenance (convention confirmed at
feedback_violations.py:108-112, category IN ('rule','pattern')). Extracting natural-
language commitments from CLAUDE.md is a separate problem (needs an extraction step,
the ContextCov axis) and is deliberately deferred — the loop's fuel is the structured
rule/pattern memory, not free text.

Honesty rail: this is a read over the record store — it reports which commitments
exist, with what confidence. It does not assert any of them is true or safe.
"""
from __future__ import annotations

import json

# Commitments live under these memory categories (feedback_violations.py:108-112).
COMMITMENT_CATEGORIES: tuple[str, ...] = ("rule", "pattern")


def load_commitments(db, *, project=None, min_confidence: float = 0.0) -> list[dict]:
    """Active commitments the gate enforces. Read-only; never mutates the store.

    Args:
        db: a MemoryDB (uses its open `conn`).
        project: None → all projects; a string → only that project's commitments.
        min_confidence: drop commitments below this confidence (0.0 = keep all).

    Returns:
        [{id, content, confidence, tags, category}], confidence-descending.
        Empty list if the store holds no rule/pattern memories.
    """
    placeholders = ",".join("?" for _ in COMMITMENT_CATEGORIES)
    sql = (
        f"SELECT id, content, confidence, tags, category FROM memories "
        f"WHERE category IN ({placeholders})"
    )
    params: list = list(COMMITMENT_CATEGORIES)
    if project is not None:
        sql += " AND project = ?"
        params.append(project)
    sql += " ORDER BY confidence DESC"

    rows = db.conn.execute(sql, params).fetchall()
    out: list[dict] = []
    for (mid, content, conf, tags_json, category) in rows:
        c = conf if conf is not None else 0.75
        if c < min_confidence:
            continue
        try:
            tags = json.loads(tags_json) if tags_json else []
        except (ValueError, TypeError):
            tags = []
        out.append({
            "id": mid,
            "content": content,
            "confidence": c,
            "tags": tags,
            "category": category,
        })
    return out


def commitment_tags(commitments: list[dict]) -> list[str]:
    """Sorted distinct tags across `commitments` — the candidate tag set the gate
    uses to find which commitments an action could invert.

    Reproduces the inline `_commitment_tags` in commitment_gate_hook.py so the hook
    can adopt this single source with a one-line swap.
    """
    out: set = set()
    for c in commitments:
        for t in (c.get("tags") or []):
            out.add(t)
    return sorted(out)
