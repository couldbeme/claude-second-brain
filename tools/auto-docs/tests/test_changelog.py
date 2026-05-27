import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from changelog import (
    UNRELEASED_HEADING,
    classify,
    generate,
    render_unreleased,
    replace_unreleased,
)


def test_classify_groups_by_cc_type():
    subjects = [
        "feat(audit): add new skill",
        "fix(memory): handle missing index",
        "chore: bump deps",
        "freeform subject without prefix",
        "docs: update README",
    ]
    g = classify(subjects)
    assert len(g["feat"]) == 1 and "audit" in g["feat"][0]
    assert len(g["fix"]) == 1 and "memory" in g["fix"][0]
    assert len(g["chore"]) == 1
    assert len(g["docs"]) == 1
    assert len(g["other"]) == 1


def test_classify_strips_auto_sync_commits():
    subjects = [
        "feat: thing",
        "chore(docs): auto-sync after abc1234",
        "chore(docs): auto-sync after def5678",
    ]
    g = classify(subjects)
    assert len(g["feat"]) == 1
    assert sum(len(v) for v in g.values()) == 1  # only the feat survives


def test_render_empty_groups_yields_no_changes_placeholder():
    out = render_unreleased({k: [] for k in ["feat", "fix", "other"]})
    assert UNRELEASED_HEADING in out
    assert "No changes since last release" in out


def test_render_groups_in_canonical_order():
    g = {
        "feat": ["a"],
        "fix": ["b"],
        "chore": ["c"],
        "other": [],
        "docs": [],
        "perf": [],
        "refactor": [],
        "test": [],
        "build": [],
        "ci": [],
        "style": [],
    }
    out = render_unreleased(g)
    assert out.index("### Added") < out.index("### Fixed") < out.index("### Chore")


def test_replace_unreleased_swaps_existing_block():
    existing = (
        "# Changelog\n\n## [Unreleased]\n\n### Added\n- old\n\n## [1.0.0] - 2025-01-01\n\n### Added\n- v1 thing\n"
    )
    new_block = "## [Unreleased]\n\n### Added\n- new\n"
    out = replace_unreleased(existing, new_block)
    assert "- new" in out
    assert "- old" not in out
    assert "- v1 thing" in out  # prior release untouched


def test_replace_unreleased_inserts_when_missing():
    existing = "# Changelog\n\n## [1.0.0] - 2025-01-01\n\n### Added\n- v1 thing\n"
    new_block = "## [Unreleased]\n\n### Added\n- new\n"
    out = replace_unreleased(existing, new_block)
    assert out.index("## [Unreleased]") < out.index("## [1.0.0]")


def _init_tmp_repo(path: Path, subjects: list[str]) -> None:
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.email", "t@t.t"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=path, check=True)
    for i, s in enumerate(subjects):
        (path / f"f{i}.txt").write_text(str(i))
        subprocess.run(["git", "add", "."], cwd=path, check=True)
        subprocess.run(["git", "commit", "-q", "-m", s], cwd=path, check=True)


def test_generate_idempotent(tmp_path: Path):
    _init_tmp_repo(tmp_path, ["feat: a", "fix: b"])
    p, changed1 = generate(tmp_path)
    assert changed1
    _, changed2 = generate(tmp_path)
    assert not changed2  # idempotent


def test_generate_filters_merge_commits(tmp_path: Path):
    _init_tmp_repo(tmp_path, ["feat: base"])
    # Create a branch, commit, then merge with --no-ff so a merge commit exists.
    subprocess.run(["git", "checkout", "-q", "-b", "side"], cwd=tmp_path, check=True)
    (tmp_path / "side.txt").write_text("x")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "feat: side"], cwd=tmp_path, check=True)
    subprocess.run(["git", "checkout", "-q", "main"], cwd=tmp_path, check=True)
    subprocess.run(
        ["git", "merge", "--no-ff", "-q", "-m", "Merge branch 'side'", "side"],
        cwd=tmp_path,
        check=True,
    )
    p, _ = generate(tmp_path)
    body = p.read_text()
    assert "Merge branch" not in body
    assert "side" in body  # the real feat: side commit is included
