#!/usr/bin/env python3
"""cy_report — run a Coherence Yield check over an existing sqlite memory.db.

This is the on-demand "live" path: it points the (formerly dormant) CY primitive
at a real memory store and prints the score + the contradictions behind it.

NON-DESTRUCTIVE: coherence_yield() calls the contradiction detector, which INSERTS
rows into the `contradictions` table. So we copy the db to a temp file and score the
copy — the real store is never written. (Confirms: your live memory.db is untouched.)

It is a DIAGNOSTIC over a record store — not a claim the agent "knows" or "is safe."

Usage:
    ~/.claude/memory-mcp/.venv/bin/python3 tools/cy_report.py [db_path] [--window DAYS]
    default db_path = ~/.claude/memory/memory.db
"""
from __future__ import annotations

import os
import shutil
import sys
import tempfile
from datetime import datetime

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_HERE, "..", "memory-mcp"))
from db import MemoryDB                       # noqa: E402
from efficacy_measure import coherence_yield  # noqa: E402

DEFAULT_DB = os.path.expanduser("~/.claude/memory/memory.db")
NOW = datetime(2030, 1, 1)  # fixed, far-future → every record is in-window deterministically


def _parse_args(argv):
    db_path, window = DEFAULT_DB, 36500
    rest = argv[1:]
    i = 0
    while i < len(rest):
        if rest[i] == "--window":
            window = int(rest[i + 1]); i += 2
        else:
            db_path = rest[i]; i += 1
    return db_path, window


def main(argv) -> int:
    db_path, window = _parse_args(argv)
    if not os.path.exists(db_path):
        print(f"no memory.db at {db_path} — pass a path, or run from a machine that has one.")
        return 2

    tmpdir = tempfile.mkdtemp(prefix="cy_report_")
    copy = os.path.join(tmpdir, "memory.db")
    shutil.copy2(db_path, copy)  # non-destructive: score the copy, never the original
    db = MemoryDB(copy)
    try:
        n_mem = db.conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
        cy = coherence_yield(db, window_days=window, now=NOW)
        pairs = db.conn.execute(
            """SELECT DISTINCT ma.content, mb.content
               FROM contradictions c
               JOIN memories ma ON ma.id = c.memory_a_id
               JOIN memories mb ON mb.id = c.memory_b_id"""
        ).fetchall()
        # dedupe unordered pairs
        seen, uniq = set(), []
        for a, b in pairs:
            k = frozenset((a, b))
            if k not in seen:
                seen.add(k); uniq.append((a, b))

        lo, hi = cy["ci_95"]
        bar = "█" * round(cy["cy"] * 20)
        print(f"\nCoherence report — {db_path}")
        print(f"  memories          : {n_mem}  (tag-sharing pairs in window = {cy['n_pairs']})")
        print(f"  contradictions    : {len(uniq)}")
        for a, b in uniq[:20]:
            print(f"      ✗  “{a[:70]}”\n         ⟂  “{b[:70]}”")
        if len(uniq) > 20:
            print(f"      … and {len(uniq) - 20} more")
        print(f"  Coherence Yield   : {cy['cy']:.2f}  [{bar:<20}]  (95% CI {lo:.2f}–{hi:.2f})")
        print(f"      C={cy['c']:.2f}  drift={cy['delta_drift']:.2f}  mean-confidence={cy['r_conf']:.2f}")
        print(f"\n  (real store untouched — scored a temp copy. CY is a diagnostic over records.)\n")
        return 0
    finally:
        db.close()
        shutil.rmtree(tmpdir, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
