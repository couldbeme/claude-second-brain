"""Embedding generation via LM Studio (primary) with graceful fallback."""

from __future__ import annotations

import logging
import os
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

DEFAULT_LMS_URL = "http://localhost:1234/v1/embeddings"
DEFAULT_MODEL = "text-embedding-nomic-embed-text-v1.5"
EMBEDDING_DIM = 768

_SAFE_URL_PREFIXES = ("http://localhost", "http://127.0.0.1")


class EmbeddingClient:
    """Generate embeddings via LM Studio's OpenAI-compatible API."""

    def __init__(
        self,
        url: str = DEFAULT_LMS_URL,
        model: str = DEFAULT_MODEL,
        timeout: float = 30.0,
    ):
        self.url = url
        self.model = model
        self.timeout = timeout
        self._available: Optional[bool] = None

        if not any(url.startswith(prefix) for prefix in _SAFE_URL_PREFIXES):
            logger.warning(
                "Embedding URL %r is not a localhost address -- remote URL may "
                "exfiltrate text to an untrusted server. Set LMS_EMBEDDING_URL "
                "to a localhost address to silence this warning.",
                url,
            )

    async def is_available(self) -> bool:
        """Check if the embedding service is reachable."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(self.url.replace("/embeddings", "/models"))
                self._available = resp.status_code == 200
        except (httpx.ConnectError, httpx.TimeoutException):
            self._available = False
        return self._available

    async def embed(self, text: str) -> Optional[list[float]]:
        """Generate an embedding for the given text. Returns None if service unavailable."""
        headers: dict[str, str] = {}
        api_key = os.environ.get("LMS_EMBEDDING_API_KEY")
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(
                    self.url,
                    json={"input": text, "model": self.model},
                    headers=headers,
                )
                resp.raise_for_status()
                data = resp.json()
                embedding = data["data"][0]["embedding"]
                # Ensure correct dimension
                if len(embedding) != EMBEDDING_DIM:
                    logger.warning(
                        "Embedding dim %d != expected %d, padding/truncating",
                        len(embedding),
                        EMBEDDING_DIM,
                    )
                    if len(embedding) > EMBEDDING_DIM:
                        embedding = embedding[:EMBEDDING_DIM]
                    else:
                        embedding.extend([0.0] * (EMBEDDING_DIM - len(embedding)))
                return embedding
        except (httpx.ConnectError, httpx.TimeoutException) as e:
            logger.warning("Embedding service unavailable: %s", e)
            return None
        except (httpx.HTTPStatusError, KeyError, IndexError) as e:
            logger.error("Embedding request failed: %s", e)
            return None

    async def embed_batch(self, texts: list[str]) -> list[Optional[list[float]]]:
        """Generate embeddings for multiple texts."""
        results = []
        for text in texts:
            results.append(await self.embed(text))
        return results
