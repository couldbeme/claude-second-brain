"""Tests for bridge_append.py — TDD-first (RED before GREEN).

All tests use real filesystem via tempfile.TemporaryDirectory and real subprocess
invocations — no mocks as deliverables per CLAUDE.md rule 7.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

# Resolve the memory-mcp directory so imports and script path work from any cwd.
SCRIPTS_DIR = Path(__file__).resolve().parent.parent
BRIDGE_APPEND_PATH = SCRIPTS_DIR / "bridge_append.py"

# All happy-path tests use tempdirs within _PROJECTS_ROOT so the path-traversal
# guard accepts them.  The guard is intentional: only paths under
# ~/.claude/projects/ are trusted for explicit --memory-dir overrides.
_PROJECTS_ROOT = Path.home() / ".claude" / "projects"

# Regex matching a valid bridge entry line.
_ENTRY_RE = re.compile(
    r"^\[(?P<timestamp>\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z)\]\s+"
    r"\[(?P<type>[A-Z\-]+)\]\s+"
    r"(?P<payload>.*)$"
)


def _run(args: list[str], env_override: dict | None = None, **kwargs) -> subprocess.CompletedProcess:
    """Invoke bridge_append.py via subprocess with optional env override."""
    base_env = os.environ.copy()
    if env_override:
        base_env.update(env_override)
    return subprocess.run(
        [sys.executable, str(BRIDGE_APPEND_PATH)] + args,
        capture_output=True,
        env=base_env,
        **kwargs,
    )


# ---------------------------------------------------------------------------
# TestCliInvocation
# ---------------------------------------------------------------------------


class TestCliInvocation(unittest.TestCase):
    """Happy-path: DECISION type appended to session_bridge.md in a tempdir."""

    def test_creates_session_bridge_and_exits_zero(self):
        _PROJECTS_ROOT.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=_PROJECTS_ROOT) as tmp:
            memory_dir = Path(tmp) / "memory"
            memory_dir.mkdir()
            result = _run(
                [
                    "--memory-dir", str(memory_dir),
                    "DECISION",
                    "use TDD | WHY: quality | REJECTED: skip",
                ],
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            bridge = memory_dir / "session_bridge.md"
            self.assertTrue(bridge.exists(), "session_bridge.md not created")
            content = bridge.read_text()
            lines = [l for l in content.splitlines() if l.strip()]
            self.assertEqual(len(lines), 1)
            m = _ENTRY_RE.match(lines[0])
            self.assertIsNotNone(m, f"Line did not match entry format: {lines[0]!r}")
            self.assertEqual(m.group("type"), "DECISION")
            self.assertIn("use TDD", m.group("payload"))


# ---------------------------------------------------------------------------
# TestInvalidTypeRejected
# ---------------------------------------------------------------------------


class TestInvalidTypeRejected(unittest.TestCase):
    """Unknown entry types must be rejected; no file should be created."""

    def test_invalid_type_exits_one(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = _run(["--memory-dir", tmp, "JUNK_TYPE", "some payload"])
            self.assertEqual(result.returncode, 1, result.stderr)

    def test_invalid_type_does_not_create_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            _run(["--memory-dir", tmp, "JUNK_TYPE", "some payload"])
            bridge = Path(tmp) / "session_bridge.md"
            self.assertFalse(bridge.exists())


# ---------------------------------------------------------------------------
# TestPathTraversalGuard
# ---------------------------------------------------------------------------


class TestPathTraversalGuard(unittest.TestCase):
    """--memory-dir pointing outside _PROJECTS_ROOT must NOT write there.
    Per bridge_append.py spec: falls back to _PROJECTS_ROOT/unknown/memory/.
    """

    def test_does_not_write_to_etc(self):
        result = _run(["--memory-dir", "/etc", "DECISION", "should not land in /etc"])
        # Either exits 1 OR falls back — /etc/session_bridge.md must NOT exist.
        self.assertFalse(
            Path("/etc/session_bridge.md").exists(),
            "/etc/session_bridge.md should never be written",
        )

    def test_falls_back_or_exits_nonzero(self):
        result = _run(["--memory-dir", "/etc", "DECISION", "fallback test"])
        # Acceptable outcomes: exit 0 with fallback write, or exit 1 (explicit reject).
        self.assertIn(result.returncode, (0, 1))


# ---------------------------------------------------------------------------
# TestPayloadIsCapped
# ---------------------------------------------------------------------------


class TestPayloadIsCapped(unittest.TestCase):
    """2000-char payload must be capped to ≤500 chars in the written file."""

    def test_payload_capped_at_500(self):
        long_payload = "A" * 2000
        _PROJECTS_ROOT.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=_PROJECTS_ROOT) as tmp:
            memory_dir = Path(tmp) / "memory"
            memory_dir.mkdir()
            result = _run(["--memory-dir", str(memory_dir), "INFLIGHT", long_payload])
            self.assertEqual(result.returncode, 0, result.stderr)
            bridge = memory_dir / "session_bridge.md"
            content = bridge.read_text()
            lines = [l for l in content.splitlines() if l.strip()]
            self.assertEqual(len(lines), 1)
            m = _ENTRY_RE.match(lines[0])
            self.assertIsNotNone(m)
            self.assertLessEqual(len(m.group("payload")), 500)


# ---------------------------------------------------------------------------
# TestNewlineStripped
# ---------------------------------------------------------------------------


class TestNewlineStripped(unittest.TestCase):
    """Payloads with embedded newlines must produce exactly one entry line."""

    def test_embedded_newline_produces_one_line(self):
        # Shell-level: pass the payload as a single arg with a literal newline replaced
        # by a space (shell strips newlines); we test via the Python arg directly.
        payload = "line one\nline two\nline three"
        _PROJECTS_ROOT.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=_PROJECTS_ROOT) as tmp:
            memory_dir = Path(tmp) / "memory"
            memory_dir.mkdir()
            result = _run(["--memory-dir", str(memory_dir), "VOICE", payload])
            self.assertEqual(result.returncode, 0, result.stderr)
            bridge = memory_dir / "session_bridge.md"
            content = bridge.read_text()
            non_empty = [l for l in content.splitlines() if l.strip()]
            self.assertEqual(len(non_empty), 1, f"Expected 1 line, got: {non_empty}")


# ---------------------------------------------------------------------------
# TestCwdSlugDerivation
# ---------------------------------------------------------------------------


class TestCwdSlugDerivation(unittest.TestCase):
    """Explicit --memory-dir override must write the file to that directory."""

    def test_explicit_memory_dir_override_works(self):
        # We simulate a valid _PROJECTS_ROOT-relative path by using
        # ~/.claude/projects as root and creating a subdirectory under it.
        projects_root = Path.home() / ".claude" / "projects"
        with tempfile.TemporaryDirectory(dir=projects_root) as tmp:
            memory_dir = Path(tmp) / "memory"
            memory_dir.mkdir(parents=True, exist_ok=True)
            result = _run(["--memory-dir", str(memory_dir), "THREAD-OPEN", "t1 | desc"])
            self.assertEqual(result.returncode, 0, result.stderr)
            bridge = memory_dir / "session_bridge.md"
            self.assertTrue(bridge.exists(), "session_bridge.md not found in explicit --memory-dir")


# ---------------------------------------------------------------------------
# TestStdoutSilent
# ---------------------------------------------------------------------------


class TestStdoutSilent(unittest.TestCase):
    """Successful invocations must produce no stdout (hook-friendly)."""

    def test_stdout_empty_on_success(self):
        _PROJECTS_ROOT.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=_PROJECTS_ROOT) as tmp:
            memory_dir = Path(tmp) / "memory"
            memory_dir.mkdir()
            result = _run(["--memory-dir", str(memory_dir), "THREAD-CLOSE", "t1"])
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout, b"")

    def test_stdout_empty_for_all_valid_types(self):
        valid_types = ["DECISION", "THREAD-OPEN", "THREAD-CLOSE", "INFLIGHT", "VOICE", "PERSONA"]
        _PROJECTS_ROOT.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=_PROJECTS_ROOT) as tmp:
            memory_dir = Path(tmp) / "memory"
            memory_dir.mkdir()
            for entry_type in valid_types:
                result = _run(["--memory-dir", str(memory_dir), entry_type, "test payload"])
                self.assertEqual(result.returncode, 0, f"{entry_type} exited nonzero: {result.stderr}")
                self.assertEqual(result.stdout, b"", f"{entry_type} produced stdout: {result.stdout!r}")


if __name__ == "__main__":
    unittest.main()
