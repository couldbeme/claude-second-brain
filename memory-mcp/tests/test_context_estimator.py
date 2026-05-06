"""Tests for context_estimator.py — TDD-first.

Eight checks defined in the feature/oss-launch scope:
1. test_threshold_tiers          — boundary values for each tier
2. test_context_window_known_models — Sonnet 4.6, Opus 4.7, Haiku 4.5 → 200_000;
                                     Sonnet 4.6 1m flag → 1_000_000
3. test_context_window_unknown_model_default — returns 200_000
4. test_estimate_sums_input_tokens — fixture JSONL with 3 turns → correct sum
5. test_estimate_handles_malformed_lines — corrupt JSON skipped, others summed
6. test_estimate_missing_transcript — graceful fail, tokens_used=0, threshold='ok'
7. test_estimate_no_usage_field  — turn without usage field skipped silently
8. test_main_cli_outputs_json_when_flag — --json flag → parseable JSON to stdout
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from io import StringIO
from pathlib import Path

# Add parent dir (memory-mcp/) to sys.path so we can import context_estimator
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from context_estimator import (  # noqa: E402
    ContextEstimate,
    context_window_for_model,
    estimate_from_transcript,
    main,
    threshold_for_percent,
)


def _write_jsonl(path: Path, lines: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _make_turn(input_tokens: int, output_tokens: int = 10) -> str:
    """Build a minimal valid assistant turn JSONL line with usage data."""
    return json.dumps({
        "type": "assistant",
        "message": {
            "usage": {
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
            }
        },
    })


class TestThresholdTiers(unittest.TestCase):
    """Test 1: boundary values for each tier."""

    def test_ok_at_zero(self):
        self.assertEqual(threshold_for_percent(0.0), "ok")

    def test_ok_below_sixty(self):
        self.assertEqual(threshold_for_percent(0.59), "ok")

    def test_notice_at_sixty(self):
        self.assertEqual(threshold_for_percent(0.60), "notice")

    def test_notice_just_below_eighty(self):
        self.assertEqual(threshold_for_percent(0.799), "notice")

    def test_warn_at_eighty(self):
        self.assertEqual(threshold_for_percent(0.80), "warn")

    def test_warn_just_below_ninety(self):
        self.assertEqual(threshold_for_percent(0.899), "warn")

    def test_imminent_at_ninety(self):
        self.assertEqual(threshold_for_percent(0.90), "imminent")

    def test_imminent_over_one_hundred(self):
        # Over 100% is still imminent (context already blown)
        self.assertEqual(threshold_for_percent(1.05), "imminent")


class TestContextWindowKnownModels(unittest.TestCase):
    """Test 2: known models map to correct window sizes."""

    def test_sonnet_46_200k(self):
        self.assertEqual(context_window_for_model("claude-sonnet-4-6"), 200_000)

    def test_opus_47_200k(self):
        self.assertEqual(context_window_for_model("claude-opus-4-7"), 200_000)

    def test_haiku_45_200k(self):
        self.assertEqual(context_window_for_model("claude-haiku-4-5"), 200_000)

    def test_sonnet_46_1m_flag(self):
        # The 1m-tier variant; model ID contains "[1m]" or similar qualifier
        self.assertEqual(context_window_for_model("claude-sonnet-4-6[1m]"), 1_000_000)

    def test_opus_47_1m_flag(self):
        self.assertEqual(context_window_for_model("claude-opus-4-7[1m]"), 1_000_000)


class TestContextWindowUnknownModelDefault(unittest.TestCase):
    """Test 3: unknown model returns 200_000 default."""

    def test_unknown_model_defaults(self):
        self.assertEqual(context_window_for_model("claude-unknown-9-9"), 200_000)

    def test_empty_string_defaults(self):
        self.assertEqual(context_window_for_model(""), 200_000)


class TestEstimateSumsInputTokens(unittest.TestCase):
    """Test 4: fixture JSONL with 3 turns → correct sum."""

    def test_three_turn_sum(self):
        with tempfile.TemporaryDirectory() as tmp:
            transcript = Path(tmp) / "session.jsonl"
            _write_jsonl(transcript, [
                _make_turn(1_000),
                _make_turn(2_000),
                _make_turn(3_000),
            ])
            result = estimate_from_transcript(transcript, model="claude-sonnet-4-6")
            self.assertEqual(result.tokens_used, 6_000)
            self.assertEqual(result.tokens_max, 200_000)
            self.assertAlmostEqual(result.percent_used, 6_000 / 200_000, places=6)
            self.assertEqual(result.threshold, "ok")

    def test_session_id_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            transcript = Path(tmp) / "abc123.jsonl"
            _write_jsonl(transcript, [_make_turn(500)])
            result = estimate_from_transcript(transcript)
            # session_id is derived from filename stem
            self.assertEqual(result.session_id, "abc123")


class TestEstimateHandlesMalformedLines(unittest.TestCase):
    """Test 5: corrupt JSON line skipped, others summed correctly."""

    def test_corrupt_line_skipped(self):
        with tempfile.TemporaryDirectory() as tmp:
            transcript = Path(tmp) / "session.jsonl"
            _write_jsonl(transcript, [
                _make_turn(1_000),
                "{this is not: valid json!!!}",
                _make_turn(2_000),
            ])
            result = estimate_from_transcript(transcript)
            self.assertEqual(result.tokens_used, 3_000)

    def test_empty_line_skipped(self):
        with tempfile.TemporaryDirectory() as tmp:
            transcript = Path(tmp) / "session.jsonl"
            # Write with a blank line in the middle
            transcript.write_text(
                _make_turn(1_500) + "\n\n" + _make_turn(500) + "\n",
                encoding="utf-8",
            )
            result = estimate_from_transcript(transcript)
            self.assertEqual(result.tokens_used, 2_000)


class TestEstimateMissingTranscript(unittest.TestCase):
    """Test 6: graceful fail when transcript doesn't exist."""

    def test_missing_file_returns_zero_ok(self):
        result = estimate_from_transcript(Path("/nonexistent/path/session.jsonl"))
        self.assertEqual(result.tokens_used, 0)
        self.assertEqual(result.threshold, "ok")
        # percent_used must be 0.0 when there are no tokens
        self.assertAlmostEqual(result.percent_used, 0.0)

    def test_missing_file_model_still_applied(self):
        result = estimate_from_transcript(
            Path("/nonexistent/path/session.jsonl"),
            model="claude-opus-4-7",
        )
        self.assertEqual(result.tokens_max, 200_000)


class TestEstimateNoUsageField(unittest.TestCase):
    """Test 7: turns without usage field skipped silently."""

    def test_no_usage_field_skipped(self):
        with tempfile.TemporaryDirectory() as tmp:
            transcript = Path(tmp) / "session.jsonl"
            no_usage_line = json.dumps({"type": "user", "message": {"content": "hello"}})
            tool_use_line = json.dumps({"type": "tool_use", "name": "Read", "input": {}})
            _write_jsonl(transcript, [
                no_usage_line,
                tool_use_line,
                _make_turn(1_234),
            ])
            result = estimate_from_transcript(transcript)
            self.assertEqual(result.tokens_used, 1_234)

    def test_usage_field_without_input_tokens_skipped(self):
        with tempfile.TemporaryDirectory() as tmp:
            transcript = Path(tmp) / "session.jsonl"
            # usage present but no input_tokens key
            partial_usage = json.dumps({
                "type": "assistant",
                "message": {"usage": {"output_tokens": 99}},
            })
            _write_jsonl(transcript, [partial_usage, _make_turn(777)])
            result = estimate_from_transcript(transcript)
            self.assertEqual(result.tokens_used, 777)


class TestMainCliOutputsJson(unittest.TestCase):
    """Test 8: --json flag produces parseable JSON to stdout."""

    def test_json_flag_produces_valid_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            transcript = Path(tmp) / "session_abc.jsonl"
            _write_jsonl(transcript, [_make_turn(5_000)])

            captured = StringIO()
            old_stdout = sys.stdout
            sys.stdout = captured
            try:
                exit_code = main([str(transcript), "--json"])
            finally:
                sys.stdout = old_stdout

            self.assertEqual(exit_code, 0)
            output = captured.getvalue()
            parsed = json.loads(output)
            self.assertIn("tokens_used", parsed)
            self.assertIn("tokens_max", parsed)
            self.assertIn("percent_used", parsed)
            self.assertIn("threshold", parsed)
            self.assertEqual(parsed["tokens_used"], 5_000)

    def test_no_json_flag_produces_human_readable(self):
        with tempfile.TemporaryDirectory() as tmp:
            transcript = Path(tmp) / "session_xyz.jsonl"
            _write_jsonl(transcript, [_make_turn(10_000)])

            captured = StringIO()
            old_stdout = sys.stdout
            sys.stdout = captured
            try:
                exit_code = main([str(transcript)])
            finally:
                sys.stdout = old_stdout

            self.assertEqual(exit_code, 0)
            output = captured.getvalue()
            # Human-readable: should contain % symbol or the word "context"
            self.assertTrue(
                "%" in output or "context" in output.lower(),
                f"Expected human-readable output, got: {output!r}",
            )


if __name__ == "__main__":
    unittest.main()
