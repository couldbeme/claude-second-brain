#!/usr/bin/env python3
"""commitment_gate_hook — PreToolUse hook that BLOCKS an agent action which
contradicts a stored operator commitment.

The un-absorbed sliver: native PreToolUse can block (exit 2), and native Auto
memory/Dreaming store + curate memories — but nothing gates an ACTION against the
operator's stored COMMITMENTS at execution time. This wires that.

Native PreToolUse contract (verified from anthropics/claude-code
examples/hooks/bash_command_validator_example.py):
    stdin JSON: {"tool_name": str, "tool_input": {...}}
    exit 2 + stderr  -> BLOCK the tool call (stderr shown to Claude)
    exit 0           -> allow

INSTALL (operator opt-in; inert until referenced in settings.json):
    {"hooks": {"PreToolUse": [{"matcher": "*", "hooks": [
      {"type": "command",
       "command": "VENV/bin/python3 .../commitment_gate_hook.py"}]}]}}

Safety rails (2026-05-31 safety tribunal — Schneier/Willison/Amodei):
  - Gate on the OBSERVED action text (the real command/content/args), NEVER an
    agent-supplied self-label like `description`. The gated party must not classify
    itself out of the gate.
  - FAIL-OPEN on ANY error (bad json, missing db, import fail). A gate that breaks
    every tool call on its own bug is worse than no gate. Only a genuine detected
    load-bearing contradiction blocks (exit 2).
  - This is a DIAGNOSTIC over records — it blocks because the action's text inverts
    a stored commitment. NOT a claim the agent "knows" or is "safe".

By default runs STRUCTURAL only (fast, no LLM). Set COMMITMENT_GATE_SEMANTIC=1 to
escalate ambiguous actions to the semantic judge (adds latency — opt-in).

ROLLOUT (Phase 1c): SHADOW by default — a detected contradiction is logged to stderr
but the tool call is ALLOWED (exit 0). Set COMMITMENT_GATE_ENFORCE=1 to actually
block (exit 2). Roll out in shadow, read the would-block log, then enforce.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

# Fields of tool_input that carry the OBSERVED action. `description` and other
# agent-narration fields are deliberately EXCLUDED (Schneier: no self-label).
_ACTION_FIELDS = ("command", "content", "new_string", "file_path", "url", "query", "prompt")
_FLOOR = float(os.environ.get("COMMITMENT_GATE_FLOOR", "0.8"))
# Phase 1c rollout safety: SHADOW by default — detect + log a would-block but exit 0
# (never break a live session until the false-positive rate is known). Set
# COMMITMENT_GATE_ENFORCE=1 to actually block (exit 2).
_ENFORCE = os.environ.get("COMMITMENT_GATE_ENFORCE", "0") == "1"


def _observed_action(tool_input: dict) -> str:
    parts = []
    for f in _ACTION_FIELDS:
        v = tool_input.get(f)
        if isinstance(v, str) and v.strip():
            parts.append(v)
    return "  ".join(parts)


def _allow() -> int:
    return 0


def _block(reason: str) -> int:
    sys.stderr.write(reason)
    return 2


def main() -> int:
    raw = sys.stdin.read()
    try:
        event = json.loads(raw) if raw.strip() else {}
    except Exception:
        return _allow()  # fail-open

    tool_input = event.get("tool_input") or {}
    action = _observed_action(tool_input)
    if not action:
        return _allow()

    db_path = os.environ.get("MEMORY_DB") or str(
        Path.home() / ".claude" / "memory" / "memory.db"
    )
    if not os.path.exists(db_path):
        return _allow()  # nothing to contradict

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    try:
        from db import MemoryDB
        from coherence_gate import evaluate_gate, evaluate_gate_tiered
        from commitments import load_commitments, commitment_tags

        # Commitments live as rule/pattern memories. commitments.load_commitments is
        # the SINGLE provenance (shared with the override CLI + the digest). Derive
        # the candidate tag set from ALL stored commitments so any commitment sharing
        # a tag with the action is considered.
        db = MemoryDB(db_path)
        try:
            tags = commitment_tags(load_commitments(db))
            if not tags:
                return _allow()
            semantic = os.environ.get("COMMITMENT_GATE_SEMANTIC", "0") == "1"
            if semantic:
                from llm_judge import judge as _judge
                model = os.environ.get("COMMITMENT_GATE_MODEL", "qwen/qwen3-vl-8b")
                jf = lambda c, a: _judge(c, a, model=model)  # noqa: E731
                decision = evaluate_gate_tiered(
                    db, action, tags, confidence_floor=_FLOOR, judge_fn=jf)
            else:
                decision = evaluate_gate(db, action, tags, confidence_floor=_FLOOR)

            if not decision.get("blocked"):
                return _allow()

            bc = decision["blocking_contradictions"][0]
            # 1b: the durable diagnostic edge — record the block in BOTH shadow and
            # enforce modes, while db is open. record_block is DIAGNOSTIC ONLY: it
            # writes a feedback_violations row and NEVER decays the commitment's
            # confidence (a block is the gate working, not evidence the commitment is
            # wrong — only a human softens a commitment, via override_review). Fail-open.
            from coherence_feedback import record_block
            action_hash = hashlib.sha256(action.encode("utf-8")).hexdigest()[:16]
            record_block(db, bc, session_id=event.get("session_id"),
                         action_hash=action_hash)

            reason = (
                "Commitment gate: this action contradicts a stored commitment "
                f"(confidence {bc.get('confidence', '?')}): \"{bc.get('content','')}\". "
                "Resolve the clash — retire the stale commitment, or restate the action. "
                "(Diagnostic over records, not a safety guarantee.)"
            )
            if _ENFORCE:
                return _block(reason)
            # Shadow mode (default): detected + logged + recorded, but NOT blocked.
            sys.stderr.write(
                "[commitment-gate shadow] WOULD block "
                "(set COMMITMENT_GATE_ENFORCE=1 to enforce): " + reason
            )
            return _allow()
        finally:
            db.close()
    except Exception:
        return _allow()  # fail-open on ANY substrate error


if __name__ == "__main__":
    sys.exit(main())
