"""CLI bridge — invoke `llm_router` to rewrite a prompt with /metaprompt scaffolding.

Read raw task description from stdin. Print rewritten prompt to stdout.
Exit non-zero only on hard errors (config malformed, all providers down,
llm_router not installed). Network/transport errors propagate as exit 2
so the caller can fall back to the static template hook.

Usage (from a slash command):
    echo "fix the auth thing" | python3 mcp-bridge/metaprompt_router.py

Or with explicit mode (default: deep):
    echo "..." | python3 mcp-bridge/metaprompt_router.py --mode fast

Design: ~/.claude/projects/-Users-macbook-Dev-claude-second-brain/memory/launch_archive/local-llm-router-recon-2026-04-28.md
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path
from typing import Any, Optional

# Make sibling import (router_init) work when run as a script.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from router_init import LLMRouterMissing, get_router  # noqa: E402

DEFAULT_SYSTEM_PROMPT = """\
You are a prompt engineer. Rewrite the user's task into a structured \
/metaprompt-shaped prompt. Output ONLY the rewritten prompt — no preamble, \
no explanation. Required sections:

## Desired Outcome
What does done look like?

## Approach
Phases, success criteria, constraints.

## Edge Cases
What could go wrong?
"""


def _build_request(task: str, system_prompt: str = DEFAULT_SYSTEM_PROMPT) -> Any:
    """Build a CompletionRequest. Lazy-imports llm_router models."""
    from llm_router import CompletionRequest, Message, Role  # type: ignore[import-not-found]

    return CompletionRequest(
        messages=[
            Message(role=Role.SYSTEM, content=system_prompt),
            Message(role=Role.USER, content=task),
        ],
        model="claude-opus-4-7",
        max_tokens=2048,
        temperature=0.4,
    )


async def _run_async(task: str, config_path: Optional[str] = None) -> str:
    router = get_router(config_path=config_path)
    request = _build_request(task)
    response = await router.complete(request)
    # Extract assistant text; CompletionResponse has `content` (string) per recon
    if hasattr(response, "content"):
        return str(response.content).strip()
    return str(response).strip()


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="metaprompt-router",
        description="Rewrite a prompt via local-llm-router (universal-model bridge).",
    )
    p.add_argument("--config", default="", help="Override path to llm_router.toml")
    p.add_argument(
        "--mode",
        choices=["fast", "deep"],
        default="deep",
        help="Scaffolding depth (fast=template-light, deep=full)",
    )
    return p


def main(argv: Optional[list[str]] = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    task = sys.stdin.read().strip()
    if not task:
        print("[ERROR] no task on stdin", file=sys.stderr)
        return 1

    try:
        rewritten = asyncio.run(_run_async(
            task=task,
            config_path=args.config or None,
        ))
    except LLMRouterMissing as e:
        print(f"[ROUTER-MISSING] {e}", file=sys.stderr)
        return 2
    except Exception as e:  # noqa: BLE001 — surface clearly to caller
        print(f"[ROUTER-ERROR] {type(e).__name__}: {e}", file=sys.stderr)
        return 2

    sys.stdout.write(rewritten + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
