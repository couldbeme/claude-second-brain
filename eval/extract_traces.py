#!/usr/bin/env python3
"""extract_traces — mine REAL Claude Code session transcripts for commitment-drift
candidate pairs (P2: real agent traces, not synthetic).

A transcript is JSONL of {type: assistant|user|summary, message:{content:[blocks]}}.
Assistant text blocks may STATE a commitment ("I won't push without asking",
"I'll keep this backward-compatible", "TDD always"). Later assistant tool_use
blocks are ACTIONS (Bash command, file write, etc.). We pair a stated commitment
with each subsequent action in the same session → a real (commitment, action) the
LLM judge can score.

PRIVACY: only reads transcripts under projects matching --owner (default the
operator's own `-Users-macbook-`); skips others. Extracted output is structural
(commitment text + action summary) and stays in the PRIVATE repo. We do NOT copy
transcript bodies wholesale — only the matched commitment line + a one-line action.

This is a CANDIDATE extractor: it finds plausible commitment statements with a
keyword heuristic; pairs still need human/LLM labeling. It does not itself decide
drift — it builds the dataset the judge runs on.
"""
from __future__ import annotations

import glob
import json
import os
import re

# Commitment-shaped assistant statements (first-person constraint the agent sets).
_COMMIT_RE = re.compile(
    r"\b("
    r"i (?:will|'ll|won't|will not|won't|am going to|won't be)\b[^.\n]{0,90}"
    r"|i (?:never|always|won't ever)\b[^.\n]{0,90}"
    r"|(?:per your|standing) rule[^.\n]{0,80}"
    r"|(?:i (?:promise|commit|guarantee))\b[^.\n]{0,90}"
    r")",
    re.IGNORECASE,
)
# Stronger: explicit prohibition first-person ("I won't X", "I will not Y", "never Z")
_PROHIB_RE = re.compile(
    r"\bi (?:won't|will not|won'?t ever|never|am not going to|won't be)\b[^.\n]{3,90}",
    re.IGNORECASE,
)


def _text_blocks(msg) -> list:
    out = []
    for blk in (msg.get("content") or []):
        if isinstance(blk, dict) and blk.get("type") == "text":
            out.append(blk["text"])
    return out


def _tool_uses(msg) -> list:
    out = []
    for blk in (msg.get("content") or []):
        if isinstance(blk, dict) and blk.get("type") == "tool_use":
            inp = blk.get("input") or {}
            summ = inp.get("command") or inp.get("file_path") or inp.get("description") or ""
            out.append({"tool": blk.get("name"), "summary": str(summ)[:160]})
    return out


def extract_session(path: str) -> dict:
    """Return {commitments:[...], actions:[...]} found in one transcript, in order."""
    commitments, actions = [], []
    order = 0
    for line in open(path, encoding="utf-8", errors="replace"):
        line = line.strip()
        if not line:
            continue
        try:
            o = json.loads(line)
        except Exception:
            continue
        if o.get("type") != "assistant":
            continue
        msg = o.get("message", {})
        for txt in _text_blocks(msg):
            for m in _PROHIB_RE.finditer(txt):
                commitments.append({"order": order, "text": m.group(0).strip()})
        for tu in _tool_uses(msg):
            if tu["summary"]:
                actions.append({"order": order, **tu})
        order += 1
    return {"commitments": commitments, "actions": actions}


def main() -> int:
    import sys
    owner = "-Users-macbook-"
    root = os.path.expanduser("~/.claude/projects")
    paths = [p for p in glob.glob(f"{root}/*/*.jsonl") if owner in p]
    out_path = sys.argv[1] if len(sys.argv) > 1 else "/tmp/real_traces.jsonl"
    n_sessions = n_commit = n_pairs = 0
    with open(out_path, "w") as out:
        for p in paths:
            try:
                s = extract_session(p)
            except Exception:
                continue
            if not s["commitments"] or not s["actions"]:
                continue
            n_sessions += 1
            n_commit += len(s["commitments"])
            # pair each commitment with later actions in the same session
            for c in s["commitments"]:
                later = [a for a in s["actions"] if a["order"] > c["order"]]
                for a in later[:8]:  # cap per commitment to avoid blowup
                    out.write(json.dumps({
                        "session": os.path.basename(p),
                        "commitment": c["text"],
                        "action": f"{a['tool']}: {a['summary']}",
                    }) + "\n")
                    n_pairs += 1
    summary = {"sessions_with_commitments": n_sessions,
               "total_commitments": n_commit,
               "candidate_pairs": n_pairs,
               "transcripts_scanned": len(paths),
               "out": out_path}
    with open(out_path + ".summary.json", "w") as f:
        json.dump(summary, f, indent=2)
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
