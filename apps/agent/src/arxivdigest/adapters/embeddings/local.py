"""Local sentence-transformers embedder — implements the :class:`Embedder` port.

Runs ``BAAI/bge-large-en-v1.5`` (1024d, English, MTEB-strong) on CPU. Loaded
lazily on first ``embed_documents`` call so importing this module is cheap
(the model itself is ~1.3 GB, downloaded once and cached under
``~/.cache/huggingface/hub``).

Why local: forever-free, no API key, no rate limit, no payment method. The
sync ``.encode`` call runs in a thread via ``asyncio.to_thread`` so the
event loop stays responsive.
"""

from __future__ import annotations

import asyncio
from collections.abc import Sequence

import structlog
from sentence_transformers import SentenceTransformer

from arxivdigest.adapters.observability.tracing import trace_span

log = structlog.get_logger(__name__)

DEFAULT_MODEL = "BAAI/bge-large-en-v1.5"
EMBED_DIM = 1024


class LocalBGEEmbedder:
    """Embeds documents locally via sentence-transformers / BGE."""

    def __init__(self, model: str = DEFAULT_MODEL) -> None:
        self._model_name = model
        self._model: SentenceTransformer | None = None

    def _load(self) -> SentenceTransformer:
        if self._model is None:
            log.info("local_embedder.loading", model=self._model_name)
            self._model = SentenceTransformer(self._model_name, device="cpu")
        return self._model

    async def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        if not texts:
            return []
        with trace_span("local.embed", count=len(texts), model=self._model_name):
            vectors = await asyncio.to_thread(self._encode, list(texts))
        log.info("local_embedder.embedded", count=len(vectors))
        return vectors

    def _encode(self, texts: list[str]) -> list[list[float]]:
        model = self._load()
        # normalize_embeddings: cosine similarity becomes a dot product; matches
        # how our pgvector HNSW index (vector_cosine_ops) ranks neighbors.
        array = model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
        return [[float(x) for x in vector] for vector in array]
