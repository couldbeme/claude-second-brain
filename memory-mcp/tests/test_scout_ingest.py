"""TDD for scout_ingest — the deterministic, model-free ingest spine of an
autonomous scout. RED: module absent.

A scout gathers findings (the GATHER step needs the model — WebSearch — and runs in
the interactive skill). Everything AFTER gather is deterministic and free, so it lives
here and is cron-safe: write findings into the belief DB (canonical, with cross-run
dedup so a daily run doesn't re-store yesterday's signal), mirror each to Obsidian, and
rank into a feed. No model, no network — pure (db, findings) -> result.

Reuses the daily-digest split: deterministic collector/ingest = free; model synthesis
stays interactive. See learnings_daily_digest_2026_06_01.
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPTS))

from db import MemoryDB  # noqa: E402
from scout_ingest import (  # noqa: E402  (RED: absent)
    ingest_findings,
    score,
    rank_feed,
    finding_from_memory,
)


@pytest.fixture
def db(tmp_path):
    d = MemoryDB(str(tmp_path / "m.db"))
    yield d
    d.close()


def _finding(**over):
    f = {
        "scout": "pain-scout",
        "title": "Founder: my agent keeps dropping the rules I set",
        "summary": "Reply under an agent-launch thread; 4 others agree.",
        "source_type": "x",
        "source_url": "https://x.com/u/status/100",
        "captured_at": "2026-06-01",
        "signal_strength": 0.8,
        "confidence": 0.7,
        "tags": ["agent-reliability", "lead"],
        "raw_quote": "it forgets constraints 5 steps later",
    }
    f.update(over)
    return f


# ---- scoring + ranking (pure) ---------------------------------------------

def test_score_is_signal_times_confidence():
    assert score(_finding(signal_strength=0.8, confidence=0.5)) == pytest.approx(0.4)


def test_score_defaults_are_safe():
    score({})  # must not raise on a bare dict


def test_rank_feed_sorts_desc_by_score():
    a = _finding(title="a", signal_strength=0.2, confidence=0.2)
    b = _finding(title="b", signal_strength=0.9, confidence=0.9, source_url="x/2")
    feed = rank_feed([a, b])
    assert feed[0]["title"] == "b"


def test_rank_feed_top_n_limits():
    fs = [_finding(title=str(i), source_url=f"x/{i}") for i in range(5)]
    assert len(rank_feed(fs, top_n=3)) == 3


# ---- ingest: persistence ---------------------------------------------------

def test_ingest_saves_to_belief_db_as_intel(db):
    res = ingest_findings(db, [_finding()], project="startup-intel")
    assert len(res["ingested"]) == 1
    assert res["ingested"][0]["id"]                       # got a db id
    rows = db.list_memories(category="intel", limit=100)
    assert len(rows) == 1
    assert rows[0]["confidence"] == pytest.approx(0.7)    # finding confidence persisted


def test_ingest_importance_tracks_signal_strength(db):
    ingest_findings(db, [_finding(signal_strength=0.8)], project="p")
    row = db.list_memories(category="intel", limit=10)[0]
    assert row["importance"] == 8                          # round(0.8*10)


# ---- ingest: cross-run dedup (the load-bearing property) -------------------

def test_ingest_dedups_same_source_url_across_runs(db):
    ingest_findings(db, [_finding()], project="p")          # run 1
    res2 = ingest_findings(db, [_finding(title="reworded")], project="p")  # run 2, same url
    assert res2["ingested"] == []
    assert len(res2["duplicates"]) == 1
    assert len(db.list_memories(category="intel", limit=100)) == 1   # not re-stored


def test_ingest_dedups_by_normalized_title_when_no_url(db):
    f = _finding(source_url=None)
    ingest_findings(db, [f], project="p")
    res2 = ingest_findings(db, [dict(f)], project="p")
    assert res2["ingested"] == []
    assert len(db.list_memories(category="intel", limit=100)) == 1


def test_distinct_findings_both_stored(db):
    ingest_findings(db, [_finding()], project="p")
    res2 = ingest_findings(db, [_finding(title="different", source_url="https://x.com/u/status/999")], project="p")
    assert len(res2["ingested"]) == 1
    assert len(db.list_memories(category="intel", limit=100)) == 2


# ---- ingest: Obsidian mirror ----------------------------------------------

def test_ingest_mirrors_to_vault_when_given(db, tmp_path):
    vault = tmp_path / "vault"
    res = ingest_findings(db, [_finding()], project="p", vault_dir=vault)
    notes = list(vault.glob("*.md"))
    assert len(notes) == 1
    assert "agent" in notes[0].read_text().lower()


def test_ingest_skips_mirror_when_no_vault(db):
    res = ingest_findings(db, [_finding()], project="p", vault_dir=None)
    assert len(res["ingested"]) == 1                       # still saved to db


# ---- vault regenerable from DB (round-trip) -------------------------------

def test_finding_from_memory_round_trips_key_fields(db):
    ingest_findings(db, [_finding()], project="p")
    mem = db.list_memories(category="intel", limit=1)[0]
    f = finding_from_memory(mem)
    assert f["title"] == "Founder: my agent keeps dropping the rules I set"
    assert f["source_url"] == "https://x.com/u/status/100"
    assert f["scout"] == "pain-scout"
    assert f["signal_strength"] == pytest.approx(0.8, abs=0.05)
    assert "agent-reliability" in f["tags"]               # topic tags survive
    # internal bookkeeping tags must NOT leak back as topic tags
    assert not any(t.startswith(("fp:", "src:", "type:")) for t in f["tags"])
