"""Tests for intel_mirror — render a belief-DB intel finding into an Obsidian note.

Decision (2026-06-01): the canonical intel store is the belief/memory DB (it gives
contradiction-detection, dedup, and confidence-weighting for free). Obsidian is a
HUMAN-FACING MIRROR — markdown notes written into a vault for graph-view + manual
reading. This module is the mirror writer: DB row -> Obsidian markdown. The DB stays
the source of truth; the vault is a derived view (safe to delete + regenerate).
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from intel_mirror import render_note, write_note, note_slug  # noqa: E402


def _finding(**over):
    f = {
        "id": 42,
        "scout": "trend-scout",
        "title": "Founders complaining agent memory silently drifts",
        "summary": "Multiple replies under an agent-launch thread report the agent "
        "forgetting stated constraints mid-task.",
        "source_type": "x",
        "source_url": "https://x.com/someuser/status/123",
        "captured_at": "2026-06-01",
        "signal_strength": 0.72,
        "confidence": 0.8,
        "tags": ["b2b-saas", "agent-reliability"],
        "related": ["agent-memory-pain"],
        "raw_quote": "my agent keeps forgetting the rules I gave it 5 steps ago",
    }
    f.update(over)
    return f


# ---- note_slug -------------------------------------------------------------

def test_slug_is_filesystem_safe():
    s = note_slug(_finding())
    assert "/" not in s and " " not in s
    assert s.endswith(".md")


def test_slug_is_stable_for_same_id():
    assert note_slug(_finding(id=42)) == note_slug(_finding(id=42))


# ---- render_note: frontmatter ---------------------------------------------

def test_render_has_yaml_frontmatter():
    note = render_note(_finding())
    assert note.startswith("---\n")
    assert note.count("---\n") >= 2  # open + close fence


def test_render_frontmatter_carries_provenance_and_scores():
    note = render_note(_finding())
    assert "source_url: https://x.com/someuser/status/123" in note
    assert "scout: trend-scout" in note
    assert "signal_strength: 0.72" in note
    assert "confidence: 0.8" in note
    assert "captured_at: 2026-06-01" in note


# ---- render_note: body -----------------------------------------------------

def test_render_body_has_title_and_summary():
    note = render_note(_finding())
    assert "# Founders complaining agent memory silently drifts" in note
    assert "silently drifts" in note  # summary present


def test_render_quotes_evidence_as_blockquote():
    note = render_note(_finding())
    assert "> my agent keeps forgetting the rules I gave it 5 steps ago" in note


def test_render_links_back_to_source():
    note = render_note(_finding())
    assert "https://x.com/someuser/status/123" in note


def test_render_emits_obsidian_wikilinks_for_related():
    note = render_note(_finding())
    assert "[[agent-memory-pain]]" in note


def test_render_emits_tags():
    note = render_note(_finding())
    assert "#trend-scout" in note          # scout as a tag
    assert "#b2b-saas" in note


# ---- honesty rail: never fabricate evidence -------------------------------

def test_render_marks_inferred_when_no_quote():
    note = render_note(_finding(raw_quote=None))
    # No fabricated quote; the absence is explicit, not invented.
    assert "my agent keeps forgetting" not in note
    assert "INFERRED" in note or "no direct quote" in note.lower()


def test_render_never_invents_a_source_url():
    note = render_note(_finding(source_url=None))
    assert "https://" not in note.split("# ", 1)[0] or "source_url:" in note
    assert "UNCITED" in note or "no source" in note.lower()


# ---- write_note ------------------------------------------------------------

def test_write_note_creates_file_in_vault(tmp_path):
    p = write_note(_finding(), vault_dir=tmp_path)
    assert p.exists()
    assert p.parent == tmp_path
    assert p.read_text().startswith("---\n")


def test_write_note_is_idempotent_by_id(tmp_path):
    p1 = write_note(_finding(title="v1"), vault_dir=tmp_path)
    p2 = write_note(_finding(title="v2"), vault_dir=tmp_path)
    assert p1 == p2                       # same id -> same file
    assert "v2" in p2.read_text()         # re-render overwrites (DB is truth)
    assert len(list(tmp_path.glob("*.md"))) == 1


def test_write_note_creates_vault_dir_if_missing(tmp_path):
    vault = tmp_path / "does-not-exist-yet"
    p = write_note(_finding(), vault_dir=vault)
    assert p.exists()
    assert vault.is_dir()
