"""Tests for commitment_gate_hook.py — the PreToolUse commitment-gate.

The un-absorbed sliver: native PreToolUse can block (exit 2), but nothing wires it
to gate an action against the operator's STORED COMMITMENTS. This does.

Driven as a real subprocess over stdin (how Claude Code invokes a PreToolUse hook).
Native contract (verified from anthropics/claude-code examples/hooks):
  - stdin JSON: {"tool_name": ..., "tool_input": {...}}
  - exit 2 + stderr  -> BLOCKS the tool call, stderr shown to Claude
  - exit 0           -> allow

Safety rails (from the 2026-05-31 safety tribunal — Schneier/Willison/Amodei):
  - gate on the OBSERVED action text (the real command/args), NOT any agent self-label.
  - FAIL-OPEN on any error (missing db, bad json, import fail) — a gate that breaks
    every tool call on its own bug is worse than no gate. Only a real detected
    load-bearing contradiction blocks.
  - diagnostic over records, not a safety/coherence-of-the-agent claim.

Phase 1c rollout safety: the gate ships in SHADOW mode by default
(COMMITMENT_GATE_ENFORCE unset/0) — it detects + logs the would-block to stderr but
exits 0, so wiring it into a live session never breaks real work until the operator
has seen the false-positive rate. Set COMMITMENT_GATE_ENFORCE=1 to actually block.

Commitment source is commitments.load_commitments (rule/pattern memories) — the
single provenance the gate, the override CLI, and the digest all read.

Uses a throwaway db via MEMORY_DB env — never the live store.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPTS_DIR))

from db import MemoryDB  # noqa: E402

HOOK = SCRIPTS_DIR / "commitment_gate_hook.py"

# Enforce-mode env: most block tests exercise the enforcement path (exit 2).
ENFORCE = {"COMMITMENT_GATE_ENFORCE": "1"}


def _seed_rule(db_path: str, content: str, tags: list, conf: float = 0.9,
               category: str = "rule") -> None:
    db = MemoryDB(db_path)
    try:
        db.save(content=content, category=category, tags=tags, confidence=conf)
    finally:
        db.close()


def _run(payload: dict, db_path: str | None, extra_env: dict | None = None):
    env = {**os.environ}
    if db_path is not None:
        env["MEMORY_DB"] = db_path
    # default: structural-only (no judge) so tests are hermetic + fast
    env.setdefault("COMMITMENT_GATE_SEMANTIC", "0")
    if extra_env:
        env.update(extra_env)
    return subprocess.run(
        [sys.executable, str(HOOK)],
        input=json.dumps(payload), capture_output=True, text=True, env=env,
    )


class TestCommitmentGateHook(unittest.TestCase):

    def test_blocks_structural_contradiction_exit2(self):
        with tempfile.TemporaryDirectory() as tmp:
            dbp = str(Path(tmp) / "m.db")
            _seed_rule(dbp, "Deploy notifications are enabled for prod.", ["slack"], 0.9)
            payload = {"tool_name": "Bash",
                       "tool_input": {"command": "set deploy notifications disabled for prod"}}
            p = _run(payload, dbp, extra_env=ENFORCE)
            self.assertEqual(p.returncode, 2)        # exit 2 = BLOCK
            self.assertIn("commitment", p.stderr.lower())

    def test_allows_clean_action_exit0(self):
        with tempfile.TemporaryDirectory() as tmp:
            dbp = str(Path(tmp) / "m.db")
            _seed_rule(dbp, "Never force-push to main.", ["git"], 0.9)
            payload = {"tool_name": "Bash", "tool_input": {"command": "git status"}}
            p = _run(payload, dbp, extra_env=ENFORCE)
            self.assertEqual(p.returncode, 0)
            self.assertEqual(p.stdout.strip(), "")

    def test_gates_on_observed_action_not_self_label(self):
        # Schneier rail: a benign declared label must NOT suppress a real contradiction.
        with tempfile.TemporaryDirectory() as tmp:
            dbp = str(Path(tmp) / "m.db")
            _seed_rule(dbp, "Deploy notifications are enabled for prod.", ["slack"], 0.9)
            payload = {"tool_name": "Bash",
                       "tool_input": {"command": "set deploy notifications disabled for prod",
                                      "description": "routine harmless sync"}}
            p = _run(payload, dbp, extra_env=ENFORCE)
            self.assertEqual(p.returncode, 2)  # still blocks; description ignored

    def test_below_floor_commitment_does_not_block(self):
        with tempfile.TemporaryDirectory() as tmp:
            dbp = str(Path(tmp) / "m.db")
            _seed_rule(dbp, "Deploy notifications are enabled for prod.", ["slack"], 0.4)
            payload = {"tool_name": "Bash",
                       "tool_input": {"command": "set deploy notifications disabled for prod"}}
            p = _run(payload, dbp, extra_env=ENFORCE)
            self.assertEqual(p.returncode, 0)  # weak prior -> advisory, not block

    def test_fail_open_on_missing_db(self):
        payload = {"tool_name": "Bash", "tool_input": {"command": "anything at all"}}
        p = _run(payload, "/nonexistent/path/to/memory.db", extra_env=ENFORCE)
        self.assertEqual(p.returncode, 0)  # no db -> allow

    def test_fail_open_on_garbage_payload(self):
        env = {**os.environ, "COMMITMENT_GATE_SEMANTIC": "0", "COMMITMENT_GATE_ENFORCE": "1"}
        p = subprocess.run([sys.executable, str(HOOK)], input="not json{{{",
                           capture_output=True, text=True, env=env)
        self.assertEqual(p.returncode, 0)

    def test_non_command_tool_extracts_text_fields(self):
        # A Write tool's content is the observed action; gate still applies.
        with tempfile.TemporaryDirectory() as tmp:
            dbp = str(Path(tmp) / "m.db")
            _seed_rule(dbp, "Deploy notifications are enabled for prod.", ["slack"], 0.9)
            payload = {"tool_name": "Write",
                       "tool_input": {"file_path": "x.txt",
                                      "content": "set deploy notifications disabled for prod"}}
            p = _run(payload, dbp, extra_env=ENFORCE)
            self.assertEqual(p.returncode, 2)

    def test_no_tags_match_allows(self):
        with tempfile.TemporaryDirectory() as tmp:
            dbp = str(Path(tmp) / "m.db")
            _seed_rule(dbp, "Never force-push to main.", ["git"], 0.9)
            payload = {"tool_name": "Bash", "tool_input": {"command": "send the weekly email"}}
            p = _run(payload, dbp, extra_env=ENFORCE)
            self.assertEqual(p.returncode, 0)

    # ── Phase 1c: shadow-mode default + single-source commitment provenance ──

    def test_shadow_mode_is_default_detects_but_allows(self):
        # No COMMITMENT_GATE_ENFORCE → a real contradiction is DETECTED and logged to
        # stderr, but the tool call is ALLOWED (exit 0). Safe-rollout default.
        with tempfile.TemporaryDirectory() as tmp:
            dbp = str(Path(tmp) / "m.db")
            _seed_rule(dbp, "Deploy notifications are enabled for prod.", ["slack"], 0.9)
            payload = {"tool_name": "Bash",
                       "tool_input": {"command": "set deploy notifications disabled for prod"}}
            p = _run(payload, dbp)  # default env = shadow
            self.assertEqual(p.returncode, 0)                 # NOT blocked
            self.assertIn("shadow", p.stderr.lower())         # but the would-block IS logged
            self.assertIn("would block", p.stderr.lower())
            db = MemoryDB(dbp)                                 # 1b: recorded even in shadow
            try:
                n = db.conn.execute(
                    "SELECT COUNT(*) FROM feedback_violations").fetchone()[0]
            finally:
                db.close()
            self.assertEqual(n, 1)

    def test_pattern_category_commitment_also_gates(self):
        # Proves the gate reads its commitments from commitments.load_commitments,
        # which includes BOTH 'rule' and 'pattern' categories.
        with tempfile.TemporaryDirectory() as tmp:
            dbp = str(Path(tmp) / "m.db")
            _seed_rule(dbp, "Deploy notifications are enabled for prod.", ["slack"],
                       0.9, category="pattern")
            payload = {"tool_name": "Bash",
                       "tool_input": {"command": "set deploy notifications disabled for prod"}}
            p = _run(payload, dbp, extra_env=ENFORCE)
            self.assertEqual(p.returncode, 2)

    def test_enforced_block_records_durable_violation_row(self):
        # 1b: a block writes a feedback_violations row (the durable diagnostic edge)
        # — in addition to exit 2. record_block never decays confidence.
        with tempfile.TemporaryDirectory() as tmp:
            dbp = str(Path(tmp) / "m.db")
            _seed_rule(dbp, "Deploy notifications are enabled for prod.", ["slack"], 0.9)
            payload = {"tool_name": "Bash",
                       "tool_input": {"command": "set deploy notifications disabled for prod"}}
            p = _run(payload, dbp, extra_env=ENFORCE)
            self.assertEqual(p.returncode, 2)
            db = MemoryDB(dbp)
            try:
                n = db.conn.execute(
                    "SELECT COUNT(*) FROM feedback_violations").fetchone()[0]
                conf = db.conn.execute(
                    "SELECT confidence FROM memories").fetchone()[0]
            finally:
                db.close()
            self.assertEqual(n, 1)              # block recorded
            self.assertAlmostEqual(conf, 0.9)   # confidence NOT decayed by the block


if __name__ == "__main__":
    unittest.main()
