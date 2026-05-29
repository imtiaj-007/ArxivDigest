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
from arxivdigest.domain.models import RawPaper, SummarizedPaper

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

_FETCH_UNEMBEDDED = """
SELECT arxiv_id, title, abstract
FROM papers
WHERE embedding IS NULL
ORDER BY published_at DESC
LIMIT $1
"""

_UPDATE_EMBEDDING = """
UPDATE papers
SET embedding = $2::vector, updated_at = now()
WHERE arxiv_id = $1
"""

_FETCH_UNCLASSIFIED = """
SELECT arxiv_id, title, abstract, authors, categories, published_at
FROM papers
WHERE themes IS NULL
ORDER BY published_at DESC
LIMIT $1
"""

_UPDATE_THEMES = """
UPDATE papers
SET themes = $2, updated_at = now()
WHERE arxiv_id = $1
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

    async def fetch_unembedded(self, limit: int) -> list[tuple[str, str, str]]:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(_FETCH_UNEMBEDDED, limit)
        return [(r["arxiv_id"], r["title"], r["abstract"]) for r in rows]

    async def update_embeddings(self, embeddings: Sequence[tuple[str, str]]) -> int:
        if not embeddings:
            return 0
        with trace_span("repository.update_embeddings", count=len(embeddings)):
            async with self._pool.acquire() as conn:
                await conn.executemany(_UPDATE_EMBEDDING, embeddings)
        log.info("repository.embeddings_updated", count=len(embeddings))
        return len(embeddings)

    async def fetch_unclassified(self, limit: int) -> list[RawPaper]:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(_FETCH_UNCLASSIFIED, limit)
        return [
            RawPaper(
                arxiv_id=r["arxiv_id"],
                title=r["title"],
                abstract=r["abstract"],
                authors=list(r["authors"]),
                categories=list(r["categories"]),
                published_at=r["published_at"],
            )
            for r in rows
        ]

    async def update_themes(self, themes: Sequence[tuple[str, list[str]]]) -> int:
        if not themes:
            return 0
        with trace_span("repository.update_themes", count=len(themes)):
            async with self._pool.acquire() as conn:
                await conn.executemany(_UPDATE_THEMES, themes)
        log.info("repository.themes_updated", count=len(themes))
        return len(themes)
