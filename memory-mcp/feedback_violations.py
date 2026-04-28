"""Feedback-violation detector — MYTHOS-SUBSTRATE Phase 1.

Surfaces "you might be about to violate a feedback memory" as a deterministic
runtime check. No LLM in the loop. Pattern-extraction is rule-based v0.1
(noun-phrase n-grams from "How to apply:" sections + imperative-marker
sentences).

Usage:
    from feedback_violations import detect_violations, record_violation

    violations = detect_violations(db, session_text)
    for v in violations:
        record_violation(db, v["feedback_memory_id"], v["matched_text"],
                         v["matched_pattern"], session_id=session_id)

Companion: efficacy_measure.coherence_yield_behavior() reads from
`feedback_violations` table and returns a behavioral analog of CY.
"""

from __future__ import annotations

import re
import secrets
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from db import MemoryDB


# Pattern extraction --------------------------------------------------------

# Words that mark imperative-form rules in feedback memory content.
_IMPERATIVE_MARKERS = ("never", "don't", "do not", "always", "stop", "avoid")

# Stopwords trimmed from extracted patterns to keep them concrete.
_STOPWORDS = frozenset({
    "the", "a", "an", "and", "or", "of", "to", "in", "on", "for", "with",
    "is", "are", "was", "were", "be", "been", "being", "this", "that",
    "these", "those", "it", "its", "as", "at", "by", "from", "up", "off",
    "if", "any", "all", "some", "you", "your", "we", "our", "they", "them",
    "their", "i", "me", "my", "s", "t", "have", "has", "had", "do", "does",
    "did", "will", "would", "should", "could", "may", "might", "must",
    "shall", "can", "rule", "via", "into", "but", "than", "out", "over",
})


def extract_trigger_patterns(content: str) -> list[str]:
    """Extract short keyword-phrase patterns from a feedback memory's content.

    v0.1 strategy:
    1. Find sentences after imperative markers (never / don't / always / stop)
    2. Find the "How to apply:" section if present
    3. Return de-stopworded n-grams (≥2 content words) suitable for substring
       matching against session text. Short (1-word) patterns are dropped to
       reduce false positives.

    Returns: list of lowercase patterns, deduplicated, max 6 per memory.
    """
    if not content or not content.strip():
        return []

    text = content.lower()
    candidates: list[str] = []

    # 1. Imperative-marker sentences
    for marker in _IMPERATIVE_MARKERS:
        for match in re.finditer(rf"\b{re.escape(marker)}\b\s+([^\.\n!]{{3,80}})", text):
            tail = match.group(1).strip()
            content_words = [w for w in re.findall(r"[a-z][a-z\-]+", tail) if w not in _STOPWORDS]
            if len(content_words) >= 2:
                candidates.append(" ".join(content_words[:5]))

    # 2. "How to apply:" sections
    for section in re.findall(r"how to apply[:\*]+\s*([^\n#]{5,200})", text):
        content_words = [w for w in re.findall(r"[a-z][a-z\-]+", section) if w not in _STOPWORDS]
        if len(content_words) >= 2:
            candidates.append(" ".join(content_words[:4]))

    # Dedupe + cap
    seen: set[str] = set()
    out: list[str] = []
    for c in candidates:
        if c and c not in seen:
            seen.add(c)
            out.append(c)
        if len(out) >= 6:
            break
    return out


# Violation detection -------------------------------------------------------

def detect_violations(
    db: "MemoryDB",
    session_text: str,
    session_id: str | None = None,
) -> list[dict]:
    """Scan session_text for matches against any feedback memory's triggers.

    Returns a list of dicts: {feedback_memory_id, matched_text, matched_pattern}.
    Does NOT write to the violations table — that's record_violation's job.
    """
    if not session_text or not session_text.strip():
        return []

    text_lower = session_text.lower()

    # Feedback memories live under category="pattern" (mapping for type=feedback)
    # and category="rule" for explicit rules. Pull both.
    rows = db.conn.execute(
        """SELECT id, content FROM memories
           WHERE category IN ('pattern', 'rule')""",
    ).fetchall()

    violations: list[dict] = []
    seen_pairs: set[tuple[str, str]] = set()

    for mem_id, content in rows:
        for pattern in extract_trigger_patterns(content or ""):
            if pattern in text_lower:
                key = (mem_id, pattern)
                if key in seen_pairs:
                    continue
                seen_pairs.add(key)
                idx = text_lower.find(pattern)
                start = max(0, idx - 30)
                end = min(len(session_text), idx + len(pattern) + 30)
                snippet = session_text[start:end]
                violations.append({
                    "feedback_memory_id": mem_id,
                    "matched_text": snippet,
                    "matched_pattern": pattern,
                })

    return violations


# Persistence ---------------------------------------------------------------

def record_violation(
    db: "MemoryDB",
    feedback_memory_id: str,
    matched_text: str,
    matched_pattern: str,
    session_id: str | None = None,
) -> str:
    """Insert a feedback_violations row. Returns the new violation id."""
    vid = secrets.token_hex(8)
    db.conn.execute(
        """INSERT INTO feedback_violations
           (id, feedback_memory_id, matched_text, matched_pattern,
            session_id, detected_at)
           VALUES (?, ?, ?, ?, ?, datetime('now'))""",
        (vid, feedback_memory_id, matched_text, matched_pattern, session_id),
    )
    db.conn.commit()
    return vid
