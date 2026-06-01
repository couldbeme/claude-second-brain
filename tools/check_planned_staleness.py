#!/usr/bin/env python3
"""check_planned_staleness — fail if any [PLANNED:YYYY-MM-DD] marker is past its build-by date.

The honesty gate the /tribunal (2026-05-31) unanimously required: a `[PLANNED]` claim in a
tracked doc must carry a falsifiable deadline, or it rots into the same overstatement it replaced
(Cherny: "wire a grep-gate"; Kahneman: "planning fallacy"; Weizenbaum: "self-expiring or it re-becomes the lie").

Marker grammar (in any tracked .md):
    [PLANNED:2026-07-01]            # build-by date; past today => FAIL
    [PLANNED:2026-07-01 reason]     # optional trailing context, ignored by the parser

A bare `[PLANNED]` with no date is itself a violation — an undated plan cannot be falsified.

Usage:
    python3 tools/check_planned_staleness.py [paths...]      # default: CLAUDE.md.template docs/
Exit 0 = clean; exit 1 = at least one stale or undated marker (suitable for CI / pre-push).
This script is stdlib-only and deterministic — it is itself `[CODE]`, not a `[RULE]`.
"""
from __future__ import annotations

import datetime as _dt
import pathlib
import re
import sys

DATED = re.compile(r"\[PLANNED:(\d{4})-(\d{2})-(\d{2})")
BARE = re.compile(r"\[PLANNED\](?!:)|\[PLANNED:\s*[^\d]")  # [PLANNED] or [PLANNED: <non-date>]
CODESPAN = re.compile(r"`[^`]*`")  # inline-code: a token NAMED, not a claim ASSERTED
DEFAULT_TARGETS = ["CLAUDE.md.template", "docs"]


def _strip_codespans(line: str) -> str:
    """Blank out `inline code` so a label *discussed* (`[PLANNED]`) never trips the gate;
    only a marker *asserted* in plain prose ([PLANNED:date]) is a live claim."""
    return CODESPAN.sub("", line)


def _iter_md(paths: list[str]):
    for p in paths:
        path = pathlib.Path(p)
        if path.is_dir():
            yield from sorted(path.rglob("*.md"))
        elif path.suffix == ".md" or path.name.endswith(".template"):
            yield path


def main(argv: list[str]) -> int:
    targets = argv[1:] or DEFAULT_TARGETS
    today = _dt.date.today()
    stale: list[str] = []
    undated: list[str] = []

    for md in _iter_md(targets):
        try:
            lines = md.read_text(encoding="utf-8").splitlines()
        except OSError:
            continue
        for n, raw in enumerate(lines, 1):
            line = _strip_codespans(raw)
            for m in DATED.finditer(line):
                try:
                    due = _dt.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
                except ValueError:
                    undated.append(f"{md}:{n}  invalid date in marker")
                    continue
                if due < today:
                    stale.append(f"{md}:{n}  PLANNED due {due} is {(today - due).days}d overdue")
            if BARE.search(line):
                undated.append(f"{md}:{n}  bare/undated [PLANNED] — add a build-by date")

    if stale or undated:
        print("FAIL: [PLANNED] markers violate the honesty gate\n")
        for s in stale:
            print("  STALE   ", s)
        for u in undated:
            print("  UNDATED ", u)
        print(f"\n{len(stale)} stale, {len(undated)} undated. Build it, re-date it, or relabel honestly.")
        return 1

    print("OK: every [PLANNED] marker carries a future build-by date.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
