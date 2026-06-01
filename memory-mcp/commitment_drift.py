"""commitment_drift — P0 reliability instrument for long-horizon agent coherence.

Flags when an agent's ACTION contradicts a commitment the agent itself stated
earlier in the same task ("never force-push main" -> later force-pushes main).
This is *commitment drift* — the long-horizon reliability failure of agentic
work — and it is distinct from contradiction-between-two-stored-memories
(see coherence_gate.py / efficacy_measure.py).

WHAT THIS IS / IS NOT (read before using):
  - It is a RELIABILITY / data-quality instrument, NOT a security control. It
    catches an HONEST agent drifting from its own stated constraints. It does
    NOT stop prompt injection, exfiltration, or a compromised agent that simply
    never states a commitment. (Willison/Schneier: coherence != security.)
  - It keys on the OBSERVED action text, NEVER on an agent-supplied self-label.
    `declared_intent` is accepted but IGNORED for the decision — it's an
    untrusted hint, recorded for the human, never trusted to suppress a flag.
    (Schneier: the gated party must not classify itself out of the gate.)

v0.1 IS STRUCTURAL (token-level) — honest blind spots:
  - Catches literal / near-literal drift (shared content tokens after a
    prohibition marker: never / don't / must not / avoid / read-only).
  - MISSES paraphrases with no shared tokens ("git push -f origin HEAD:main"
    has no 'force'/'push' token to match "never force-push to main"). The test
    suite asserts this miss so the limitation is documented, not hidden.
  - Handles prohibition-style commitments; positive constraints phrased without
    a prohibition marker (e.g. "always keep the API compatible") yield no terms
    and are skipped. Semantic detection is the v0.2 experiment.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional

# Markers that introduce a prohibition. Text after the marker (up to the next
# sentence delimiter) is the prohibited core.
_PROHIBITION_MARKERS = (
    "must never", "must not", "do not", "don't", "dont", "never", "avoid", "no longer",
)

# "read-only" implies a prohibition on writing.
_READONLY_RE = re.compile(r"read[\s\-]?only")

_STOPWORDS = frozenset({
    "to", "the", "a", "an", "is", "are", "be", "of", "in", "on", "for", "and",
    "or", "do", "not", "any", "all", "it", "its", "this", "that", "please",
    "will", "would", "should", "must", "always", "keep", "stay", "ever",
})


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z]+", text.lower())


def _stem(tok: str) -> str:
    """Crude singularize so 'files' matches 'file'."""
    return tok[:-1] if len(tok) > 3 and tok.endswith("s") else tok


def _content_terms(text: str) -> set[str]:
    return {_stem(t) for t in _tokenize(text) if t not in _STOPWORDS}


@dataclass(frozen=True)
class Commitment:
    text: str
    terms: frozenset  # the prohibited core (stemmed content tokens); empty = not a constraint


@dataclass
class DriftReport:
    drifted: bool
    violations: list = field(default_factory=list)  # [{commitment_text, matched_terms}]
    note: str = ""


def parse_commitment(text: str) -> Commitment:
    """Extract the prohibited-core terms from a commitment statement.

    A commitment is a *constraint* only if it carries a prohibition marker
    (never / don't / must not / avoid) or 'read-only'. Otherwise terms is empty
    and the commitment is treated as a non-constraint (skipped by check_action).
    """
    lowered = (text or "").lower()
    terms: set[str] = set()

    if _READONLY_RE.search(lowered):
        terms.add("write")

    for marker in _PROHIBITION_MARKERS:
        idx = lowered.find(marker)
        if idx == -1:
            continue
        # clause = text from end of marker to the next sentence delimiter
        clause = lowered[idx + len(marker):]
        clause = re.split(r"[.;,!\n]", clause, maxsplit=1)[0]
        terms |= _content_terms(clause)

    return Commitment(text=text, terms=frozenset(terms))


def check_action(
    action_text: str,
    commitments: list[Commitment],
    *,
    declared_intent: Optional[str] = None,
) -> DriftReport:
    """Flag whether `action_text` drifts from any prior commitment.

    Decision is made ONLY from the observed `action_text`. `declared_intent` is
    recorded in the note but never trusted to suppress a flag.
    """
    action_terms = {_stem(t) for t in _tokenize(action_text or "")}

    violations: list[dict] = []
    for c in commitments:
        if not c.terms:
            continue  # non-constraint commitment -> nothing to enforce
        if c.terms <= action_terms:  # every prohibited-core term present in the action
            violations.append({
                "commitment_text": c.text,
                "matched_terms": sorted(c.terms),
            })

    note = ""
    if declared_intent:
        note = f"agent declared_intent (untrusted, ignored for decision): {declared_intent!r}"

    return DriftReport(drifted=bool(violations), violations=violations, note=note)
