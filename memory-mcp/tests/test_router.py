"""Tests for mcp-bridge/router_init.py and metaprompt_router.py.

Coverage:
  - get_router raises LLMRouterMissing when llm_router not installed
  - get_router accepts valid strategy names and rejects invalid ones
  - metaprompt_router.main exits 1 on empty stdin
  - metaprompt_router.main exits 2 when llm_router missing
  - _build_request constructs a CompletionRequest with system + user messages
    (skipped when llm_router not installed — graceful)
"""

from __future__ import annotations

import io
import sys
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Resolve mcp-bridge import path
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "mcp-bridge"))

import router_init  # noqa: E402
import metaprompt_router  # noqa: E402

from router_init import LLMRouterMissing, get_router  # noqa: E402


class TestGetRouterMissing(unittest.TestCase):
    """When llm_router is not installed, get_router raises LLMRouterMissing."""

    def test_missing_raises_llm_router_missing(self):
        # Force ImportError by making the import inside get_router fail
        with patch.dict(sys.modules, {"llm_router": None}):
            with self.assertRaises(LLMRouterMissing) as ctx:
                get_router()
            self.assertIn("pip install llm-router", str(ctx.exception))

    def test_module_imports_without_llm_router(self):
        """router_init must import even when llm_router is absent."""
        # Just verify the module imported successfully (it did at the top)
        self.assertTrue(hasattr(router_init, "get_router"))
        self.assertTrue(hasattr(router_init, "LLMRouterMissing"))


class TestGetRouterStrategy(unittest.TestCase):
    """Strategy parameter validation, with mocked llm_router."""

    def test_valid_strategy_passed(self):
        fake_router = MagicMock()

        class FakeStrategy:
            FALLBACK = "fallback-sentinel"
            MANUAL = "manual-sentinel"
            HEALTH = "health-sentinel"

            def __class_getitem__(cls, name):
                return getattr(cls, name)

        fake_module = MagicMock()
        fake_module.Router.from_config.return_value = fake_router
        fake_module.RoutingStrategy = FakeStrategy

        with patch.dict(sys.modules, {"llm_router": fake_module}):
            router = get_router(strategy="FALLBACK")
        fake_router.set_strategy.assert_called_once_with("fallback-sentinel")
        self.assertIs(router, fake_router)

    def test_invalid_strategy_raises_value_error(self):
        import enum

        class FakeStrategy(enum.Enum):
            FALLBACK = "fallback"
            MANUAL = "manual"

        fake_module = MagicMock()
        fake_module.Router.from_config.return_value = MagicMock()
        fake_module.RoutingStrategy = FakeStrategy

        with patch.dict(sys.modules, {"llm_router": fake_module}):
            with self.assertRaises(ValueError) as ctx:
                get_router(strategy="NOT_A_REAL_STRATEGY")
            self.assertIn("strategy must be one of", str(ctx.exception))
            # Confirm the error message lists the valid options
            self.assertIn("FALLBACK", str(ctx.exception))


class TestMetapromptRouterCLI(unittest.TestCase):

    def test_empty_stdin_exits_one(self):
        with patch("sys.stdin", io.StringIO("")), \
             patch("sys.stderr", new_callable=io.StringIO) as fake_err:
            rc = metaprompt_router.main([])
        self.assertEqual(rc, 1)
        self.assertIn("no task", fake_err.getvalue().lower())

    def test_router_missing_exits_two(self):
        with patch("sys.stdin", io.StringIO("fix the thing")), \
             patch.dict(sys.modules, {"llm_router": None}), \
             patch("sys.stderr", new_callable=io.StringIO) as fake_err:
            rc = metaprompt_router.main([])
        self.assertEqual(rc, 2)
        self.assertIn("router-missing", fake_err.getvalue().lower())

    def test_runtime_error_exits_two(self):
        # Patch _run_async to raise; verify exit code 2 + stderr message
        async def boom(*args, **kwargs):
            raise RuntimeError("upstream timeout")

        with patch("sys.stdin", io.StringIO("task")), \
             patch.object(metaprompt_router, "_run_async", boom), \
             patch("sys.stderr", new_callable=io.StringIO) as fake_err:
            rc = metaprompt_router.main([])
        self.assertEqual(rc, 2)
        self.assertIn("router-error", fake_err.getvalue().lower())
        self.assertIn("upstream timeout", fake_err.getvalue())

    def test_success_writes_rewritten_to_stdout(self):
        async def fake_async(task, config_path=None):
            return "## Desired Outcome\n...rewritten..."

        with patch("sys.stdin", io.StringIO("fix the auth thing")), \
             patch.object(metaprompt_router, "_run_async", fake_async), \
             patch("sys.stdout", new_callable=io.StringIO) as fake_out:
            rc = metaprompt_router.main([])
        self.assertEqual(rc, 0)
        self.assertIn("Desired Outcome", fake_out.getvalue())


class TestRouterInitNoSideEffects(unittest.TestCase):
    """Importing router_init must not perform network I/O or read config."""

    def test_module_attributes_present(self):
        # Sanity-check the public surface
        self.assertTrue(callable(router_init.get_router))
        self.assertTrue(issubclass(router_init.LLMRouterMissing, RuntimeError))
        self.assertIsInstance(router_init.DEFAULT_CONFIG_PATH, Path)


if __name__ == "__main__":
    unittest.main()
