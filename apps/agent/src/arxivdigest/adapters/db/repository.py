"""Postgres repository — implements the :class:`Repository` port over asyncpg.

Writes summarized papers to the shared ``papers`` table (the schema Drizzle owns
on the TS side). ``embedding`` and ``score`` are left null here; the embed and
rank stages populate them later.
"""

from __future__ import annotations

from collections.abc import Sequence

import asyncpg
import structlog

from arxivdigest.adapters.observability.tracing import trace_span
from arxivdigest.domain.models import SummarizedPaper

log = structlog.get_logger(__name__)

_UPSERT = """
INSERT INTO papers (arxiv_id, title, abstract, authors, categories, published_at, summary)
VALUES ($1, $2, $3, $4, $5, $6, $7)
ON CONFLICT (arxiv_id) DO UPDATE SET
    title = EXCLUDED.title,
    abstract = EXCLUDED.abstract,
    authors = EXCLUDED.authors,
    categories = EXCLUDED.categories,
    published_at = EXCLUDED.published_at,
    summary = EXCLUDED.summary,
    updated_at = now()
"""


class PostgresRepository:
    """Persists summarized papers, idempotent on arxiv_id."""

    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def upsert_papers(self, papers: Sequence[SummarizedPaper]) -> int:
        if not papers:
            return 0
        records = [
            (
                sp.paper.arxiv_id,
                sp.paper.title,
                sp.paper.abstract,
                sp.paper.authors,
                sp.paper.categories,
                sp.paper.published_at,
                sp.summary.model_dump_json(),
            )
            for sp in papers
        ]
        with trace_span("repository.upsert_papers", count=len(records)):
            async with self._pool.acquire() as conn:
                await conn.executemany(_UPSERT, records)
        log.info("repository.upserted", count=len(records))
        return len(records)
