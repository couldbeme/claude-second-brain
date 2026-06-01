"""intel_mirror — mirror a belief-DB intel finding into an Obsidian vault note.

Architecture decision (2026-06-01): the startup-intel scouts write findings into the
belief/memory DB (the CANONICAL store — it gives contradiction-detection, dedup, and
confidence-weighting for free). Obsidian is a HUMAN-FACING MIRROR: derived markdown
notes for graph-view + manual reading. The DB stays the source of truth; the vault is
regenerable (safe to delete + rebuild from the DB at any time).

Honesty rails (inherited from /x-launch-recon + project DNA):
  - Never fabricate a quote: a finding with no `raw_quote` is rendered as INFERRED,
    not given invented words.
  - Never invent a source: a finding with no `source_url` is rendered UNCITED.
  - Every note carries provenance (source_url) + freshness (captured_at) + the
    scout's own signal_strength/confidence so a human can weigh it.

The vault dir is config (caller-supplied). Default lives in the scout config, not
here — this module is pure: (finding dict) -> markdown / file.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

_SLUG_RE = re.compile(r"[^a-z0-9]+")


def _slugify(text: str) -> str:
    return _SLUG_RE.sub("-", (text or "").lower()).strip("-") or "untitled"


def note_slug(finding: dict[str, Any]) -> str:
    """Filesystem-safe, id-stable note filename. Keyed on id ALONE so re-rendering a
    finding (e.g. after the scout updates its summary) overwrites the same note rather
    than spawning duplicates — the DB is the truth, the note is a regenerable view.
    The human-readable title lives in frontmatter (Obsidian shows it, not the
    filename)."""
    fid = finding.get("id")
    stem = f"finding-{fid:06d}" if isinstance(fid, int) else _slugify(str(fid))
    return f"{stem}.md"


def _yaml_list(items: list[str]) -> str:
    return "[" + ", ".join(items) + "]"


def render_note(finding: dict[str, Any]) -> str:
    """Render a finding into an Obsidian markdown note (YAML frontmatter + body).

    Pure function — no IO. Deterministic so the same DB row always renders the same
    note (idempotent mirror)."""
    title = finding.get("title", "Untitled finding")
    scout = finding.get("scout", "unknown-scout")
    source_url = finding.get("source_url")
    captured_at = finding.get("captured_at", "")
    source_type = finding.get("source_type", "")
    signal = finding.get("signal_strength")
    confidence = finding.get("confidence")
    tags = finding.get("tags") or []
    related = finding.get("related") or []
    summary = finding.get("summary", "")
    quote = finding.get("raw_quote")

    # --- frontmatter (provenance + scores; consumed by Obsidian Dataview) ---
    fm = ["---"]
    fm.append(f"title: {title}")
    fm.append(f"scout: {scout}")
    if source_type:
        fm.append(f"source_type: {source_type}")
    fm.append(f"source_url: {source_url}" if source_url else "source_url: null  # UNCITED")
    if captured_at:
        fm.append(f"captured_at: {captured_at}")
    if signal is not None:
        fm.append(f"signal_strength: {signal}")
    if confidence is not None:
        fm.append(f"confidence: {confidence}")
    # tags: scout name + finding tags, all as Obsidian-compatible frontmatter tags
    fm_tags = [scout] + [str(t) for t in tags]
    fm.append(f"tags: {_yaml_list(fm_tags)}")
    fm.append("mirror_of: belief-db  # canonical store is the DB; this note is derived")
    fm.append("---")

    body = [f"# {title}", ""]

    # evidence — quote it verbatim or mark INFERRED; never fabricate
    if quote:
        for line in str(quote).splitlines() or [""]:
            body.append(f"> {line}")
        body.append("")
    else:
        body.append("> _No direct quote captured — this finding is **INFERRED** from "
                     "the source, not a verbatim claim._")
        body.append("")

    if summary:
        body.append(summary)
        body.append("")

    # provenance line
    if source_url:
        body.append(f"**Source:** [{source_type or 'link'}]({source_url})")
    else:
        body.append("**Source:** _UNCITED — no source URL on this finding._")
    if captured_at:
        body.append(f"  ·  captured {captured_at}")
    body.append("")

    # Obsidian wikilinks to related findings (builds the graph)
    if related:
        body.append("**Related:** " + " ".join(f"[[{_slugify(str(r))}]]" for r in related))
        body.append("")

    # inline tags (Obsidian renders #tag); scout as a namespaced tag too
    tag_line = " ".join([f"#{scout}"] + [f"#{_slugify(str(t))}" for t in tags])
    if tag_line.strip():
        body.append(tag_line)

    return "\n".join(fm) + "\n" + "\n".join(body) + "\n"


def write_note(finding: dict[str, Any], vault_dir: str | Path) -> Path:
    """Write the rendered note into the vault. Idempotent by finding id (re-render
    overwrites — the DB is the truth, the note is a view). Creates the vault dir if
    it does not exist."""
    vault = Path(vault_dir)
    vault.mkdir(parents=True, exist_ok=True)
    path = vault / note_slug(finding)
    path.write_text(render_note(finding), encoding="utf-8")
    return path
