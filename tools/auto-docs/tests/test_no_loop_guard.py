import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from run_all import AUTO_PATHS, should_skip


def _init(path: Path) -> None:
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.email", "t@t.t"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=path, check=True)


def _commit(path: Path, files: dict[str, str], subject: str) -> None:
    for rel, content in files.items():
        full = path / rel
        full.parent.mkdir(parents=True, exist_ok=True)
        full.write_text(content)
    subprocess.run(["git", "add", "."], cwd=path, check=True)
    subprocess.run(["git", "commit", "-q", "-m", subject], cwd=path, check=True)


def test_skip_when_head_is_auto_sync(tmp_path: Path):
    _init(tmp_path)
    _commit(tmp_path, {"CHANGELOG.md": "a"}, "chore(docs): auto-sync after abc1234")
    skip, reason = should_skip(tmp_path)
    assert skip
    assert "auto-sync" in reason


def test_skip_when_head_changes_only_auto_paths(tmp_path: Path):
    _init(tmp_path)
    _commit(tmp_path, {"src/x.py": "x"}, "feat: real change")
    _commit(
        tmp_path,
        {"CHANGELOG.md": "a", "README.md": "b", "docs/SKILLS.md": "c"},
        "manual changelog tweak",
    )
    skip, _ = should_skip(tmp_path)
    assert skip


def test_no_skip_when_head_touches_source(tmp_path: Path):
    _init(tmp_path)
    _commit(tmp_path, {"src/x.py": "x", "CHANGELOG.md": "a"}, "feat: add module")
    skip, _ = should_skip(tmp_path)
    assert not skip


def test_skip_marker_in_subject_honored(tmp_path: Path):
    _init(tmp_path)
    _commit(tmp_path, {"src/x.py": "x"}, "feat: thing [skip auto-docs]")
    skip, reason = should_skip(tmp_path)
    assert skip


def test_auto_paths_covers_expected_set():
    assert AUTO_PATHS == {"CHANGELOG.md", "README.md", "docs/SKILLS.md", "examples/README.md"}
