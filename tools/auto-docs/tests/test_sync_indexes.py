import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sync_indexes import (
    first_paragraph,
    parse_frontmatter,
    render_examples_index,
    render_skills_index,
    sync,
)


def test_parse_frontmatter_simple():
    text = "---\nname: foo\ndescription: a thing\n---\n\nbody\n"
    fm = parse_frontmatter(text)
    assert fm["name"] == "foo"
    assert fm["description"] == "a thing"


def test_parse_frontmatter_missing_returns_empty():
    assert parse_frontmatter("# just a heading\n") == {}


def test_first_paragraph_skips_frontmatter_and_h1():
    text = (
        "---\nname: x\n---\n\n"
        "# A Title\n\n"
        "First real paragraph.\n\n"
        "Second paragraph.\n"
    )
    assert first_paragraph(text) == "First real paragraph."


def test_render_skills_index_against_real_repo():
    repo = Path(__file__).resolve().parents[3]
    out = render_skills_index(repo)
    assert "# Skills" in out
    assert "resume" in out  # known skill
    assert "Auto-generated" in out


def test_render_examples_index_against_real_repo():
    repo = Path(__file__).resolve().parents[3]
    out = render_examples_index(repo)
    assert "# Examples" in out
    assert "sandbox" in out  # known examples subdir


def test_sync_creates_both_files_in_tmp(tmp_path: Path):
    # Tiny fixture repo
    (tmp_path / "skills" / "demo").mkdir(parents=True)
    (tmp_path / "skills" / "demo" / "SKILL.md").write_text(
        "---\nname: demo\ndescription: a demo skill\n---\n\nbody\n"
    )
    (tmp_path / "examples" / "ex-a").mkdir(parents=True)
    (tmp_path / "examples" / "ex-a" / "README.md").write_text(
        "# Example A\n\nDescribes example A.\n"
    )
    results = sync(tmp_path)
    skills_md = tmp_path / "docs" / "SKILLS.md"
    examples_md = tmp_path / "examples" / "README.md"
    assert results[skills_md]
    assert results[examples_md]
    assert "demo" in skills_md.read_text()
    assert "ex-a/" in examples_md.read_text()


def test_sync_idempotent(tmp_path: Path):
    (tmp_path / "skills" / "demo").mkdir(parents=True)
    (tmp_path / "skills" / "demo" / "SKILL.md").write_text(
        "---\nname: demo\ndescription: a demo skill\n---\n"
    )
    sync(tmp_path)
    results = sync(tmp_path)
    assert not any(results.values())  # second run is no-op
