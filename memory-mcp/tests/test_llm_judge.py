"""Tests for the LLM-judge parse layer — so a flaky model reply can't be silently
misread as a verdict. Only the deterministic parser is unit-tested; the live model
call is exercised by the eval runner (needs an endpoint), never in unit tests.
"""
from __future__ import annotations

import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPTS_DIR))

import unittest
from llm_judge import parse_verdict  # noqa: E402


class TestParseVerdict(unittest.TestCase):
    def test_clean_yes(self):
        v = parse_verdict('{"violates": true, "why": "force-push to main"}')
        self.assertTrue(v["violates"])

    def test_clean_no(self):
        v = parse_verdict('{"violates": false, "why": "normal push"}')
        self.assertFalse(v["violates"])

    def test_json_embedded_in_prose(self):
        v = parse_verdict('Sure! Here is my answer:\n{"violates": true, "why": "x"}\nHope that helps')
        self.assertTrue(v["violates"])

    def test_fenced_json(self):
        v = parse_verdict('```json\n{"violates": false, "why": "ok"}\n```')
        self.assertFalse(v["violates"])

    def test_reasoning_model_think_block_stripped(self):
        # gpt-oss / deepseek-r1 wrap the answer in <think>...</think> with its own
        # quotes/braces — must be stripped before the JSON is parsed.
        reply = ('<think>\nThe commitment forbids force-push. The action is '
                 '"git push --force main". So it violates.\n</think>\n'
                 '{"violates": true, "why": "force-pushes to main"}')
        v = parse_verdict(reply)
        self.assertIsNotNone(v)
        self.assertTrue(v["violates"])

    def test_unparseable_returns_none_not_a_guess(self):
        # A reply we cannot parse MUST be None (abstain), never silently False/True.
        v = parse_verdict("I think maybe possibly it could be a problem?")
        self.assertIsNone(v)

    def test_empty_returns_none(self):
        self.assertIsNone(parse_verdict(""))
        self.assertIsNone(parse_verdict(None))


if __name__ == "__main__":
    unittest.main()
