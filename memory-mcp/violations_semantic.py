"""violations_semantic — judge-backed feedback-violation detection (P2.5).

Wires the proven commitment-drift entailment judge into the dormant behavioral-
coherence primitive. feedback memories (category 'rule'/'pattern') ARE persistent
commitments; an action this session that violates one is the same entailment the
P0-P2 judge handles. This replaces the keyword matcher in
feedback_violations.extract_trigger_patterns (which P1 proved is a 30%-recall toy).

The judge is INJECTABLE (judge_fn) so callers/tests can supply a fake; the default
uses llm_judge.judge (needs a chat endpoint). Violations feed
efficacy_measure.coherence_yield_behavior via the feedback_violations table.

Honesty rails (same as the rest of the stack):
  - decision from the OBSERVED action + the rule only; no agent self-label.
  - judge ABSTAIN (None) is NOT a violation — never guessed.
  - this is a reliability/coherence DIAGNOSTIC over records, not a security control.
"""
from __future__ import annotations

from typing import Callable, Optional

# rule-bearing feedback memories live under these categories (see feedback_violations)
_RULE_CATEGORIES = ("rule", "pattern")


def _default_judge(model: str):
    from llm_judge import judge as _j

    def _fn(commitment: str, action: str):
        return _j(commitment, action, model=model)
    return _fn


def detect_violations_semantic(
    db,
    actions: list[str],
    *,
    judge_fn: Optional[Callable[[str, str], Optional[dict]]] = None,
    model: str = "qwen/qwen3-vl-8b",
    record: bool = False,
    session_id: Optional[str] = None,
) -> list[dict]:
    """Flag actions that violate a stored feedback-rule, by entailment judge.

    Returns [{feedback_memory_id, rule, action, why}] — one per (rule, action)
    the judge calls a violation. Deduped by (rule_id, action). If record=True,
    inserts each into the feedback_violations table (feeds CY-behavior).
    """
    judge_fn = judge_fn or _default_judge(model)

    placeholders = ",".join("?" for _ in _RULE_CATEGORIES)
    rules = db.conn.execute(
        f"SELECT id, content FROM memories WHERE category IN ({placeholders})",
        _RULE_CATEGORIES,
    ).fetchall()

    out: list[dict] = []
    seen: set = set()
    for (rule_id, rule_text) in rules:
        if not rule_text:
            continue
        for action in actions:
            if not action:
                continue
            key = (rule_id, action)
            if key in seen:
                continue
            verdict = judge_fn(rule_text, action)
            if verdict is None:               # abstain — never a violation
                continue
            if not verdict.get("violates"):
                continue
            seen.add(key)
            rec = {
                "feedback_memory_id": rule_id,
                "rule": rule_text,
                "action": action,
                "why": verdict.get("why", ""),
            }
            out.append(rec)
            if record:
                from feedback_violations import record_violation
                record_violation(db, rule_id, action[:200], rec["why"][:200],
                                  session_id=session_id)
    return out
