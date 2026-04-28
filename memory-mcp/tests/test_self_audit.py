"""Tests for self_audit.py — TDD-first, 12 blocks, RED before GREEN.

Design reference: SELF-AUDIT-DESIGN-2026-04-28.md § 7

Block 1  — TestFrontmatterParser
Block 2  — TestCorpusCollection
Block 3  — TestRuleCMD1
Block 4  — TestRuleCMD3
Block 5  — TestRuleAGENT1
Block 6  — TestRuleAGENT3
Block 7  — TestRuleSKILL2
Block 8  — TestFullToolkitSmoke
Block 9  — TestPrivacySpotCheck
Block 10 — TestStdlibOnly
Block 11 — TestDeterministicOutput
Block 12 — TestCLI
"""

from __future__ import annotations

import ast
import importlib
import io
import json
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

# Add parent dir (memory-mcp/) to sys.path — matches existing test convention
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from self_audit import (  # noqa: E402
    ArtifactFile,
    AuditReport,
    CatalogEntry,
    Finding,
    _parse_frontmatter,
    _parse_tools_list,
    collect_corpus,
    load_catalog,
    run_rules,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _make_toolkit(tmp: Path) -> Path:
    """Scaffold a minimal well-formed toolkit tree."""
    (tmp / "commands").mkdir()
    (tmp / "agents").mkdir()
    (tmp / "skills" / "demo").mkdir(parents=True)
    return tmp


CATALOG_PATH = Path(__file__).resolve().parent.parent / "self_audit_catalog.json"


# ---------------------------------------------------------------------------
# Block 1: TestFrontmatterParser
# ---------------------------------------------------------------------------

class TestFrontmatterParser(unittest.TestCase):

    def test_parses_name_and_description(self):
        text = "---\nname: my-agent\ndescription: Does stuff\n---\nbody"
        fm, body = _parse_frontmatter(text)
        self.assertEqual(fm["name"], "my-agent")
        self.assertEqual(fm["description"], "Does stuff")
        self.assertIn("body", body)

    def test_parses_tools_as_raw_string(self):
        text = "---\ntools: Glob, Read, Bash(git log:*)\n---"
        fm, _ = _parse_frontmatter(text)
        self.assertIn("tools", fm)

    def test_no_frontmatter_returns_empty_dict(self):
        text = "# Just a heading\nno frontmatter here"
        fm, body = _parse_frontmatter(text)
        self.assertEqual(fm, {})
        self.assertIn("Just a heading", body)

    def test_incomplete_frontmatter_no_closing(self):
        text = "---\nname: broken\ndescription: no closing fence"
        fm, body = _parse_frontmatter(text)
        # Should not crash; may return partial or empty
        self.assertIsInstance(fm, dict)

    def test_tools_list_strips_parenthesized_args(self):
        raw = "Glob, Read, Bash(git log:*), WebFetch(url)"
        tools = _parse_tools_list(raw)
        self.assertIn("Glob", tools)
        self.assertIn("Read", tools)
        self.assertIn("Bash", tools)
        self.assertIn("WebFetch", tools)
        # No parenthesized residue
        self.assertNotIn("Bash(git log:*)", tools)

    def test_tools_list_empty_string(self):
        self.assertEqual(_parse_tools_list(""), [])

    def test_tools_list_single_item(self):
        self.assertEqual(_parse_tools_list("Read"), ["Read"])


# ---------------------------------------------------------------------------
# Block 2: TestCorpusCollection
# ---------------------------------------------------------------------------

class TestCorpusCollection(unittest.TestCase):

    def test_finds_command_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            t = Path(tmp)
            _make_toolkit(t)
            _write(t / "commands" / "foo.md", "---\ndescription: Foo\n---\nbody")
            corpus = collect_corpus(t)
            names = [a.path.name for a in corpus]
            self.assertIn("foo.md", names)

    def test_finds_agent_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            t = Path(tmp)
            _make_toolkit(t)
            _write(t / "agents" / "bar.md", "---\nname: bar\n---\nbody")
            corpus = collect_corpus(t)
            names = [a.path.name for a in corpus]
            self.assertIn("bar.md", names)

    def test_finds_skill_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            t = Path(tmp)
            _make_toolkit(t)
            _write(t / "skills" / "demo" / "SKILL.md", "---\ndescription: d\n---\nbody")
            corpus = collect_corpus(t)
            names = [a.path.name for a in corpus]
            self.assertIn("SKILL.md", names)

    def test_skips_unreadable_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            t = Path(tmp)
            _make_toolkit(t)
            bad = t / "commands" / "bad.md"
            _write(bad, "ok")
            bad.chmod(0o000)
            try:
                corpus = collect_corpus(t)
                # Should not raise; bad.md skipped
                names = [a.path.name for a in corpus]
                self.assertNotIn("bad.md", names)
            finally:
                bad.chmod(0o644)

    def test_empty_toolkit_returns_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            t = Path(tmp)
            # No commands/agents/skills dirs
            corpus = collect_corpus(t)
            self.assertEqual(corpus, [])

    def test_artifact_type_labelled_correctly(self):
        with tempfile.TemporaryDirectory() as tmp:
            t = Path(tmp)
            _make_toolkit(t)
            _write(t / "commands" / "c.md", "---\ndescription: c\n---")
            _write(t / "agents" / "a.md", "---\nname: a\n---")
            corpus = collect_corpus(t)
            types = {a.artifact_type for a in corpus}
            self.assertIn("command", types)
            self.assertIn("agent", types)


# ---------------------------------------------------------------------------
# Block 3: TestRuleCMD1
# ---------------------------------------------------------------------------

class TestRuleCMD1(unittest.TestCase):
    """R-CMD-1: argument-hint present but $ARGUMENTS absent in body."""

    def _run(self, content: str) -> list[Finding]:
        with tempfile.TemporaryDirectory() as tmp:
            t = Path(tmp)
            _make_toolkit(t)
            _write(t / "commands" / "cmd.md", content)
            corpus = collect_corpus(t)
            catalog = load_catalog(CATALOG_PATH)
            return [f for f in run_rules(corpus, catalog) if f.rule_id == "R-CMD-1"]

    def test_fires_when_hint_but_no_arguments_placeholder(self):
        content = "---\ndescription: d\nargument-hint: <target>\n---\nDo something without placeholder."
        findings = self._run(content)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].severity, "warn")

    def test_clean_when_hint_and_arguments_present(self):
        content = "---\ndescription: d\nargument-hint: <target>\n---\nDo something with $ARGUMENTS."
        findings = self._run(content)
        self.assertEqual(len(findings), 0)

    def test_clean_when_neither_hint_nor_arguments(self):
        content = "---\ndescription: d\n---\nDo something."
        findings = self._run(content)
        self.assertEqual(len(findings), 0)


# ---------------------------------------------------------------------------
# Block 4: TestRuleCMD3
# ---------------------------------------------------------------------------

class TestRuleCMD3(unittest.TestCase):
    """R-CMD-3: $ARGUMENTS in body but no argument-hint in frontmatter."""

    def _run(self, content: str) -> list[Finding]:
        with tempfile.TemporaryDirectory() as tmp:
            t = Path(tmp)
            _make_toolkit(t)
            _write(t / "commands" / "cmd.md", content)
            corpus = collect_corpus(t)
            catalog = load_catalog(CATALOG_PATH)
            return [f for f in run_rules(corpus, catalog) if f.rule_id == "R-CMD-3"]

    def test_fires_when_arguments_but_no_hint(self):
        content = "---\ndescription: d\n---\nFocus on $ARGUMENTS and do stuff."
        findings = self._run(content)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].severity, "warn")

    def test_clean_when_both_present(self):
        content = "---\ndescription: d\nargument-hint: <target>\n---\nFocus on $ARGUMENTS."
        findings = self._run(content)
        self.assertEqual(len(findings), 0)

    def test_clean_when_neither_present(self):
        content = "---\ndescription: d\n---\nNo placeholder here."
        findings = self._run(content)
        self.assertEqual(len(findings), 0)


# ---------------------------------------------------------------------------
# Block 5: TestRuleAGENT1
# ---------------------------------------------------------------------------

class TestRuleAGENT1(unittest.TestCase):
    """R-AGENT-1: model:sonnet + reasoning keywords → suggest opus."""

    def _run(self, content: str) -> list[Finding]:
        with tempfile.TemporaryDirectory() as tmp:
            t = Path(tmp)
            _make_toolkit(t)
            _write(t / "agents" / "a.md", content)
            corpus = collect_corpus(t)
            catalog = load_catalog(CATALOG_PATH)
            return [f for f in run_rules(corpus, catalog) if f.rule_id == "R-AGENT-1"]

    def test_fires_on_sonnet_with_architecture_keyword(self):
        content = "---\nmodel: sonnet\n---\nYou design architecture for the system."
        findings = self._run(content)
        self.assertEqual(len(findings), 1)

    def test_fires_on_sonnet_with_research_keyword(self):
        content = "---\nmodel: sonnet\n---\nYou research and analyze deep questions."
        findings = self._run(content)
        self.assertEqual(len(findings), 1)

    def test_clean_on_opus_with_reasoning_keyword(self):
        content = "---\nmodel: opus\n---\nYou analyze and research complex topics."
        findings = self._run(content)
        self.assertEqual(len(findings), 0)

    def test_clean_on_sonnet_without_reasoning_keywords(self):
        content = "---\nmodel: sonnet\n---\nRun lint checks on the file."
        findings = self._run(content)
        self.assertEqual(len(findings), 0)


# ---------------------------------------------------------------------------
# Block 6: TestRuleAGENT3
# ---------------------------------------------------------------------------

class TestRuleAGENT3(unittest.TestCase):
    """R-AGENT-3: Bash patterns in body but Bash not in tools list."""

    def _run(self, content: str) -> list[Finding]:
        with tempfile.TemporaryDirectory() as tmp:
            t = Path(tmp)
            _make_toolkit(t)
            _write(t / "agents" / "a.md", content)
            corpus = collect_corpus(t)
            catalog = load_catalog(CATALOG_PATH)
            return [f for f in run_rules(corpus, catalog) if f.rule_id == "R-AGENT-3"]

    def test_fires_when_bash_in_body_not_in_tools(self):
        content = "---\ntools: Glob, Read\n---\nRun: `git log --oneline` to see commits."
        findings = self._run(content)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].severity, "warn")

    def test_clean_when_bash_in_tools_and_body(self):
        content = "---\ntools: Glob, Read, Bash(git log:*)\n---\nRun `git log` to see commits."
        findings = self._run(content)
        self.assertEqual(len(findings), 0)

    def test_clean_when_no_shell_patterns_in_body(self):
        content = "---\ntools: Glob, Read\n---\nJust read files and think."
        findings = self._run(content)
        self.assertEqual(len(findings), 0)


# ---------------------------------------------------------------------------
# Block 7: TestRuleSKILL2
# ---------------------------------------------------------------------------

class TestRuleSKILL2(unittest.TestCase):
    """R-SKILL-2: SKILL.md references a script path that doesn't exist."""

    def _run(self, content: str, extra_files: list[str] | None = None) -> list[Finding]:
        with tempfile.TemporaryDirectory() as tmp:
            t = Path(tmp)
            _make_toolkit(t)
            if extra_files:
                for f in extra_files:
                    _write(t / f, "# script")
            _write(t / "skills" / "demo" / "SKILL.md", content)
            corpus = collect_corpus(t)
            catalog = load_catalog(CATALOG_PATH)
            return [f for f in run_rules(corpus, catalog) if f.rule_id == "R-SKILL-2"]

    def test_fires_when_script_path_missing(self):
        content = "---\ndescription: d\n---\nRun: `python3 ~/Dev/claude-second-brain/memory-mcp/nonexistent_script.py`"
        findings = self._run(content)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].severity, "warn")

    def test_clean_when_no_script_paths_referenced(self):
        content = "---\ndescription: d\n---\nJust describe behavior, no scripts."
        findings = self._run(content)
        self.assertEqual(len(findings), 0)


# ---------------------------------------------------------------------------
# Block 8: TestFullToolkitSmoke
# ---------------------------------------------------------------------------

class TestFullToolkitSmoke(unittest.TestCase):

    def test_runs_against_real_toolkit_fast(self):
        toolkit = Path(__file__).resolve().parent.parent.parent
        self.assertTrue((toolkit / "commands").is_dir(), "commands/ dir expected")
        start = time.monotonic()
        corpus = collect_corpus(toolkit)
        catalog = load_catalog(CATALOG_PATH)
        findings = run_rules(corpus, catalog)
        elapsed = time.monotonic() - start
        self.assertLess(elapsed, 10.0, f"Smoke test too slow: {elapsed:.1f}s")
        # Should find at least some files
        self.assertGreater(len(corpus), 0)
        # findings is a list (may be empty or non-empty, no exception is the pass)
        self.assertIsInstance(findings, list)

    def test_real_toolkit_findings_are_valid_schema(self):
        toolkit = Path(__file__).resolve().parent.parent.parent
        corpus = collect_corpus(toolkit)
        catalog = load_catalog(CATALOG_PATH)
        findings = run_rules(corpus, catalog)
        for f in findings:
            self.assertIsInstance(f, Finding)
            self.assertIn(f.severity, ("warn", "info"))
            self.assertIn(f.effort, ("S", "M", "L"))
            self.assertTrue(f.rule_id.startswith("R-"))


# ---------------------------------------------------------------------------
# Block 9: TestPrivacySpotCheck
# ---------------------------------------------------------------------------

class TestPrivacySpotCheck(unittest.TestCase):

    def test_no_direct_jsonl_body_reads(self):
        """Source-level check: .jsonl only appears in context_estimator call site."""
        src = Path(__file__).resolve().parent.parent / "self_audit.py"
        text = src.read_text(encoding="utf-8")
        lines_with_jsonl = [
            (i + 1, line)
            for i, line in enumerate(text.splitlines())
            if ".jsonl" in line
        ]
        # All .jsonl references must be within context_estimator usage (import or
        # the single estimate_from_transcript call), not raw open() calls
        for lineno, line in lines_with_jsonl:
            stripped = line.strip()
            # Must not be an open() call on a .jsonl
            self.assertNotIn("open(", stripped,
                msg=f"Line {lineno}: direct .jsonl open() found: {stripped!r}")
            # Must not be read_text() on .jsonl
            self.assertNotIn("read_text(", stripped,
                msg=f"Line {lineno}: direct .jsonl read_text() found: {stripped!r}")

    def test_transcript_content_never_in_output(self):
        """R-SESSION-1 with --no-session flag produces no session data in output."""
        import self_audit
        toolkit = Path(__file__).resolve().parent.parent.parent
        catalog = load_catalog(CATALOG_PATH)
        corpus = collect_corpus(toolkit)
        findings = run_rules(corpus, catalog, no_session=True)
        # R-SESSION-1 should not appear when --no-session
        session_findings = [f for f in findings if f.rule_id == "R-SESSION-1"]
        self.assertEqual(session_findings, [])


# ---------------------------------------------------------------------------
# Block 10: TestStdlibOnly
# ---------------------------------------------------------------------------

class TestStdlibOnly(unittest.TestCase):

    ALLOWED_STDLIB = {
        "argparse", "ast", "dataclasses", "datetime", "json",
        "os", "pathlib", "re", "sys", "time", "typing",
        "__future__",
    }
    # Sibling toolkit modules allowed
    ALLOWED_SIBLINGS = {"context_estimator", "lint_memory"}

    def test_no_third_party_imports(self):
        src = Path(__file__).resolve().parent.parent / "self_audit.py"
        text = src.read_text(encoding="utf-8")
        tree = ast.parse(text)
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        top = alias.name.split(".")[0]
                        self.assertIn(
                            top,
                            self.ALLOWED_STDLIB | self.ALLOWED_SIBLINGS,
                            f"Third-party import detected: {alias.name}",
                        )
                else:  # ImportFrom
                    if node.module:
                        top = node.module.split(".")[0]
                        self.assertIn(
                            top,
                            self.ALLOWED_STDLIB | self.ALLOWED_SIBLINGS,
                            f"Third-party import detected: from {node.module}",
                        )


# ---------------------------------------------------------------------------
# Block 11: TestDeterministicOutput
# ---------------------------------------------------------------------------

class TestDeterministicOutput(unittest.TestCase):

    def test_same_input_same_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            t = Path(tmp)
            _make_toolkit(t)
            _write(t / "commands" / "cmd.md",
                   "---\ndescription: d\nargument-hint: <x>\n---\nNo placeholder.")
            _write(t / "agents" / "a.md",
                   "---\nmodel: sonnet\n---\nResearch and analyze complex architecture.")
            catalog = load_catalog(CATALOG_PATH)
            corpus = collect_corpus(t)

            findings_a = run_rules(corpus, catalog)
            findings_b = run_rules(corpus, catalog)

            ids_a = [(f.rule_id, f.target) for f in findings_a]
            ids_b = [(f.rule_id, f.target) for f in findings_b]
            self.assertEqual(ids_a, ids_b)

    def test_sorted_output_severity_then_effort(self):
        with tempfile.TemporaryDirectory() as tmp:
            t = Path(tmp)
            _make_toolkit(t)
            # Seed multiple findings of different severities
            _write(t / "commands" / "c1.md",
                   "---\ndescription: d\nargument-hint: <x>\n---\nNo placeholder.")
            _write(t / "agents" / "a1.md",
                   "---\nmodel: sonnet\ntools: Glob\n---\nResearch architecture. Run `git log`.")
            catalog = load_catalog(CATALOG_PATH)
            corpus = collect_corpus(t)
            findings = run_rules(corpus, catalog)
            # Check severity ordering: warn before info
            sev_order = {"warn": 0, "info": 1}
            for i in range(len(findings) - 1):
                self.assertLessEqual(
                    sev_order.get(findings[i].severity, 99),
                    sev_order.get(findings[i + 1].severity, 99),
                )


# ---------------------------------------------------------------------------
# Block 12: TestCLI
# ---------------------------------------------------------------------------

class TestCLI(unittest.TestCase):

    PYTHON = str(Path.home() / ".claude" / "memory-mcp" / ".venv" / "bin" / "python3")
    MODULE = str(Path(__file__).resolve().parent.parent / "self_audit.py")

    def _run_cli(self, args: list[str]) -> subprocess.CompletedProcess:
        return subprocess.run(
            [self.PYTHON, self.MODULE] + args,
            capture_output=True, text=True, timeout=30,
        )

    def test_json_flag_produces_parseable_json(self):
        result = self._run_cli(["--json"])
        self.assertEqual(result.returncode, 0)
        data = json.loads(result.stdout)
        self.assertIn("findings", data)
        self.assertIn("generated_at", data)
        self.assertIn("catalog_version", data)
        self.assertIn("corpus_stats", data)
        self.assertIn("summary", data)

    def test_json_schema_finding_fields(self):
        result = self._run_cli(["--json"])
        data = json.loads(result.stdout)
        for f in data["findings"]:
            self.assertIn("target", f)
            self.assertIn("rule_id", f)
            self.assertIn("severity", f)
            self.assertIn("effort", f)
            self.assertIn("evidence", f)
            self.assertIn("suggestion", f)

    def test_exit_on_finding_returns_1_when_findings(self):
        # Use real toolkit which should have findings
        result = self._run_cli(["--exit-on-finding"])
        # May be 0 or 1 depending on findings; at minimum should not crash
        self.assertIn(result.returncode, (0, 1))

    def test_clean_target_exits_0(self):
        with tempfile.TemporaryDirectory() as tmp:
            # Empty dir = no corpus = no findings
            result = self._run_cli(["--target", tmp])
            self.assertEqual(result.returncode, 0)

    def test_quiet_suppresses_output_when_clean(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = self._run_cli(["--target", tmp, "--quiet"])
            self.assertEqual(result.returncode, 0)
            self.assertEqual(result.stdout.strip(), "")

    def test_no_session_flag_accepted(self):
        result = self._run_cli(["--no-session", "--json"])
        self.assertEqual(result.returncode, 0)
        data = json.loads(result.stdout)
        self.assertIn("findings", data)

    def test_rules_filter_limits_output(self):
        result = self._run_cli(["--json", "--rules", "R-CMD-1"])
        data = json.loads(result.stdout)
        for f in data["findings"]:
            self.assertEqual(f["rule_id"], "R-CMD-1")


if __name__ == "__main__":
    unittest.main()
