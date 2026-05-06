"""Lazy-load wrapper around `llm_router` (couldbeme/local-llm-router).

The package is OPTIONAL — claude-second-brain works against Anthropic
directly without it. Importing this module is cheap; the actual `llm_router`
import only happens when `get_router()` is called.

Usage:
    from router_init import get_router
    router = get_router()  # raises RuntimeError if llm_router not installed

Design: ~/.claude/projects/-Users-macbook-Dev-claude-second-brain/memory/launch_archive/local-llm-router-recon-2026-04-28.md
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

DEFAULT_CONFIG_PATH = Path.home() / ".claude" / "llm_router.toml"


class LLMRouterMissing(RuntimeError):
    """llm-router package is not installed in the current environment."""


def get_router(
    config_path: Optional[str] = None,
    strategy: str = "FALLBACK",
) -> Any:
    """Return a configured `llm_router.Router`.

    Lazy-imports `llm_router` so this module is import-safe even when
    the package is missing. Raises LLMRouterMissing with a clear message
    on absence.

    `config_path` defaults to ~/.claude/llm_router.toml. If the file is
    missing, llm_router falls back to env-var-only configuration
    (LLM_ROUTER_PRIMARY, ANTHROPIC_API_KEY, etc.).

    `strategy` is one of MANUAL | FALLBACK | HEALTH (matches
    llm_router.RoutingStrategy enum).
    """
    try:
        from llm_router import Router, RoutingStrategy  # type: ignore[import-not-found]
    except ImportError as e:
        raise LLMRouterMissing(
            "llm-router not installed. Install with: pip install llm-router"
        ) from e

    resolved_config = config_path or (
        str(DEFAULT_CONFIG_PATH) if DEFAULT_CONFIG_PATH.exists() else None
    )

    router = Router.from_config(config_path=resolved_config)

    try:
        router.set_strategy(RoutingStrategy[strategy])
    except (KeyError, ValueError) as e:
        valid = [m.name for m in RoutingStrategy]
        raise ValueError(f"strategy must be one of {valid}, got {strategy!r}") from e

    return router
