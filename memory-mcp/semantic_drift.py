"""semantic_drift — P1 judge layer for commitment-drift detection.

Two judges over the same instrument:
  1. LEXICAL-ALIAS judge (runs anywhere, deterministic): normalizes dev/ops
     surface forms to a canonical term (-f->force, DROP->delete, ship->deploy,
     prod->production, credentials->secret) then reuses the structural overlap.
     A SHALLOW lift over v0.1 — catches synonym paraphrases, NOT real semantic
     equivalence.
  2. EMBEDDING judge (the real P1): cosine similarity between the action and the
     commitment's prohibited intent, via an embeddings endpoint (LM Studio). This
     is the honest semantic upgrade — but it needs an endpoint. `embedding_available()`
     probes for one; absent it, the judge cannot be evaluated (we do NOT fake numbers).

Honest stance: the alias judge is measurable anywhere but is partly circular on a
self-authored eval; the embedding judge is the real test and is gated on infra.
The gap between them is the point: how much of the paraphrase miss is cheap
synonyms vs genuine semantics.
"""

from __future__ import annotations

import json
import os
import urllib.request
from typing import Optional

from commitment_drift import parse_commitment, _tokenize, _stem, DriftReport  # noqa: F401

# General dev/ops surface-form -> canonical term. Authored from common practitioner
# knowledge, not reverse-engineered from the eval (though overlap is unavoidable).
ALIASES = {
    "f": "force", "force": "force", "forced": "force",
    "drop": "delete", "truncate": "delete", "delete": "delete", "remove": "delete", "rm": "delete", "del": "delete",
    "update": "write", "insert": "write", "write": "write", "set": "write", "modify": "write",
    "ship": "deploy", "release": "deploy", "deploy": "deploy", "rollout": "deploy", "publish": "deploy",
    "prod": "production", "production": "production",
    "credential": "secret", "credentials": "secret", "token": "secret", "secret": "secret",
    "env": "secret", "password": "secret", "apikey": "secret", "key": "secret",
    "master": "main", "main": "main",
}


def normalize_tokens(text: str) -> set:
    """Tokenize + stem + map known surface forms to their canonical term."""
    out = set()
    for t in _tokenize(text or ""):
        s = _stem(t)
        out.add(ALIASES.get(s, ALIASES.get(t, s)))
    return out


def check_action_aliased(action_text: str, commitments: list) -> DriftReport:
    """Like check_action, but matches on alias-normalized tokens (lexical-semantic)."""
    action_norm = normalize_tokens(action_text)
    violations = []
    for c in commitments:
        if not c.terms:
            continue
        terms_norm = {ALIASES.get(t, t) for t in c.terms}
        if terms_norm <= action_norm:
            violations.append({"commitment_text": c.text, "matched_terms": sorted(terms_norm)})
    return DriftReport(drifted=bool(violations), violations=violations)


# --- Embedding judge (the real P1 — gated on an endpoint) ---------------------

_EMBED_URL = os.environ.get("LMS_EMBEDDING_URL", "http://localhost:1234/v1/embeddings")


def embedding_available(timeout: float = 2.0) -> bool:
    """True iff an embeddings endpoint is reachable. We never fake numbers without one."""
    base = _EMBED_URL.rsplit("/v1/", 1)[0] + "/v1/models"
    try:
        with urllib.request.urlopen(base, timeout=timeout) as r:
            return r.status == 200
    except Exception:
        return False


def _embed(text: str, model: str, timeout: float) -> Optional[list]:
    payload = json.dumps({"model": model, "input": text}).encode()
    req = urllib.request.Request(_EMBED_URL, data=payload, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read())["data"][0]["embedding"]
    except Exception:
        return None


def _cosine(a: list, b: list) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = sum(x * x for x in a) ** 0.5
    nb = sum(y * y for y in b) ** 0.5
    return dot / (na * nb) if na and nb else 0.0


def check_action_embedding(action_text: str, commitments: list, *,
                           model: str = "text-embedding-nomic-embed-text-v1.5",
                           threshold: float = 0.55, timeout: float = 10.0) -> DriftReport:
    """Semantic judge: flag if the action embeds close to a commitment's prohibited
    intent. Requires an embeddings endpoint; raises RuntimeError if unavailable so a
    caller can NEVER mistake 'no endpoint' for 'no drift'."""
    if not embedding_available(timeout=2.0):
        raise RuntimeError(
            "No embeddings endpoint reachable at "
            f"{_EMBED_URL} — the semantic judge cannot be evaluated here. "
            "Start LM Studio (or set LMS_EMBEDDING_URL) to run real P1 numbers."
        )
    av = _embed(action_text, model, timeout)
    if av is None:
        raise RuntimeError("embedding request failed for the action")
    violations = []
    for c in commitments:
        if not c.terms:
            continue
        cv = _embed(c.text, model, timeout)
        if cv is None:
            continue
        sim = _cosine(av, cv)
        if sim >= threshold:
            violations.append({"commitment_text": c.text, "similarity": round(sim, 3)})
    return DriftReport(drifted=bool(violations), violations=violations)
