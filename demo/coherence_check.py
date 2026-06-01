#!/usr/bin/env python3
"""coherence_check — the Choir hero demo. Run a Coherence Yield (CY) check over an
agent's stored beliefs, surface the contradictions, watch the number recover when
they're resolved.

WHAT THIS IS (read first — Weizenbaum lens, /tribunal 2026-05-31):
    This is a DIAGNOSTIC over a record store. It finds pairs of stored statements
    that invert each other (always/never, enabled/disabled, required/optional, ...).
    It does NOT make an assistant "know what it believes," "be coherent," or "be safe
    to act autonomously." CY is a number about records, not a property of an agent.

WHY IT MATTERS:
    Agent memory layers (openclaw's, Mem0, Pieces, csb's own) all STORE beliefs.
    None CHECK whether the stored beliefs contradict each other. An assistant that
    has learned both "standup is always 9am" and "standup is never at 9am anymore"
    will act on whichever it retrieves. CY is the missing coherence check.

This runs the REAL csb code (memory-mcp/db.py + efficacy_measure.py) — not a
reimplementation. The fixture below is a SEEDED stand-in for a real memory export:
the contradictions are planted so the output is reproducible (N=3, CY≈0.36). Point
`load_beliefs()` at a real openclaw/Mem0/csb export to find real ones — same code path.

Usage:  ~/.claude/memory-mcp/.venv/bin/python3 demo/coherence_check.py
"""
from __future__ import annotations

import json
import os
import re
import sys
import tempfile
from datetime import datetime
from pathlib import Path

# Import the real csb substrate (no reimplementation).
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_HERE, "..", "memory-mcp"))
from db import MemoryDB                       # noqa: E402
from efficacy_measure import coherence_yield  # noqa: E402

# Fixed clock so CY is deterministic regardless of when you run it.
NOW = datetime(2026, 6, 1, 0, 0, 0)
WINDOW_DAYS = 3650  # wide window: every fixture belief is in-scope

# A seeded stand-in for a real assistant memory export. Each belief is
# (id, content, tags, confidence). Three pairs invert each other on a shared tag.
BELIEFS = [
    ("b1", "Standup is always at 9am for the user.",            ["standup", "schedule"], 0.80),
    ("b2", "The user said standup is never at 9am anymore.",    ["standup", "schedule"], 0.70),
    ("b3", "Slack deploy notifications are enabled for prod.",  ["slack", "notifications"], 0.90),
    ("b4", "Deploy notifications are disabled to cut noise.",   ["slack", "notifications"], 0.60),
    ("b5", "The staging API key is required for deploys.",      ["deploy", "config"], 0.85),
    ("b6", "The staging API key is optional now we use OIDC.",  ["deploy", "config"], 0.80),
    ("b7", "User prefers responses in Hebrew.",                 ["prefs"], 0.90),
    ("b8", "User timezone is Asia/Jerusalem.",                  ["prefs", "schedule"], 0.95),
]
STALE_SIDE = ["b1", "b3", "b5"]  # the beliefs a correction would retire


def load_beliefs(source: str | None = None):
    """Return [(id, content, tags, confidence)].

    No source  -> the seeded fixture (deterministic demo).
    *.json     -> a memory export: list of {content, tags?, confidence?, id?}.
    directory/ -> one belief per *.md (optional `tags:`/`confidence:` frontmatter; body = content).

    The JSON/markdown shapes are the common denominator of openclaw / Mem0 / csb
    exports — point this at a real one to find real contradictions, same code path."""
    if source is None:
        return BELIEFS
    p = Path(source)
    if p.is_dir():
        return _load_markdown_dir(p)
    if p.suffix == ".json":
        return _load_json(p)
    raise SystemExit(f"unsupported source: {source!r} (give a .json file or a directory of .md)")


def _coerce(idx, raw_id, content, tags, conf):
    return (
        str(raw_id) if raw_id else f"m{idx}",
        str(content or "").strip(),
        [str(t) for t in (tags or [])],
        float(conf) if conf is not None else 0.75,
    )


def _load_json(path: Path):
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict):  # tolerate {"memories":[...]} or {"items":[...]}
        data = data.get("memories") or data.get("items") or data.get("beliefs") or []
    out = []
    for i, item in enumerate(data):
        if isinstance(item, str):
            out.append(_coerce(i, None, item, [], None))
        else:
            out.append(_coerce(i, item.get("id"), item.get("content") or item.get("text"),
                               item.get("tags"), item.get("confidence")))
    return [b for b in out if b[1]]


_FM = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)


def _load_markdown_dir(d: Path):
    out = []
    for i, md in enumerate(sorted(d.glob("*.md"))):
        text = md.read_text(encoding="utf-8")
        tags, conf = [], None
        m = _FM.match(text)
        if m:
            for line in m.group(1).splitlines():
                if line.startswith("tags:"):
                    tags = re.findall(r"[\w\-/]+", line.split(":", 1)[1])
                elif line.startswith("confidence:"):
                    try:
                        conf = float(line.split(":", 1)[1].strip())
                    except ValueError:
                        pass
            text = text[m.end():]
        out.append(_coerce(i, md.stem, " ".join(text.split()), tags, conf))
    return [b for b in out if b[1]]


def _seed(db: MemoryDB, beliefs) -> None:
    for mem_id, content, tags, conf in beliefs:
        db.save(content=content, category="fact", tags=tags,
                project="demo", confidence=conf, mem_id=mem_id)


def _list_contradictions(db: MemoryDB):
    """Return the UNIQUE contradiction pairs [(content_a, content_b)].

    The detector writes a table row on every detection pass (save-time and CY-time,
    both directions), so the raw table double-counts. We dedupe by unordered pair to
    match the n_live count coherence_yield() uses for C(T) — the displayed N must
    equal C × n_pairs, or the number isn't trustworthy."""
    rows = db.conn.execute(
        """SELECT ma.content, mb.content
           FROM contradictions c
           JOIN memories ma ON ma.id = c.memory_a_id
           JOIN memories mb ON mb.id = c.memory_b_id"""
    ).fetchall()
    seen, unique = set(), []
    for a, b in rows:
        key = frozenset((a, b))
        if key not in seen:
            seen.add(key)
            unique.append((a, b))
    return unique


def _report(label: str, cy: dict, pairs) -> None:
    lo, hi = cy["ci_95"]
    print(f"\n{label}")
    print(f"  beliefs scanned   : tag-sharing pairs = {cy['n_pairs']}")
    print(f"  contradictions    : {len(pairs)}")
    for a, b in pairs:
        print(f"      ✗  “{a}”\n         ⟂  “{b}”")
    bar = "█" * round(cy["cy"] * 20)
    print(f"  Coherence Yield   : {cy['cy']:.2f}  [{bar:<20}]  (95% CI {lo:.2f}–{hi:.2f})")
    print(f"      C={cy['c']:.2f}  drift={cy['delta_drift']:.2f}  mean-confidence={cy['r_conf']:.2f}")


def main() -> int:
    source = sys.argv[1] if len(sys.argv) > 1 else None
    beliefs = load_beliefs(source)
    tmp = tempfile.mkdtemp(prefix="cy_demo_")
    db = MemoryDB(os.path.join(tmp, "demo.db"))
    try:
        _seed(db, beliefs)

        if source is None:
            # DEMO (seeded fixture): the two-beat drop-and-recover arc.
            cy1 = coherence_yield(db, window_days=WINDOW_DAYS, now=NOW)
            _report("① BEFORE — the agent's stored beliefs:", cy1, _list_contradictions(db))
            if os.environ.get("CY_DEMO_PACE"):  # GIF pacing only — no effect on the numbers
                import time as _t; _t.sleep(float(os.environ["CY_DEMO_PACE"]))
            for sid in STALE_SIDE:  # the user corrects; retire the stale side of each pair
                db.conn.execute("DELETE FROM memories WHERE id = ?", (sid,))
            db.conn.execute("DELETE FROM contradictions")  # re-detected live on recompute
            db.conn.commit()
            cy2 = coherence_yield(db, window_days=WINDOW_DAYS, now=NOW)
            _report("② AFTER  — stale beliefs retired (the user corrected them):", cy2, _list_contradictions(db))
            print(f"\n→ CY recovered {cy1['cy']:.2f} → {cy2['cy']:.2f}. "
                  f"A diagnostic over records — not a claim that the agent 'knows' anything.\n")
        else:
            # REPORT (real export): one-shot coherence check on your data.
            cy = coherence_yield(db, window_days=WINDOW_DAYS, now=NOW)
            _report(f"Coherence report — {len(beliefs)} beliefs from {source}", cy,
                    _list_contradictions(db))
            n = len(_list_contradictions(db))
            print(f"\n→ {n} contradiction(s) found. CY is a diagnostic over records — "
                  f"resolve a pair by retiring the stale side, then re-run.\n")
        return 0
    finally:
        db.close()
        for f in os.listdir(tmp):
            os.remove(os.path.join(tmp, f))
        os.rmdir(tmp)


if __name__ == "__main__":
    raise SystemExit(main())
