"""Embed stage — backfill embeddings for papers that lack one.

Idempotent and status-driven: it operates on rows where ``embedding IS NULL``,
so re-running only processes what's missing (no mass backfill needed).
"""

from __future__ import annotations

import structlog

from arxivdigest.adapters.observability.tracing import trace_span
from arxivdigest.ports.embeddings import Embedder
from arxivdigest.ports.repository import Repository

log = structlog.get_logger(__name__)


def _to_pgvector(vector: list[float]) -> str:
    """Render a float vector as a pgvector text literal: ``[0.1,0.2,...]``."""
    return "[" + ",".join(repr(x) for x in vector) + "]"


async def run_embed_stage(embedder: Embedder, repository: Repository, *, limit: int) -> int:
    """Embed up to ``limit`` un-embedded papers (title + abstract) and persist the vectors."""
    with trace_span("stage.embed", limit=limit):
        rows = await repository.fetch_unembedded(limit)
        if not rows:
            log.info("embed.nothing_to_do")
            return 0

        texts = [f"{title}\n\n{abstract}" for _arxiv_id, title, abstract in rows]
        vectors = await embedder.embed_documents(texts)

        updates = [
            (arxiv_id, _to_pgvector(vector))
            for (arxiv_id, _title, _abstract), vector in zip(rows, vectors, strict=True)
        ]
        written = await repository.update_embeddings(updates)
        log.info("embed.persisted", written=written, fetched=len(rows))
    return written
