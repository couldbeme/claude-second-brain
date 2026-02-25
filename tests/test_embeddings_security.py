"""Security tests for EmbeddingClient: URL validation and API key auth.

TDD cycle:
  RED   -- these tests fail because the features don't exist yet
  GREEN -- implement URL warning + auth header in embeddings.py
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent / "memory-mcp"))
sys.modules["sqlite_vec"] = MagicMock()
# httpx lives only in the memory-mcp venv; mock it so the project-root
# pytest venv can import embeddings.py without the real package.
sys.modules["httpx"] = MagicMock()

from embeddings import DEFAULT_LMS_URL, EmbeddingClient  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_ok_response(embedding: list[float] | None = None) -> MagicMock:
    """Return a mock httpx response that looks like a successful embedding call."""
    if embedding is None:
        embedding = [0.1] * 768
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = {"data": [{"embedding": embedding}]}
    return mock_resp


# ---------------------------------------------------------------------------
# TestEmbeddingURLValidation
# ---------------------------------------------------------------------------

class TestEmbeddingURLValidation:
    """URL validation: warn on non-localhost URLs, stay silent on safe ones."""

    def test_default_localhost_url_no_warning(self):
        """Default localhost URL should not emit any warning."""
        with patch("embeddings.logger") as mock_logger:
            EmbeddingClient(url=DEFAULT_LMS_URL)
            mock_logger.warning.assert_not_called()

    def test_remote_url_logs_warning(self):
        """A remote (non-localhost) URL should log a security warning."""
        with patch("embeddings.logger") as mock_logger:
            EmbeddingClient(url="http://evil.com/embed")
            mock_logger.warning.assert_called_once()
            warning_msg = mock_logger.warning.call_args[0][0]
            assert "remote" in warning_msg.lower() or "localhost" in warning_msg.lower() or "warning" in warning_msg.lower() or "url" in warning_msg.lower()

    def test_127_0_0_1_url_no_warning(self):
        """Explicit 127.0.0.1 URL should not emit any warning."""
        with patch("embeddings.logger") as mock_logger:
            EmbeddingClient(url="http://127.0.0.1:1234/v1/embeddings")
            mock_logger.warning.assert_not_called()

    def test_https_remote_url_logs_warning(self):
        """An HTTPS remote URL should also log a security warning."""
        with patch("embeddings.logger") as mock_logger:
            EmbeddingClient(url="https://embeddings.example.com/v1/embeddings")
            mock_logger.warning.assert_called_once()

    def test_remote_url_does_not_raise(self):
        """Warning must not block -- client should still be constructed."""
        with patch("embeddings.logger"):
            client = EmbeddingClient(url="http://evil.com/embed")
        assert client.url == "http://evil.com/embed"


# ---------------------------------------------------------------------------
# TestEmbeddingAuth
# ---------------------------------------------------------------------------

class TestEmbeddingAuth:
    """API key support: include Authorization header when env var is set."""

    def _make_mock_client(self, mock_resp: MagicMock):
        """Return a mock httpx.AsyncClient context-manager that returns mock_resp on post()."""
        mock_post = AsyncMock(return_value=mock_resp)
        mock_instance = AsyncMock()
        mock_instance.post = mock_post
        mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_instance.__aexit__ = AsyncMock(return_value=False)
        return mock_instance, mock_post

    def test_api_key_env_var_sets_auth_header(self):
        """When LMS_EMBEDDING_API_KEY is set, the POST includes Authorization: Bearer <key>."""
        fake_key = "sk-test-secret-abc123"
        mock_instance, mock_post = self._make_mock_client(_make_ok_response())

        async def _run():
            with patch("embeddings.logger"), \
                 patch.dict("os.environ", {"LMS_EMBEDDING_API_KEY": fake_key}), \
                 patch("httpx.AsyncClient", return_value=mock_instance):
                client = EmbeddingClient()
                return await client.embed("hello world")

        result = asyncio.run(_run())
        assert result is not None
        all_kwargs = mock_post.call_args.kwargs
        assert "headers" in all_kwargs, f"Expected 'headers' kwarg in POST call, got: {mock_post.call_args}"
        assert all_kwargs["headers"].get("Authorization") == f"Bearer {fake_key}"

    def test_no_api_key_env_var_no_auth_header(self):
        """When LMS_EMBEDDING_API_KEY is not set, no Authorization header is sent."""
        import os
        mock_instance, mock_post = self._make_mock_client(_make_ok_response())
        env_without_key = {k: v for k, v in os.environ.items() if k != "LMS_EMBEDDING_API_KEY"}

        async def _run():
            with patch("embeddings.logger"), \
                 patch.dict("os.environ", env_without_key, clear=True), \
                 patch("httpx.AsyncClient", return_value=mock_instance):
                client = EmbeddingClient()
                return await client.embed("hello world")

        result = asyncio.run(_run())
        assert result is not None
        all_kwargs = mock_post.call_args.kwargs
        # Either no headers kwarg at all, or headers dict without Authorization
        headers = all_kwargs.get("headers") or {}
        assert "Authorization" not in headers, \
            f"Authorization header should not be present, got: {headers}"

    def test_api_key_bearer_format(self):
        """Authorization header must use 'Bearer <key>' format exactly."""
        fake_key = "my-super-secret-key"
        mock_instance, mock_post = self._make_mock_client(_make_ok_response())

        async def _run():
            with patch("embeddings.logger"), \
                 patch.dict("os.environ", {"LMS_EMBEDDING_API_KEY": fake_key}), \
                 patch("httpx.AsyncClient", return_value=mock_instance):
                client = EmbeddingClient()
                await client.embed("test text")

        asyncio.run(_run())
        all_kwargs = mock_post.call_args.kwargs
        assert all_kwargs["headers"]["Authorization"] == f"Bearer {fake_key}"
