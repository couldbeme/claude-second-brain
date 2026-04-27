"""Context-window visibility estimator.

Reads a Claude Code session JSONL transcript, sums `usage.input_tokens` per
turn, and returns a structured estimate of how full the context window is.

Design constraints:
- Pure stdlib only — no tiktoken, no Anthropic SDK.
- Privacy: reads ONLY usage.input_tokens; never loads message bodies.
- Backwards-compat: missing `usage` field in a turn is skipped silently.
- Atomic writes are the caller's responsibility (precompact_hook.py).

Public API:
    ContextEstimate          — dataclass returned by estimate_from_transcript
    estimate_from_transcript — reads JSONL, sums tokens, returns estimate
    context_window_for_model — maps model name → context-window size
    threshold_for_percent    — maps 0.0–1.0+ to 'ok'|'notice'|'warn'|'imminent'
    main                     — CLI entry point (reads $CLAUDE_TRANSCRIPT_PATH or argv)
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

# ---------------------------------------------------------------------------
# Context-window table (April 2026)
# Default is 200_000 for any unrecognised model.
# The "[1m]" suffix in the model ID signals the 1M-token extended tier.
# ---------------------------------------------------------------------------

_DEFAULT_WINDOW = 200_000
_ONE_MILLION = 1_000_000

# Models that have a 1M-token tier.  Match by checking if model ID contains
# one of these stems AND the "[1m]" qualifier.
_ONE_MILLION_CAPABLE = {
    "claude-sonnet-4-6",
    "claude-opus-4-7",
}

# Explicit full-name → window map for models that are NOT 200K by default.
# Currently all known Claude 4.x models default to 200K, so this is a forward-
# compat hook rather than an active override.
_MODEL_WINDOW_MAP: dict[str, int] = {}


# ---------------------------------------------------------------------------
# Dataclass
# ---------------------------------------------------------------------------

@dataclass
class ContextEstimate:
    session_id: str
    model: str
    tokens_used: int
    tokens_max: int
    percent_used: float       # 0.0 to 1.0+ (can exceed 1.0 if over limit)
    threshold: str            # 'ok' | 'notice' | 'warn' | 'imminent'


# ---------------------------------------------------------------------------
# Core functions
# ---------------------------------------------------------------------------

def context_window_for_model(model: str) -> int:
    """Return the context-window size for the given model ID.

    Rules (in priority order):
    1. If model ends with '[1m]' and the base model is 1M-capable → 1_000_000.
    2. If model is in the explicit override map → use that value.
    3. Default → 200_000.
    """
    if not model:
        return _DEFAULT_WINDOW

    # Check for 1M qualifier — e.g. "claude-sonnet-4-6[1m]"
    if model.endswith("[1m]"):
        base = model[:-4]  # strip "[1m]"
        if base in _ONE_MILLION_CAPABLE:
            return _ONE_MILLION
        # Unknown model with [1m] flag — still honour it as 1M
        return _ONE_MILLION

    # Explicit override map
    if model in _MODEL_WINDOW_MAP:
        return _MODEL_WINDOW_MAP[model]

    return _DEFAULT_WINDOW


def threshold_for_percent(percent: float) -> str:
    """Map usage fraction to a threshold label.

    Tiers:
      0.0 – <0.60  → 'ok'
      0.60 – <0.80 → 'notice'
      0.80 – <0.90 → 'warn'
      0.90+        → 'imminent'
    """
    if percent >= 0.90:
        return "imminent"
    if percent >= 0.80:
        return "warn"
    if percent >= 0.60:
        return "notice"
    return "ok"


def estimate_from_transcript(
    transcript_path: Path,
    model: str | None = None,
) -> ContextEstimate:
    """Read transcript JSONL, sum input_tokens, return ContextEstimate.

    - Missing file → returns ContextEstimate with tokens_used=0, threshold='ok'.
    - Malformed JSON lines → skipped silently.
    - Turns without 'usage' or 'usage.input_tokens' → skipped silently.
    - Only reads usage.input_tokens; never loads message content.
    """
    resolved_model = model or "claude-sonnet-4-6"
    tokens_max = context_window_for_model(resolved_model)
    session_id = transcript_path.stem  # filename without extension

    # Graceful failure when transcript does not exist
    if not transcript_path.exists():
        return ContextEstimate(
            session_id=session_id,
            model=resolved_model,
            tokens_used=0,
            tokens_max=tokens_max,
            percent_used=0.0,
            threshold="ok",
        )

    tokens_used = 0
    try:
        text = transcript_path.read_text(encoding="utf-8")
    except OSError:
        # Unreadable file — treat as missing
        return ContextEstimate(
            session_id=session_id,
            model=resolved_model,
            tokens_used=0,
            tokens_max=tokens_max,
            percent_used=0.0,
            threshold="ok",
        )

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue  # malformed line — skip silently

        # Navigate: event → message → usage → input_tokens
        # Privacy: we read ONLY this field, nothing else.
        try:
            input_tokens = event["message"]["usage"]["input_tokens"]
        except (KeyError, TypeError):
            continue  # field absent — skip silently

        if isinstance(input_tokens, int):
            tokens_used += input_tokens

    percent_used = tokens_used / tokens_max if tokens_max > 0 else 0.0
    threshold = threshold_for_percent(percent_used)

    return ContextEstimate(
        session_id=session_id,
        model=resolved_model,
        tokens_used=tokens_used,
        tokens_max=tokens_max,
        percent_used=percent_used,
        threshold=threshold,
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    """CLI entry point.

    Usage:
        python context_estimator.py [transcript_path] [--json] [--model MODEL]

    If transcript_path is omitted, reads $CLAUDE_TRANSCRIPT_PATH env var.
    """
    parser = argparse.ArgumentParser(
        description="Estimate Claude Code context-window usage from a session JSONL."
    )
    parser.add_argument(
        "transcript",
        nargs="?",
        default=None,
        help="Path to the session JSONL transcript. "
             "Falls back to $CLAUDE_TRANSCRIPT_PATH if omitted.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="output_json",
        help="Output machine-readable JSON instead of human-readable text.",
    )
    parser.add_argument(
        "--model",
        default=None,
        help="Model ID override (e.g. claude-sonnet-4-6). "
             "Falls back to $ANTHROPIC_MODEL if omitted.",
    )

    args = parser.parse_args(argv)

    # Resolve transcript path
    transcript_str = args.transcript or os.environ.get("CLAUDE_TRANSCRIPT_PATH")
    if not transcript_str:
        parser.error(
            "transcript path required: pass it as an argument or set "
            "$CLAUDE_TRANSCRIPT_PATH"
        )
    transcript_path = Path(transcript_str)

    # Resolve model
    model = args.model or os.environ.get("ANTHROPIC_MODEL")

    estimate = estimate_from_transcript(transcript_path, model=model)

    if args.output_json:
        print(json.dumps(asdict(estimate), indent=2))
    else:
        pct = estimate.percent_used * 100
        bar_filled = int(pct / 5)  # 20-char bar
        bar = "#" * bar_filled + "-" * (20 - bar_filled)
        status_label = {
            "ok": "OK",
            "notice": "NOTICE",
            "warn": "WARN",
            "imminent": "COMPACTION-IMMINENT",
        }.get(estimate.threshold, estimate.threshold.upper())

        print(
            f"[CONTEXT: {pct:.1f}%] [{bar}] {estimate.tokens_used:,}/{estimate.tokens_max:,} tokens"
            f" — {status_label}"
            f" — session {estimate.session_id}"
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
