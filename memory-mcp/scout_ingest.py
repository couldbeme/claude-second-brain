"""scout_ingest — the deterministic, model-free ingest spine of an autonomous scout.

A scout's lifecycle is GATHER (needs the model: WebSearch over X/web — runs in the
interactive `/pain-scout` skill) then INGEST (deterministic — this module). Keeping
ingest model-free means it is FREE to run on a schedule: per the daily-digest finding,
scheduled `claude -p`/SDK draws a separate METERED credit pool from 2026-06-15, so the
free pattern is "deterministic work in cron, model synthesis interactive"
([[learnings_daily_digest_2026_06_01]]).

What ingest does, given findings the gather step produced:
  1. Write each finding into the belief DB (category="intel") — the CANONICAL store,
     which gives contradiction-detection + confidence-weighting for free.
  2. DEDUP across runs so a daily run doesn't re-store yesterday's signal — keyed on a
     fingerprint (source_url, else normalized title) stored as an `fp:` tag.
  3. Mirror each NEW finding to an Obsidian vault (human view) via intel_mirror.
  4. Return a ranked feed (signal_strength × confidence).

The DB↔finding mapping is round-trippable (`finding_from_memory`) so the vault is
regenerable from the DB alone.
"""
from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any, Optional

from intel_mirror import write_note

_INTEL = "intel"
_WS = re.compile(r"\s+")


# --------------------------------------------------------------------------- scoring

def score(finding: dict[str, Any]) -> float:
    """Salience = signal_strength × confidence. Safe on a bare/partial dict."""
    s = finding.get("signal_strength")
    c = finding.get("confidence")
    s = 0.0 if s is None else float(s)
    c = 0.75 if c is None else float(c)
    return s * c


def rank_feed(findings: list[dict], top_n: Optional[int] = None) -> list[dict]:
    ranked = sorted(findings, key=score, reverse=True)
    return ranked[:top_n] if top_n else ranked


# ----------------------------------------------------------------- fingerprint / dedup

def _normalize(text: str) -> str:
    return _WS.sub(" ", (text or "").strip().lower())


def _fingerprint(finding: dict[str, Any]) -> str:
    """Stable identity for a finding: prefer the source URL (one tweet = one finding);
    fall back to the normalized title when a finding is uncited."""
    basis = finding.get("source_url") or _normalize(finding.get("title", ""))
    return hashlib.sha256(basis.encode("utf-8")).hexdigest()[:12]


def _existing_fingerprints(db, project: Optional[str]) -> set[str]:
    fps: set[str] = set()
    for mem in db.list_memories(category=_INTEL, project=project, limit=100000):
        for t in mem.get("tags", []):
            if t.startswith("fp:"):
                fps.add(t[3:])
    return fps


# ----------------------------------------------------------------- tag (de)composition

_RESERVED = ("fp:", "src:", "type:", "scout:")


def _compose_tags(finding: dict[str, Any]) -> list[str]:
    fp = _fingerprint(finding)
    tags = [f"fp:{fp}", f"scout:{finding.get('scout', 'unknown')}"]
    if finding.get("source_url"):
        tags.append(f"src:{finding['source_url']}")
    if finding.get("source_type"):
        tags.append(f"type:{finding['source_type']}")
    for t in finding.get("tags", []):
        tags.append(str(t))
    return tags


def finding_from_memory(mem: dict[str, Any]) -> dict[str, Any]:
    """Reverse map a belief-DB intel memory back into a finding dict, so the Obsidian
    vault can be regenerated from the DB alone. raw_quote is not separately preserved
    (it lives in the prose content) → a regenerated note renders it INFERRED, honestly."""
    tags = mem.get("tags", [])
    src = next((t[4:] for t in tags if t.startswith("src:")), None)
    stype = next((t[5:] for t in tags if t.startswith("type:")), None)
    scout = next((t[6:] for t in tags if t.startswith("scout:")), None)
    topic = [t for t in tags if not t.startswith(_RESERVED)]
    imp = mem.get("importance")
    return {
        "id": mem.get("id"),
        "scout": scout or (mem.get("source", "").removeprefix("scout:") or "unknown"),
        "title": mem.get("summary") or mem.get("content", ""),
        "summary": mem.get("content", ""),
        "source_type": stype,
        "source_url": src,
        "signal_strength": (imp / 10.0) if isinstance(imp, (int, float)) else None,
        "confidence": mem.get("confidence", 0.75),
        "tags": topic,
        "raw_quote": None,
        "related": [],
    }


# ----------------------------------------------------------------------------- ingest

def _importance(finding: dict[str, Any]) -> int:
    s = finding.get("signal_strength")
    if s is None:
        return 5
    return max(1, min(10, round(float(s) * 10)))


def ingest_findings(
    db,
    findings: list[dict[str, Any]],
    *,
    project: Optional[str] = None,
    vault_dir: Optional[str | Path] = None,
) -> dict[str, list[dict]]:
    """Persist + dedup + mirror a batch of findings. Returns
    {"ingested": [new findings w/ db id], "duplicates": [...], "feed": [ranked new]}.
    Idempotent across runs: a finding whose fingerprint already exists is skipped."""
    seen = _existing_fingerprints(db, project)
    ingested: list[dict] = []
    duplicates: list[dict] = []

    for f in findings:
        fp = _fingerprint(f)
        if fp in seen:
            duplicates.append(f)
            continue
        seen.add(fp)  # guard against intra-batch dupes too

        content = f.get("summary") or f.get("title", "")
        if f.get("raw_quote"):
            content = f"{content}\n\nQuote: {f['raw_quote']}"
        mem_id = db.save(
            content=content,
            category=_INTEL,
            summary=f.get("title", ""),
            tags=_compose_tags(f),
            project=project,
            importance=_importance(f),
            source=f"scout:{f.get('scout', 'unknown')}",
            confidence=float(f.get("confidence", 0.75)),
        )
        stored = dict(f, id=mem_id)
        ingested.append(stored)
        if vault_dir is not None:
            write_note(stored, vault_dir)

    return {"ingested": ingested, "duplicates": duplicates, "feed": rank_feed(ingested)}
