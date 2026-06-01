#!/usr/bin/env python3
"""metaprompt_demo — a LABELED example of what /metaprompt produces.

Honesty note: /metaprompt is a model-driven skill, so this is NOT a live model run
(unlike demo/coherence_check.py, which is a real deterministic script). The content
below is a REAL, verbatim transformation from docs/METAPROMPT-EXAMPLES.md (Example 1),
lightly wrapped/abridged for GIF width. It is marked as an example by construction —
no invented output.
"""
import os
import time


def pace() -> None:
    p = os.environ.get("MP_DEMO_PACE")  # GIF pacing only
    if p:
        time.sleep(float(p))


BEFORE = ("i need a recap on what's built, what's not built, what we're\n"
          "  doing next, and suggestions for the next steps")

AFTER = """---
description: End-of-session recap — what shipped, queued, next, sequencing.
             Reader re-orients in <60 seconds.
argument-hint: (operates on session state + checkpoint.md + git logs)
---
# Mission
  Tight one-screen recap. Three sections, each <=200 words:
  BUILT, NOT BUILT, NEXT.
# Phases
  1. scan: repos `git log --oneline -20`, checkpoint.md, TaskList, in-flight
  2. classify: Built=landed | Not Built=queued/declined | Next=priority->cost
  3. deliver in the exact format below
# Format
  ## Built          — [artifact, where it lives, why]
  ## Not built      — [item, reason]
  ## Next (ranked)  — [verb + artifact + estimate + dependency]
  Recommend:        [highest-leverage move + one-sentence rationale]
# Constraints
  <=600 words | group related | ONE consolidated recap"""


def main() -> None:
    print("/metaprompt — example transformation (real, from docs/METAPROMPT-EXAMPLES.md)\n")
    print("YOU TYPE — a ~15-word fuzzy ask:")
    print("  /metaprompt " + BEFORE + "\n")
    pace()
    print("  v  upskilling...\n")
    pace()
    print("YOU GET — a structured, phased, executable prompt:")
    for ln in AFTER.splitlines():
        print("  " + ln)
    print("\n  (abridged for width — full prompt + 4 more examples in "
          "docs/METAPROMPT-EXAMPLES.md)")


if __name__ == "__main__":
    main()
