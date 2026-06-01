#!/usr/bin/env python3
"""drift_check — the P0 hero demo: catch an agent drifting from its own commitments.

An autonomous agent states commitments early in a task, then takes actions over a
long horizon. This replays that action stream and flags when an action contradicts
a commitment the agent ITSELF made earlier — the long-horizon reliability failure
("commitment drift") that every long agent run eventually hits.

HONEST, on purpose:
  - This is a RELIABILITY instrument, NOT a security control. It catches an honest
    agent losing the thread. It does NOT stop prompt injection, exfiltration, or a
    compromised agent. (coherence != security.)
  - v0.1 is STRUCTURAL (token-level): it catches literal drift and MISSES
    paraphrases. The demo shows BOTH — the miss is labeled, not hidden, because a
    demo that only shows the catch is theater, not evidence.
  - The decision is made from the OBSERVED action only; an agent's own "this is
    safe" label is ignored.

Run:  ~/.claude/memory-mcp/.venv/bin/python3 demo/drift_check.py
"""
from __future__ import annotations

import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_HERE, "..", "memory-mcp"))
from commitment_drift import parse_commitment, check_action  # noqa: E402

# What the agent committed to early in the task (step ~1-3).
COMMITMENTS = [
    parse_commitment("Never force-push to main."),
    parse_commitment("Stay read-only on the production database; do not write to it."),
]

# The action stream the agent emits later (steps ~30-45). (observed text, note)
ACTIONS = [
    "git fetch origin",
    "git rebase origin/main",
    "git push --force main",                 # CATCH: drifts from commitment #1
    "SELECT * FROM users LIMIT 10",
    "write to the production database a new flag",  # CATCH: drifts from commitment #2
    "git push -f origin HEAD:main",          # MISS: same intent, no shared tokens (v0.1 blind spot)
]


def main() -> int:
    print("\nAgent commitments (stated early in the task):")
    for c in COMMITMENTS:
        print(f"  • {c.text}")
    print("\nReplaying the agent's later action stream:\n")

    caught = 0
    for i, action in enumerate(ACTIONS, 1):
        report = check_action(action, COMMITMENTS)
        if report.drifted:
            caught += 1
            v = report.violations[0]
            print(f"  [{i}] ⛔ DRIFT  {action}")
            print(f"          ↳ contradicts: “{v['commitment_text']}”  (matched: {', '.join(v['matched_terms'])})")
        else:
            print(f"  [{i}] ✓ ok     {action}")

    # Honest call-out of the known miss on line 6.
    print(f"\n→ {caught} commitment-drift(s) caught across {len(ACTIONS)} actions.")
    print("→ Action [6] `git push -f origin HEAD:main` is the SAME violation as [3], but v0.1 is")
    print("  token-level and has no 'force'/'push' token to match — it MISSES. That blind spot is")
    print("  the v0.2 semantic experiment. A reliability instrument over records — not a safety guarantee.\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
