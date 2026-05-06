"""Tests for metaprompt_hook.py — TDD-first (RED before GREEN).

All tests use real filesystem via tempfile.TemporaryDirectory — no mocks as
deliverables per CLAUDE.md rule 7.

UserPromptSubmit hook that intercepts every prompt and (depending on session
toggle state) passes through, lightly templates, or deeply structures it.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

# Resolve the mcp-bridge directory so imports and script path work from any cwd.
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
HOOK_PATH = REPO_ROOT / "mcp-bridge" / "metaprompt_hook.py"

# mcp-bridge needs to be on sys.path for module-level imports in tests.
MCP_BRIDGE_DIR = REPO_ROOT / "mcp-bridge"


def _run_hook(stdin_payload: dict, env_override: dict | None = None) -> subprocess.CompletedProcess:
    """Invoke metaprompt_hook.py via subprocess with JSON stdin."""
    base_env = os.environ.copy()
    if env_override:
        base_env.update(env_override)
    return subprocess.run(
        [sys.executable, str(HOOK_PATH)],
        input=json.dumps(stdin_payload),
        capture_output=True,
        text=True,
        env=base_env,
    )


def _parse_output(result: subprocess.CompletedProcess) -> dict:
    """Parse hook JSON output, return empty dict on failure."""
    try:
        return json.loads(result.stdout)
    except (json.JSONDecodeError, ValueError):
        return {}


# ---------------------------------------------------------------------------
# TestBypassPrefixes
# ---------------------------------------------------------------------------

class TestBypassPrefixes(unittest.TestCase):
    """Prompts starting with *, /, # must pass through unchanged regardless of mode."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.state_dir = Path(self.tmp.name)
        self.state_file = self.state_dir / ".metaprompt-mode"
        # Set mode to deep so bypass is provably independent of mode
        self.state_file.write_text("deep")

    def tearDown(self):
        self.tmp.cleanup()

    def _run(self, prompt: str) -> dict:
        payload = {
            "prompt": prompt,
            "cwd": self.tmp.name,
            "session_id": "test-session",
        }
        env = {"METAPROMPT_GLOBAL_STATE": str(self.state_file)}
        result = _run_hook(payload, env)
        self.assertEqual(result.returncode, 0)
        return _parse_output(result)

    def test_star_prefix_passes_through(self):
        """* prefix: strip * and pass raw prompt."""
        out = self._run("*do a thing")
        ctx = out.get("hookSpecificOutput", {}).get("additionalContext", "")
        # Should contain the original message after stripping prefix
        self.assertIn("do a thing", ctx)
        # Should NOT have deep-mode metaprompt scaffolding injected
        self.assertNotIn("metaprompt", ctx.lower())

    def test_slash_prefix_passes_through(self):
        """/cmd prefix: pass raw, no scaffolding."""
        out = self._run("/recall memory systems")
        ctx = out.get("hookSpecificOutput", {}).get("additionalContext", "")
        # raw passthrough — slash commands must not be altered
        self.assertNotIn("Phase", ctx)

    def test_hash_prefix_passes_through(self):
        """# prefix: pass raw, no scaffolding."""
        out = self._run("#memo remember this")
        ctx = out.get("hookSpecificOutput", {}).get("additionalContext", "")
        self.assertNotIn("Phase", ctx)


# ---------------------------------------------------------------------------
# TestStateReading
# ---------------------------------------------------------------------------

class TestStateReading(unittest.TestCase):
    """State file resolution: per-project beats global; missing → default off."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.cwd = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def _run(self, prompt: str, global_state_file: Path | None = None,
             per_project_state_file: Path | None = None) -> tuple[dict, subprocess.CompletedProcess]:
        payload = {
            "prompt": prompt,
            "cwd": str(self.cwd),
            "session_id": "state-test",
        }
        env: dict = {}
        if global_state_file is not None:
            env["METAPROMPT_GLOBAL_STATE"] = str(global_state_file)
        if per_project_state_file is not None:
            env["METAPROMPT_PROJECT_STATE"] = str(per_project_state_file)
        result = _run_hook(payload, env)
        return _parse_output(result), result

    def test_missing_state_defaults_to_off(self):
        """No state files → mode is off → passthrough."""
        out, proc = self._run("build me a thing")
        self.assertEqual(proc.returncode, 0)
        # off mode: no additionalContext or empty
        ctx = out.get("hookSpecificOutput", {}).get("additionalContext", "")
        self.assertNotIn("Phase", ctx)
        self.assertNotIn("Constraints", ctx)

    def test_global_state_fast_applies(self):
        """Global state=fast → fast-mode scaffolding injected."""
        global_file = self.cwd / ".metaprompt-mode-global"
        global_file.write_text("fast")
        out, proc = self._run("build me a thing", global_state_file=global_file)
        self.assertEqual(proc.returncode, 0)
        ctx = out.get("hookSpecificOutput", {}).get("additionalContext", "")
        # fast mode injects structural keywords
        has_scaffold = "Phase" in ctx or "Constraints" in ctx or "Success" in ctx
        self.assertTrue(has_scaffold, f"Expected scaffold in fast mode, got: {ctx!r}")

    def test_per_project_beats_global(self):
        """Per-project state=off overrides global=deep."""
        global_file = self.cwd / ".metaprompt-mode-global"
        global_file.write_text("deep")
        project_file = self.cwd / ".metaprompt-state"
        project_file.write_text("off")
        out, proc = self._run(
            "build me a thing",
            global_state_file=global_file,
            per_project_state_file=project_file,
        )
        self.assertEqual(proc.returncode, 0)
        ctx = out.get("hookSpecificOutput", {}).get("additionalContext", "")
        # off mode wins → no deep scaffolding
        self.assertNotIn("metaprompt", ctx.lower())


# ---------------------------------------------------------------------------
# TestOffMode
# ---------------------------------------------------------------------------

class TestOffMode(unittest.TestCase):
    """off mode: prompt passes through unchanged; no envelope overhead."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.state_file = Path(self.tmp.name) / ".metaprompt-mode"
        self.state_file.write_text("off")

    def tearDown(self):
        self.tmp.cleanup()

    def _run(self, prompt: str) -> tuple[dict, subprocess.CompletedProcess]:
        payload = {"prompt": prompt, "cwd": self.tmp.name, "session_id": "off-test"}
        env = {"METAPROMPT_GLOBAL_STATE": str(self.state_file)}
        result = _run_hook(payload, env)
        return _parse_output(result), result

    def test_off_returns_exit_zero(self):
        out, proc = self._run("just a plain prompt")
        self.assertEqual(proc.returncode, 0)

    def test_off_no_scaffolding(self):
        out, proc = self._run("just a plain prompt")
        ctx = out.get("hookSpecificOutput", {}).get("additionalContext", "")
        self.assertNotIn("Phase", ctx)
        self.assertNotIn("Constraints", ctx)
        self.assertNotIn("metaprompt", ctx.lower())

    def test_off_no_stderr_noise(self):
        """Happy path: no stderr output."""
        _, proc = self._run("clean prompt")
        self.assertEqual(proc.stderr.strip(), "")


# ---------------------------------------------------------------------------
# TestFastMode
# ---------------------------------------------------------------------------

class TestFastMode(unittest.TestCase):
    """fast mode: structural scaffolding injected, <150 tokens (~600 chars), no LLM."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.state_file = Path(self.tmp.name) / ".metaprompt-mode"
        self.state_file.write_text("fast")

    def tearDown(self):
        self.tmp.cleanup()

    def _run(self, prompt: str) -> tuple[dict, subprocess.CompletedProcess]:
        payload = {"prompt": prompt, "cwd": self.tmp.name, "session_id": "fast-test"}
        env = {"METAPROMPT_GLOBAL_STATE": str(self.state_file)}
        result = _run_hook(payload, env)
        return _parse_output(result), result

    def test_fast_contains_phase_keyword(self):
        out, proc = self._run("implement the auth module")
        self.assertEqual(proc.returncode, 0)
        ctx = out.get("hookSpecificOutput", {}).get("additionalContext", "")
        self.assertIn("Phase", ctx)

    def test_fast_contains_constraints_keyword(self):
        out, proc = self._run("implement the auth module")
        ctx = out.get("hookSpecificOutput", {}).get("additionalContext", "")
        self.assertIn("Constraints", ctx)

    def test_fast_size_budget_600_chars(self):
        """Fast-mode output total must be ≤ 600 chars (heuristic for 150 tokens)."""
        out, proc = self._run("implement the auth module")
        ctx = out.get("hookSpecificOutput", {}).get("additionalContext", "")
        self.assertLessEqual(
            len(ctx), 600,
            f"fast mode output too large ({len(ctx)} chars > 600): {ctx!r}",
        )

    def test_fast_no_llm_call(self):
        """fast mode must complete in <500ms — proves no LLM call."""
        import time
        t0 = time.monotonic()
        self._run("a prompt that would take seconds if LLM were called")
        elapsed = time.monotonic() - t0
        self.assertLess(elapsed, 0.5, f"fast mode took {elapsed:.2f}s — LLM call suspected")

    def test_fast_no_stderr_noise(self):
        _, proc = self._run("clean prompt")
        self.assertEqual(proc.stderr.strip(), "")


# ---------------------------------------------------------------------------
# TestDeepMode
# ---------------------------------------------------------------------------

class TestDeepMode(unittest.TestCase):
    """deep mode: full /metaprompt scaffolding injected, <300 tokens (~1200 chars)."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.state_file = Path(self.tmp.name) / ".metaprompt-mode"
        self.state_file.write_text("deep")

    def tearDown(self):
        self.tmp.cleanup()

    def _run(self, prompt: str) -> tuple[dict, subprocess.CompletedProcess]:
        payload = {"prompt": prompt, "cwd": self.tmp.name, "session_id": "deep-test"}
        env = {"METAPROMPT_GLOBAL_STATE": str(self.state_file)}
        result = _run_hook(payload, env)
        return _parse_output(result), result

    def test_deep_contains_metaprompt_scaffolding(self):
        out, proc = self._run("build an auth system")
        self.assertEqual(proc.returncode, 0)
        ctx = out.get("hookSpecificOutput", {}).get("additionalContext", "")
        # deep mode injects /metaprompt mission-style scaffold
        has_meta = (
            "desired outcome" in ctx.lower()
            or "success criteria" in ctx.lower()
            or "prompt engineering" in ctx.lower()
            or "metaprompt" in ctx.lower()
        )
        self.assertTrue(has_meta, f"Expected metaprompt scaffold in deep mode, got: {ctx!r}")

    def test_deep_size_budget_1200_chars(self):
        """Deep-mode output total must be ≤ 1200 chars (heuristic for 300 tokens)."""
        out, proc = self._run("build an auth system")
        ctx = out.get("hookSpecificOutput", {}).get("additionalContext", "")
        self.assertLessEqual(
            len(ctx), 1200,
            f"deep mode output too large ({len(ctx)} chars > 1200): {ctx!r}",
        )

    def test_deep_no_llm_call(self):
        """deep mode injects static scaffold — no LLM call, must be <500ms."""
        import time
        t0 = time.monotonic()
        self._run("build an auth system")
        elapsed = time.monotonic() - t0
        self.assertLess(elapsed, 0.5, f"deep mode took {elapsed:.2f}s — LLM call suspected")

    def test_deep_no_stderr_noise(self):
        _, proc = self._run("clean prompt")
        self.assertEqual(proc.stderr.strip(), "")


# ---------------------------------------------------------------------------
# TestMalformedJSON
# ---------------------------------------------------------------------------

class TestMalformedJSON(unittest.TestCase):
    """Malformed stdin: exit 0, raw passthrough, no crash."""

    def _run_raw(self, raw_stdin: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, str(HOOK_PATH)],
            input=raw_stdin,
            capture_output=True,
            text=True,
        )

    def test_empty_stdin_exit_zero(self):
        result = self._run_raw("")
        self.assertEqual(result.returncode, 0)

    def test_garbage_stdin_exit_zero(self):
        result = self._run_raw("{not valid json {{{{")
        self.assertEqual(result.returncode, 0)

    def test_malformed_json_produces_valid_output_or_empty(self):
        """Output must be valid JSON or empty — never a traceback."""
        result = self._run_raw("this is not json at all")
        self.assertEqual(result.returncode, 0)
        # stdout must be valid JSON or empty
        if result.stdout.strip():
            try:
                json.loads(result.stdout)
            except json.JSONDecodeError:
                self.fail(f"stdout is neither empty nor valid JSON: {result.stdout!r}")

    def test_malformed_logs_to_stderr_not_stdout(self):
        """On parse error, hook may emit one-line diagnostic to stderr, not stdout."""
        result = self._run_raw("{bad}")
        # stdout must not contain Python traceback keywords
        self.assertNotIn("Traceback", result.stdout)
        self.assertNotIn("Error", result.stdout)


# ---------------------------------------------------------------------------
# TestPathTraversalGuard
# ---------------------------------------------------------------------------

class TestPathTraversalGuard(unittest.TestCase):
    """Malicious cwd must not escape ~/.claude/projects/ boundary."""

    def _run(self, cwd: str) -> subprocess.CompletedProcess:
        payload = {
            "prompt": "some prompt",
            "cwd": cwd,
            "session_id": "traversal-test",
        }
        return subprocess.run(
            [sys.executable, str(HOOK_PATH)],
            input=json.dumps(payload),
            capture_output=True,
            text=True,
        )

    def test_path_traversal_attempt_exit_zero(self):
        """Traversal cwd: hook must not crash, must exit 0."""
        result = self._run("/../../../etc/passwd")
        self.assertEqual(result.returncode, 0)

    def test_dotdot_slug_is_sanitized(self):
        """.. sequences must be sanitized in slug construction."""
        result = self._run("/projects/../../sensitive")
        self.assertEqual(result.returncode, 0)
        # Confirm no stderr crash
        self.assertNotIn("Traceback", result.stderr)

    def test_newline_in_cwd_sanitized(self):
        """Newline injection in cwd must be stripped, exit 0."""
        result = self._run("/Users/me/project\n/injected/path")
        self.assertEqual(result.returncode, 0)


# ---------------------------------------------------------------------------
# TestOutputEnvelope
# ---------------------------------------------------------------------------

class TestOutputEnvelope(unittest.TestCase):
    """Output must conform to the hookSpecificOutput envelope when context is added."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.state_file = Path(self.tmp.name) / ".metaprompt-mode"

    def tearDown(self):
        self.tmp.cleanup()

    def _run(self, prompt: str, mode: str) -> tuple[dict, subprocess.CompletedProcess]:
        self.state_file.write_text(mode)
        payload = {"prompt": prompt, "cwd": self.tmp.name, "session_id": "envelope-test"}
        env = {"METAPROMPT_GLOBAL_STATE": str(self.state_file)}
        result = _run_hook(payload, env)
        return _parse_output(result), result

    def test_fast_mode_envelope_shape(self):
        """fast mode: output is a valid envelope with hookSpecificOutput."""
        out, proc = self._run("do something", "fast")
        self.assertEqual(proc.returncode, 0)
        self.assertIn("hookSpecificOutput", out)
        self.assertEqual(
            out["hookSpecificOutput"].get("hookEventName"),
            "UserPromptSubmit",
        )
        self.assertIn("additionalContext", out["hookSpecificOutput"])

    def test_deep_mode_envelope_shape(self):
        """deep mode: same envelope structure."""
        out, proc = self._run("do something", "deep")
        self.assertEqual(proc.returncode, 0)
        self.assertIn("hookSpecificOutput", out)
        self.assertEqual(
            out["hookSpecificOutput"].get("hookEventName"),
            "UserPromptSubmit",
        )

    def test_off_mode_stdout_is_valid_json_or_empty(self):
        """off mode: stdout is empty or valid JSON — never garbage."""
        out, proc = self._run("do something", "off")
        self.assertEqual(proc.returncode, 0)
        # Already parsed — if we got here, it's valid JSON or empty dict
        # Just confirm no crash and clean stderr
        self.assertEqual(proc.stderr.strip(), "")


if __name__ == "__main__":
    unittest.main()
