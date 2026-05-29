"""Voyage AI embedding adapter — implements the :class:`Embedder` port.

Uses ``voyage-3`` at 1024 dimensions to match the ``papers.embedding`` column.

Voyage's no-payment-method free tier is capped at 3 requests/min and 10K
tokens/min. The binding constraint is tokens, so this adapter chunks each call
to stay under a per-request token budget and paces successive chunks ~1 minute
apart; a tenacity retry covers any estimate slippage.
"""

from __future__ import annotations

import asyncio
from collections.abc import Sequence

import structlog
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_fixed
from voyageai.client_async import AsyncClient
from voyageai.error import RateLimitError

from arxivdigest.adapters.observability.tracing import trace_span

log = structlog.get_logger(__name__)

DEFAULT_MODEL = "voyage-3"
EMBED_DIM = 1024

# Free-tier pacing. 8K leaves margin under the 10K TPM cap; 60s between chunks
# keeps any rolling minute under both the token and request limits.
_MAX_TOKENS_PER_REQUEST = 8000
_INTER_CHUNK_DELAY_S = 60.0


def _estimate_tokens(text: str) -> int:
    """Rough token estimate (~4 chars/token). Conservative enough for budgeting."""
    return len(text) // 4 + 1


def _chunk_by_tokens(texts: Sequence[str], budget: int) -> list[list[str]]:
    """Greedily group texts so each chunk's estimated tokens stays under ``budget``.

    A single oversized text still gets its own chunk (Voyage truncates it).
    """
    chunks: list[list[str]] = []
    current: list[str] = []
    current_tokens = 0
    for text in texts:
        tokens = _estimate_tokens(text)
        if current and current_tokens + tokens > budget:
            chunks.append(current)
            current, current_tokens = [], 0
        current.append(text)
        current_tokens += tokens
    if current:
        chunks.append(current)
    return chunks


class VoyageEmbedder:
    """Embeds documents via Voyage AI, pacing requests to fit the free-tier limits."""

    def __init__(self, api_key: str, model: str = DEFAULT_MODEL) -> None:
        self._client = AsyncClient(api_key=api_key)
        self._model = model

    @retry(
        retry=retry_if_exception_type(RateLimitError),
        wait=wait_fixed(_INTER_CHUNK_DELAY_S),
        stop=stop_after_attempt(4),
        reraise=True,
    )
    async def _embed_chunk(self, texts: list[str]) -> list[list[float]]:
        result = await self._client.embed(
            texts,
            model=self._model,
            input_type="document",
            output_dimension=EMBED_DIM,
        )
        return [[float(x) for x in vector] for vector in result.embeddings]

    async def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        if not texts:
            return []
        chunks = _chunk_by_tokens(texts, _MAX_TOKENS_PER_REQUEST)
        vectors: list[list[float]] = []
        with trace_span("voyage.embed", count=len(texts), chunks=len(chunks), model=self._model):
            for i, chunk in enumerate(chunks):
                if i > 0:
                    await asyncio.sleep(_INTER_CHUNK_DELAY_S)
                vectors.extend(await self._embed_chunk(chunk))
        log.info("voyage.embedded", count=len(vectors), chunks=len(chunks))
        return vectors
