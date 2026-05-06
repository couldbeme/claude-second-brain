"""Tests for whats_new_check.py — TDD-first, mirrors test_self_audit.py shape.

Block 1  — TestCategorize           (bucket regexes)
Block 2  — TestExtractBullets        (markdown parsing)
Block 3  — TestStateLoadSave         (state file round-trip + atomic write)
Block 4  — TestStateMalformed        (corrupt state surfaces, doesn't overwrite)
Block 5  — TestFetchHTTPCases        (200, 304, 403, 5xx, offline, malformed)
Block 6  — TestDiffReleases          (new vs seen)
Block 7  — TestBuildBuckets          (release-body grouping)
Block 8  — TestFormatOutputs         (text / markdown / json)
Block 9  — TestBuildReport           (orchestration with mocks)
Block 10 — TestCLI                   (argparse + main)
Block 11 — TestStdlibOnly            (no third-party imports)
Block 12 — TestSeenReleasesCap       (FIFO rotation at 200)
"""

from __future__ import annotations

import ast
import io
import json
import sys
import tempfile
import unittest
import urllib.error
from dataclasses import asdict
from pathlib import Path
from unittest.mock import patch

# Add parent dir (memory-mcp/) to sys.path — matches existing test convention
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from whats_new_check import (  # noqa: E402
    BUCKET_ORDER,
    DEFAULT_API_URL,
    SCHEMA_VERSION,
    SEEN_RELEASES_CAP,
    DiffReport,
    FetchResult,
    ReleaseEntry,
    State,
    build_buckets,
    build_report,
    categorize_bullet,
    diff_releases,
    extract_bullets,
    fetch_releases,
    format_json,
    format_markdown,
    format_text,
    load_state,
    main,
    save_state,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class _FakeResp:
    """Mimics urllib's response context manager."""
    def __init__(self, body: bytes = b"[]", status: int = 200, etag: str = ""):
        self._body = body
        self.status = status
        self.headers = {"ETag": etag} if etag else {}

    def read(self) -> bytes:
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def _make_opener(resp_or_exc):
    """Return a callable matching urlopen(req, timeout=...) signature."""
    def _opener(req, timeout=None):
        if isinstance(resp_or_exc, Exception):
            raise resp_or_exc
        return resp_or_exc
    return _opener


# ---------------------------------------------------------------------------
# Block 1: TestCategorize
# ---------------------------------------------------------------------------

class TestCategorize(unittest.TestCase):

    def test_hooks_bucket(self):
        for s in [
            "Added PreCompact hook support",
            "New UserPromptSubmit event",
            "PostToolUse fires on tool result",
            "Fixed Stop hook regression",
        ]:
            with self.subTest(s=s):
                self.assertEqual(categorize_bullet(s), "Hooks")

    def test_skills_bucket(self):
        self.assertEqual(categorize_bullet("Added new skill loader"), "Skills")
        self.assertEqual(categorize_bullet("SKILL.md frontmatter validated"), "Skills")

    def test_mcp_bucket(self):
        self.assertEqual(categorize_bullet("New MCP server discovery"), "MCP")
        self.assertEqual(categorize_bullet("mcp__memory__save tool exposed"), "MCP")

    def test_slash_commands_bucket(self):
        self.assertEqual(categorize_bullet("New slash command /test"), "Slash Commands")
        self.assertEqual(categorize_bullet("/foo command added"), "Slash Commands")

    def test_settings_bucket(self):
        self.assertEqual(categorize_bullet("settings.json now supports X"), "Settings")
        self.assertEqual(categorize_bullet("config flag for Y"), "Settings")

    def test_model_bucket(self):
        self.assertEqual(categorize_bullet("Default model now claude-opus-4-7"), "Model")
        self.assertEqual(categorize_bullet("Sonnet 4.6 available"), "Model")

    def test_cli_bucket(self):
        self.assertEqual(categorize_bullet("Added --plugin-url flag"), "CLI")
        self.assertEqual(categorize_bullet("claude --help redesigned"), "CLI")

    def test_misc_fallback(self):
        self.assertEqual(categorize_bullet("Fixed a totally unrelated bug"), "Misc")
        self.assertEqual(categorize_bullet(""), "Misc")

    def test_first_match_wins(self):
        # Bullet mentioning both hook and skill → Hooks (defined first in BUCKET_PATTERNS)
        self.assertEqual(
            categorize_bullet("New hook for skills"),
            "Hooks",
        )


# ---------------------------------------------------------------------------
# Block 2: TestExtractBullets
# ---------------------------------------------------------------------------

class TestExtractBullets(unittest.TestCase):

    def test_simple_bullets(self):
        body = "## What's changed\n- First\n- Second\n- Third"
        self.assertEqual(extract_bullets(body), ["First", "Second", "Third"])

    def test_asterisk_bullets(self):
        body = "* one\n* two"
        self.assertEqual(extract_bullets(body), ["one", "two"])

    def test_empty_body(self):
        self.assertEqual(extract_bullets(""), [])
        self.assertEqual(extract_bullets("no bullets here"), [])

    def test_indented_bullets(self):
        body = "  - indented one\n  - indented two"
        self.assertEqual(extract_bullets(body), ["indented one", "indented two"])

    def test_bullet_with_inline_code(self):
        body = "- Added `--flag` to CLI"
        self.assertEqual(extract_bullets(body), ["Added `--flag` to CLI"])


# ---------------------------------------------------------------------------
# Block 3: TestStateLoadSave
# ---------------------------------------------------------------------------

class TestStateLoadSave(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "state.json"

    def tearDown(self):
        self.tmp.cleanup()

    def test_load_missing_returns_default(self):
        state = load_state(self.path)
        self.assertEqual(state.schema_version, SCHEMA_VERSION)
        self.assertEqual(state.seen_releases, [])
        self.assertEqual(state.last_etag, "")

    def test_save_then_load_roundtrip(self):
        original = State(
            last_checked_at="2026-05-06T12:00:00Z",
            last_checked_version="v2.1.131",
            last_etag='W/"abc123"',
            seen_releases=[{"tag": "v2.1.131", "published_at": "2026-05-05T00:00:00Z"}],
        )
        save_state(self.path, original)
        loaded = load_state(self.path)
        self.assertEqual(loaded.last_checked_version, "v2.1.131")
        self.assertEqual(loaded.last_etag, 'W/"abc123"')
        self.assertEqual(len(loaded.seen_releases), 1)

    def test_save_creates_parent_dirs(self):
        nested = Path(self.tmp.name) / "a" / "b" / "c" / "state.json"
        save_state(nested, State())
        self.assertTrue(nested.exists())

    def test_save_atomic_no_partial_on_failure(self):
        # Save a good state first
        good = State(last_checked_version="v1")
        save_state(self.path, good)
        # Saving another state should leave the file readable throughout
        save_state(self.path, State(last_checked_version="v2"))
        loaded = load_state(self.path)
        self.assertEqual(loaded.last_checked_version, "v2")


# ---------------------------------------------------------------------------
# Block 4: TestStateMalformed
# ---------------------------------------------------------------------------

class TestStateMalformed(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "corrupt.json"

    def tearDown(self):
        self.tmp.cleanup()

    def test_malformed_json_raises_value_error(self):
        self.path.write_text("{not valid json", encoding="utf-8")
        with self.assertRaises(ValueError):
            load_state(self.path)

    def test_malformed_state_not_overwritten_silently(self):
        self.path.write_text("garbage", encoding="utf-8")
        with self.assertRaises(ValueError):
            load_state(self.path)
        # File contents must be unchanged
        self.assertEqual(self.path.read_text(encoding="utf-8"), "garbage")


# ---------------------------------------------------------------------------
# Block 5: TestFetchHTTPCases
# ---------------------------------------------------------------------------

class TestFetchHTTPCases(unittest.TestCase):

    def test_200_ok_parses_releases(self):
        payload = json.dumps([
            {
                "tag_name": "v2.1.131",
                "published_at": "2026-05-05T00:00:00Z",
                "body": "- Added foo\n- Fixed bar",
                "html_url": "https://...",
            },
            {
                "tag_name": "v2.1.130",
                "published_at": "2026-05-04T00:00:00Z",
                "body": "",
            },
        ]).encode()
        resp = _FakeResp(body=payload, etag='W/"xyz"')
        result = fetch_releases(opener=_make_opener(resp))
        self.assertEqual(result.status, "ok")
        self.assertEqual(result.etag, 'W/"xyz"')
        self.assertEqual(len(result.releases), 2)
        self.assertEqual(result.releases[0].tag, "v2.1.131")

    def test_304_not_modified_via_status(self):
        resp = _FakeResp(status=304)
        result = fetch_releases(opener=_make_opener(resp))
        self.assertEqual(result.status, "not_modified")

    def test_304_not_modified_via_httperror(self):
        err = urllib.error.HTTPError(
            url="x", code=304, msg="Not Modified", hdrs=None, fp=None,
        )
        result = fetch_releases(opener=_make_opener(err))
        self.assertEqual(result.status, "not_modified")

    def test_403_rate_limit(self):
        # Build a minimal HTTPError; headers are accessed via `.headers`
        err = urllib.error.HTTPError(
            url="x", code=403, msg="rate", hdrs=None, fp=None,
        )
        result = fetch_releases(opener=_make_opener(err))
        self.assertEqual(result.status, "rate_limited")

    def test_500_upstream_error(self):
        err = urllib.error.HTTPError(
            url="x", code=500, msg="server", hdrs=None, fp=None,
        )
        result = fetch_releases(opener=_make_opener(err))
        self.assertEqual(result.status, "upstream_error")

    def test_offline_url_error(self):
        err = urllib.error.URLError("connection refused")
        result = fetch_releases(opener=_make_opener(err))
        self.assertEqual(result.status, "offline")

    def test_offline_timeout(self):
        result = fetch_releases(opener=_make_opener(TimeoutError("slow")))
        self.assertEqual(result.status, "offline")

    def test_malformed_json(self):
        resp = _FakeResp(body=b"{not json")
        result = fetch_releases(opener=_make_opener(resp))
        self.assertEqual(result.status, "upstream_error")
        self.assertIn("malformed", result.detail.lower())

    def test_unexpected_payload_shape(self):
        resp = _FakeResp(body=b'{"message": "Not Found"}')
        result = fetch_releases(opener=_make_opener(resp))
        self.assertEqual(result.status, "upstream_error")

    def test_releases_with_missing_tag_skipped(self):
        payload = json.dumps([
            {"tag_name": "v1", "published_at": "2026-01-01T00:00:00Z"},
            {"published_at": "2026-01-02T00:00:00Z"},  # no tag → skip
            {"tag_name": "", "published_at": "x"},     # empty tag → skip
        ]).encode()
        resp = _FakeResp(body=payload)
        result = fetch_releases(opener=_make_opener(resp))
        self.assertEqual(len(result.releases), 1)
        self.assertEqual(result.releases[0].tag, "v1")

    def test_etag_passed_when_state_has_one(self):
        seen_req: list = []

        def opener(req, timeout=None):
            seen_req.append(req)
            return _FakeResp(body=b"[]")

        fetch_releases(etag='W/"abc"', opener=opener)
        self.assertEqual(seen_req[0].headers.get("If-none-match"), 'W/"abc"')


# ---------------------------------------------------------------------------
# Block 6: TestDiffReleases
# ---------------------------------------------------------------------------

class TestDiffReleases(unittest.TestCase):

    def test_all_new_when_state_empty(self):
        state = State()
        fetched = [
            ReleaseEntry(tag="v2", published_at="2026-05-02T00:00:00Z"),
            ReleaseEntry(tag="v1", published_at="2026-05-01T00:00:00Z"),
        ]
        result = diff_releases(state, fetched)
        self.assertEqual([r.tag for r in result], ["v2", "v1"])

    def test_all_seen_returns_empty(self):
        state = State(seen_releases=[
            {"tag": "v1", "published_at": "x"},
            {"tag": "v2", "published_at": "y"},
        ])
        fetched = [
            ReleaseEntry(tag="v1", published_at="x"),
            ReleaseEntry(tag="v2", published_at="y"),
        ]
        self.assertEqual(diff_releases(state, fetched), [])

    def test_partial_overlap(self):
        state = State(seen_releases=[{"tag": "v1", "published_at": "x"}])
        fetched = [
            ReleaseEntry(tag="v1", published_at="2026-05-01T00:00:00Z"),
            ReleaseEntry(tag="v2", published_at="2026-05-02T00:00:00Z"),
        ]
        result = diff_releases(state, fetched)
        self.assertEqual([r.tag for r in result], ["v2"])

    def test_empty_fetch(self):
        self.assertEqual(diff_releases(State(), []), [])

    def test_sort_descending_by_published_at(self):
        fetched = [
            ReleaseEntry(tag="v1", published_at="2026-05-01T00:00:00Z"),
            ReleaseEntry(tag="v3", published_at="2026-05-03T00:00:00Z"),
            ReleaseEntry(tag="v2", published_at="2026-05-02T00:00:00Z"),
        ]
        result = diff_releases(State(), fetched)
        self.assertEqual([r.tag for r in result], ["v3", "v2", "v1"])


# ---------------------------------------------------------------------------
# Block 7: TestBuildBuckets
# ---------------------------------------------------------------------------

class TestBuildBuckets(unittest.TestCase):

    def test_single_release_single_bucket(self):
        releases = [ReleaseEntry(
            tag="v1", published_at="x",
            body="- Added new MCP server",
        )]
        buckets = build_buckets(releases)
        self.assertIn("MCP", buckets)
        self.assertEqual(len(buckets["MCP"]), 1)
        self.assertIn("[v1]", buckets["MCP"][0])

    def test_multi_bucket_release(self):
        releases = [ReleaseEntry(
            tag="v1", published_at="x",
            body="- Added PreCompact hook\n- New skill loader\n- Random fix",
        )]
        buckets = build_buckets(releases)
        self.assertIn("Hooks", buckets)
        self.assertIn("Skills", buckets)
        self.assertIn("Misc", buckets)

    def test_empty_body_no_buckets(self):
        releases = [ReleaseEntry(tag="v1", published_at="x", body="")]
        self.assertEqual(build_buckets(releases), {})

    def test_release_tag_appears_in_each_line(self):
        releases = [ReleaseEntry(
            tag="v9.9.9", published_at="x",
            body="- alpha\n- beta",
        )]
        buckets = build_buckets(releases)
        for lines in buckets.values():
            for line in lines:
                self.assertIn("[v9.9.9]", line)


# ---------------------------------------------------------------------------
# Block 8: TestFormatOutputs
# ---------------------------------------------------------------------------

class TestFormatOutputs(unittest.TestCase):

    def _sample_report(self) -> DiffReport:
        return DiffReport(
            new_releases=[
                ReleaseEntry(tag="v2.1.131", published_at="2026-05-05T00:00:00Z"),
            ],
            buckets={"Hooks": ["[v2.1.131] Added PreCompact hook"]},
            fetch_status="ok",
        )

    def test_text_includes_release_tag(self):
        out = format_text(self._sample_report())
        self.assertIn("v2.1.131", out)
        self.assertIn("Hooks", out)

    def test_markdown_uses_h2_h3(self):
        out = format_markdown(self._sample_report())
        self.assertIn("## What's new", out)
        self.assertIn("### Hooks", out)

    def test_json_is_valid_and_structured(self):
        out = format_json(self._sample_report())
        parsed = json.loads(out)
        self.assertEqual(parsed["fetch_status"], "ok")
        self.assertEqual(len(parsed["new_releases"]), 1)
        self.assertIn("Hooks", parsed["buckets"])

    def test_text_no_releases(self):
        report = DiffReport(fetch_status="ok")
        self.assertIn("No new releases", format_text(report))

    def test_text_offline_marker(self):
        report = DiffReport(fetch_status="offline", fetch_detail="cached")
        out = format_text(report)
        self.assertIn("OFFLINE", out)

    def test_markdown_offline_marker(self):
        report = DiffReport(fetch_status="offline", fetch_detail="cached")
        out = format_markdown(report)
        self.assertIn("Offline", out)

    def test_json_offline_status_preserved(self):
        report = DiffReport(fetch_status="offline", fetch_detail="cached")
        parsed = json.loads(format_json(report))
        self.assertEqual(parsed["fetch_status"], "offline")

    def test_bucket_order_stable(self):
        report = DiffReport(
            new_releases=[ReleaseEntry(tag="v1", published_at="x")],
            buckets={
                "Misc": ["[v1] last"],
                "Hooks": ["[v1] first"],
                "Skills": ["[v1] middle"],
            },
            fetch_status="ok",
        )
        out = format_text(report)
        hooks_idx = out.index("Hooks")
        skills_idx = out.index("Skills")
        misc_idx = out.index("Misc")
        self.assertLess(hooks_idx, skills_idx)
        self.assertLess(skills_idx, misc_idx)


# ---------------------------------------------------------------------------
# Block 9: TestBuildReport
# ---------------------------------------------------------------------------

class TestBuildReport(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.state_path = Path(self.tmp.name) / "state.json"

    def tearDown(self):
        self.tmp.cleanup()

    def test_no_network_short_circuits(self):
        report, state = build_report(self.state_path, no_network=True)
        self.assertEqual(report.fetch_status, "offline")
        self.assertIn("no-network", report.fetch_detail.lower())

    def test_ok_fetch_produces_diff(self):
        payload = json.dumps([
            {"tag_name": "v2", "published_at": "2026-05-02T00:00:00Z", "body": "- Added hook"},
            {"tag_name": "v1", "published_at": "2026-05-01T00:00:00Z", "body": ""},
        ]).encode()
        resp = _FakeResp(body=payload, etag='W/"new"')
        report, state = build_report(self.state_path, opener=_make_opener(resp))
        self.assertEqual(report.fetch_status, "ok")
        self.assertEqual(len(report.new_releases), 2)
        self.assertEqual(state.last_checked_version, "v2")
        self.assertEqual(state.last_etag, 'W/"new"')

    def test_not_modified_keeps_state(self):
        save_state(self.state_path, State(
            last_checked_version="v1",
            last_etag='W/"old"',
            seen_releases=[{"tag": "v1", "published_at": "x"}],
        ))
        err = urllib.error.HTTPError(url="x", code=304, msg="nm", hdrs=None, fp=None)
        report, state = build_report(self.state_path, opener=_make_opener(err))
        self.assertEqual(report.fetch_status, "not_modified")
        self.assertEqual(state.last_checked_version, "v1")

    def test_since_filters_against_tag_string(self):
        payload = json.dumps([
            {"tag_name": "v2", "published_at": "2026-05-02T00:00:00Z", "body": ""},
            {"tag_name": "v1", "published_at": "2026-05-01T00:00:00Z", "body": ""},
        ]).encode()
        resp = _FakeResp(body=payload)
        report, _ = build_report(
            self.state_path,
            since="v1",
            opener=_make_opener(resp),
        )
        self.assertEqual([r.tag for r in report.new_releases], ["v2"])


# ---------------------------------------------------------------------------
# Block 10: TestCLI
# ---------------------------------------------------------------------------

class TestCLI(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.state_path = Path(self.tmp.name) / "state.json"

    def tearDown(self):
        self.tmp.cleanup()

    def test_main_no_network_returns_zero(self):
        with patch("sys.stdout", new_callable=io.StringIO) as fake_out:
            rc = main(["--no-network", "--state-file", str(self.state_path)])
        self.assertEqual(rc, 0)
        self.assertIn("offline", fake_out.getvalue().lower())

    def test_main_quiet_no_releases_no_output(self):
        # quiet suppresses output only when fetch=ok AND no new releases.
        # Pre-seed v1 in seen_releases so the fetched v1 is NOT new.
        save_state(self.state_path, State(
            last_checked_version="v1",
            seen_releases=[{"tag": "v1", "published_at": "x"}],
        ))
        with patch("whats_new_check.fetch_releases") as fake_fetch, \
             patch("sys.stdout", new_callable=io.StringIO) as fake_out:
            fake_fetch.return_value = FetchResult(
                releases=[ReleaseEntry(tag="v1", published_at="x")],
                etag='W/"a"',
                status="ok",
            )
            rc = main([
                "--quiet",
                "--state-file", str(self.state_path),
            ])
        self.assertEqual(rc, 0)
        self.assertEqual(fake_out.getvalue(), "")

    def test_main_format_json(self):
        save_state(self.state_path, State())
        with patch("whats_new_check.fetch_releases") as fake_fetch, \
             patch("sys.stdout", new_callable=io.StringIO) as fake_out:
            fake_fetch.return_value = FetchResult(status="not_modified")
            rc = main([
                "--format", "json",
                "--state-file", str(self.state_path),
            ])
        self.assertEqual(rc, 0)
        parsed = json.loads(fake_out.getvalue())
        self.assertEqual(parsed["fetch_status"], "not_modified")

    def test_main_corrupt_state_returns_one(self):
        self.state_path.write_text("garbage", encoding="utf-8")
        with patch("sys.stderr", new_callable=io.StringIO):
            rc = main(["--state-file", str(self.state_path)])
        self.assertEqual(rc, 1)


# ---------------------------------------------------------------------------
# Block 11: TestStdlibOnly
# ---------------------------------------------------------------------------

class TestStdlibOnly(unittest.TestCase):
    """Mirror test_self_audit.py — refuses to import third-party deps."""

    BANNED = {"requests", "httpx", "yaml", "pydantic", "click", "rich", "anthropic"}

    def test_module_imports_only_stdlib_or_internal(self):
        module_path = Path(__file__).resolve().parent.parent / "whats_new_check.py"
        tree = ast.parse(module_path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    self.assertNotIn(alias.name.split(".")[0], self.BANNED)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    self.assertNotIn(node.module.split(".")[0], self.BANNED)


# ---------------------------------------------------------------------------
# Block 12: TestSeenReleasesCap
# ---------------------------------------------------------------------------

class TestSeenReleasesCap(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "state.json"

    def tearDown(self):
        self.tmp.cleanup()

    def test_fifo_rotation_at_cap(self):
        oversized = [
            {"tag": f"v{i}", "published_at": f"2026-01-{(i % 28) + 1:02d}T00:00:00Z"}
            for i in range(SEEN_RELEASES_CAP + 50)
        ]
        save_state(self.path, State(seen_releases=oversized))
        loaded = load_state(self.path)
        self.assertEqual(len(loaded.seen_releases), SEEN_RELEASES_CAP)
        # Most-recent kept (last 200), oldest dropped
        self.assertEqual(loaded.seen_releases[-1]["tag"], oversized[-1]["tag"])


if __name__ == "__main__":
    unittest.main()
