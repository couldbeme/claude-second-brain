import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from readme_stamp import END, START, build_block, count_markdown, insert_or_replace, stamp


def test_build_block_contains_required_fields():
    out = build_block("2026-05-20", 7, 32, ["feat: a", "fix: b"])
    assert START in out and END in out
    assert "2026-05-20" in out
    assert "Skills: 7" in out
    assert "Commands: 32" in out
    assert "feat: a" in out
    assert "fix: b" in out


def test_build_block_redacts_secrets_in_recent():
    out = build_block("2026-05-20", 1, 1, ["feat: AKIAIOSFODNN7EXAMPLE leaked"])
    assert "AKIA" not in out
    assert "<REDACTED-aws-access-key>" in out


def test_insert_when_no_block_appends_after_h1():
    content = "# Title\n\nSome prose here.\n"
    block = f"{START}\nstamp\n{END}"
    out = insert_or_replace(content, block)
    assert out.index("# Title") < out.index(START) < out.index("Some prose here")


def test_replace_existing_block_preserves_prose():
    content = (
        "# Title\n\n"
        f"{START}\nold\n{END}\n\n"
        "Important prose here.\n"
    )
    new = f"{START}\nnew\n{END}"
    out = insert_or_replace(content, new)
    assert "old" not in out
    assert "new" in out
    assert "Important prose here." in out


def test_count_markdown_counts_skill_dirs_and_command_files(tmp_path: Path):
    (tmp_path / "commands").mkdir()
    (tmp_path / "commands" / "a.md").write_text("a")
    (tmp_path / "commands" / "b.md").write_text("b")
    (tmp_path / "skills").mkdir()
    (tmp_path / "skills" / "s1").mkdir()
    (tmp_path / "skills" / "s1" / "SKILL.md").write_text("s1")
    (tmp_path / "skills" / "s2").mkdir()
    (tmp_path / "skills" / "s2" / "SKILL.md").write_text("s2")
    assert count_markdown(tmp_path / "commands") == 2
    assert count_markdown(tmp_path / "skills") == 2


def _init_repo(path: Path) -> None:
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.email", "t@t.t"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=path, check=True)


def test_stamp_idempotent(tmp_path: Path):
    _init_repo(tmp_path)
    (tmp_path / "README.md").write_text("# Project\n\nProse.\n")
    (tmp_path / "f.txt").write_text("x")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "feat: init"], cwd=tmp_path, check=True)
    _, changed1 = stamp(tmp_path, today="2026-05-20")
    assert changed1
    _, changed2 = stamp(tmp_path, today="2026-05-20")
    assert not changed2  # idempotent same day
