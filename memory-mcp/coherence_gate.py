"""coherence_gate — turn the Coherence Yield diagnostic into an actual gate.

csb already MEASURES coherence (efficacy_measure.coherence_yield) but the number
gated nothing — a thermometer, not a thermostat. This module wires the missing
leg an Amodei-style review names: measure -> threshold -> GATE, at the write path.

The control: a *fresh* candidate belief that inverts a *load-bearing* existing
belief (existing confidence >= floor) is BLOCKED from being written until a human
resolves the clash, instead of being silently saved alongside its own negation.

Honesty boundary (Weizenbaum/Amodei lenses, /tribunal 2026-05-31): this is a
diagnostic gate over RECORDS. It blocks a write because two stored statements
invert each other on a shared tag. It does NOT mean the agent "knows" anything,
is "coherent", or is "safe to act autonomously". It is a string-level consistency
tripwire on the memory store — useful precisely because nothing else gates on it.

    from coherence_gate import evaluate_gate, gated_save
    result = gated_save(db, content=..., category="fact", tags=[...], confidence=0.9)
    if not result["saved"]:
        # surface result["gate"]["blocking_contradictions"] to the operator
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from db import MemoryDB

# Default load-bearing threshold. A contradiction only blocks if the EXISTING
# belief it inverts was written with at least this confidence. Below it, the
# clash is advisory (surfaced, not blocking) — you don't halt the agent over a
# belief it was never sure of.
DEFAULT_CONFIDENCE_FLOOR = 0.8


def evaluate_gate(
    db: "MemoryDB",
    content: str,
    tags: list[str],
    project: Optional[str] = None,
    confidence_floor: float = DEFAULT_CONFIDENCE_FLOOR,
    since_days: int = 30,
) -> dict:
    """Decide whether writing `content` should be blocked.

    Pure read — never mutates the store. Returns:
        {
          "blocked": bool,                       # True iff a load-bearing clash exists
          "decision": "block" | "allow",
          "confidence_floor": float,
          "contradictions": [ {id, content, confidence, load_bearing} ],  # all clashes
          "blocking_contradictions": [ ...load_bearing subset... ],
          "reason": str,
        }
    """
    conflicts = db.find_conflicts(content, tags, project=project, since_days=since_days)

    annotated = []
    for c in conflicts:
        load_bearing = c["confidence"] >= confidence_floor
        annotated.append({**c, "load_bearing": load_bearing})

    blocking = [c for c in annotated if c["load_bearing"]]
    blocked = len(blocking) > 0

    if blocked:
        reason = (
            f"{len(blocking)} load-bearing contradiction(s) "
            f"(existing confidence >= {confidence_floor}). "
            f"Resolve the clash (retire the stale side) before writing."
        )
    elif annotated:
        reason = (
            f"{len(annotated)} advisory contradiction(s) below the "
            f"{confidence_floor} floor — surfaced, not blocking."
        )
    else:
        reason = "No contradiction with existing beliefs."

    return {
        "blocked": blocked,
        "decision": "block" if blocked else "allow",
        "confidence_floor": confidence_floor,
        "contradictions": annotated,
        "blocking_contradictions": blocking,
        "reason": reason,
    }


def evaluate_gate_tiered(
    db: "MemoryDB",
    content: str,
    tags: list[str],
    project: Optional[str] = None,
    *,
    confidence_floor: float = DEFAULT_CONFIDENCE_FLOOR,
    judge_fn=None,
    escalate: bool = True,
    since_days: int = 30,
) -> dict:
    """Tiered coherence gate: fast structural Tier-0, then semantic Tier-2.

    Tier-0 (sync, structural): the existing token-inversion `evaluate_gate`. If it
    finds a load-bearing block, return immediately — the judge is NEVER called for
    the obvious cases (fast path, no LLM latency).

    Tier-2 (semantic, escalation): only if Tier-0 did not block, `escalate` is on,
    and a `judge_fn` is supplied. Fetch same-project tag-sharing neighbors and ask
    the entailment judge whether `content` violates each load-bearing one. A
    `{"violates": true}` against a belief with confidence >= floor → block.
    Judge ABSTAIN (None) is NOT a block — never guessed.

    `judge_fn(commitment, action) -> {"violates": bool, "why": str} | None`.
    Default None = pure structural (no latency, identical to evaluate_gate).
    NOTE: the semantic tier adds a judge call per candidate — it is the ESCALATION
    path, not the inline hot path. Honesty boundary unchanged: a diagnostic over
    records, not a claim the agent "knows" or is "safe".

    Returns evaluate_gate's dict shape plus `"tier": "structural" | "semantic"`.
    """
    base = evaluate_gate(
        db, content, tags, project=project,
        confidence_floor=confidence_floor, since_days=since_days,
    )
    base["tier"] = "structural"
    if base["blocked"]:
        return base  # Tier-0 caught it; do not pay judge latency

    if not (escalate and judge_fn):
        return base  # pure structural

    neighbors = db.tag_neighbors(tags, project=project, since_days=since_days)
    semantic_blocking = []
    for n in neighbors:
        if n["confidence"] < confidence_floor:
            continue  # not load-bearing — don't block over a weak prior
        verdict = judge_fn(n["content"], content)
        if verdict is None:
            continue  # abstain — never a block
        if verdict.get("violates"):
            semantic_blocking.append({
                **n, "load_bearing": True, "why": verdict.get("why", ""),
            })

    if semantic_blocking:
        return {
            "blocked": True,
            "decision": "block",
            "confidence_floor": confidence_floor,
            "contradictions": base["contradictions"],
            "blocking_contradictions": semantic_blocking,
            "reason": (
                f"{len(semantic_blocking)} load-bearing SEMANTIC contradiction(s) "
                f"(judge-detected, confidence >= {confidence_floor}). "
                f"Resolve the clash before writing."
            ),
            "tier": "semantic",
        }
    return base


def gated_save(
    db: "MemoryDB",
    content: str,
    category: str,
    *,
    tags: Optional[list[str]] = None,
    project: Optional[str] = None,
    confidence: float = 0.75,
    confidence_floor: float = DEFAULT_CONFIDENCE_FLOOR,
    since_days: int = 30,
    semantic: bool = False,
    judge_fn=None,
    **save_kwargs,
) -> dict:
    """Coherence-gated write. Saves `content` UNLESS it inverts a load-bearing
    existing belief, in which case the write is refused and surfaced.

    Returns:
        {"saved": bool, "mem_id": str | None, "gate": <evaluate_gate result>}
    """
    if semantic:
        gate = evaluate_gate_tiered(
            db, content, tags or [], project=project,
            confidence_floor=confidence_floor, since_days=since_days,
            judge_fn=judge_fn, escalate=True,
        )
    else:
        gate = evaluate_gate(
            db, content, tags or [], project=project,
            confidence_floor=confidence_floor, since_days=since_days,
        )
    if gate["blocked"]:
        return {"saved": False, "mem_id": None, "gate": gate}

    mem_id = db.save(
        content=content, category=category, tags=tags, project=project,
        confidence=confidence, **save_kwargs,
    )
    return {"saved": True, "mem_id": mem_id, "gate": gate}
