"""Postgres repository — implements the :class:`Repository` port over asyncpg.

Writes summarized papers to the shared ``papers`` table (the schema Drizzle owns
on the TS side). ``embedding`` and ``score`` are left null here; the embed and
rank stages populate them later.
"""

from __future__ import annotations

import datetime
import uuid
from collections.abc import Sequence

import asyncpg
import structlog

from arxivdigest.adapters.observability.tracing import trace_span
from arxivdigest.domain.models import RawPaper, Run, ScoredPaper, SummarizedPaper

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

_UPSERT_RAW = """
INSERT INTO papers (arxiv_id, title, abstract, authors, categories, published_at)
VALUES ($1, $2, $3, $4, $5, $6)
ON CONFLICT (arxiv_id) DO NOTHING
"""

_FETCH_UNSUMMARIZED = """
SELECT arxiv_id, title, abstract, authors, categories, published_at
FROM papers
WHERE summary IS NULL
ORDER BY published_at DESC
LIMIT $1
"""

_UPDATE_SUMMARY = """
UPDATE papers
SET summary = $2, updated_at = now()
WHERE arxiv_id = $1
"""

_FETCH_TOP = """
SELECT id, title, themes, score
FROM papers
WHERE summary IS NOT NULL AND themes IS NOT NULL AND score IS NOT NULL
ORDER BY score DESC
LIMIT $1
"""

_UPSERT_DIGEST = """
INSERT INTO digests (date, summary, paper_ids)
VALUES ($1, $2, $3)
ON CONFLICT (date) DO UPDATE SET
    summary = EXCLUDED.summary,
    paper_ids = EXCLUDED.paper_ids
"""

_START_RUN = """
INSERT INTO runs (status) VALUES ('running') RETURNING id
"""

_COMPLETE_RUN = """
UPDATE runs
SET completed_at = now(),
    status = 'completed',
    papers_crawled = $2,
    papers_summarized = $3,
    papers_classified = $4,
    papers_embedded = $5,
    papers_ranked = $6,
    papers_published = $7
WHERE id = $1
"""

_FAIL_RUN = """
UPDATE runs
SET completed_at = now(),
    status = 'failed',
    error_summary = $2
WHERE id = $1
"""

_FETCH_RECENT_RUNS = """
SELECT id, started_at, completed_at, status,
       papers_crawled, papers_summarized, papers_classified,
       papers_embedded, papers_ranked, papers_published, error_summary
FROM runs
WHERE started_at > now() - make_interval(days => $1)
ORDER BY started_at DESC
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

_FETCH_UNRANKED = """
SELECT arxiv_id, title, abstract, authors, categories, published_at
FROM papers
WHERE score IS NULL AND embedding IS NOT NULL
ORDER BY published_at DESC
LIMIT $1
"""

# Mean cosine distance from this paper to its N nearest other embedded papers.
_NEIGHBOR_DISTANCE = """
SELECT avg(dist) FROM (
    SELECT p.embedding <=> t.embedding AS dist
    FROM papers p, (SELECT embedding FROM papers WHERE arxiv_id = $1) t
    WHERE p.embedding IS NOT NULL AND p.arxiv_id != $1
    ORDER BY p.embedding <=> t.embedding
    LIMIT $2
) nearest
"""

_UPDATE_SCORE = """
UPDATE papers
SET score = $2, updated_at = now()
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

    async def upsert_raw_papers(self, papers: Sequence[RawPaper]) -> int:
        if not papers:
            return 0
        records = [
            (p.arxiv_id, p.title, p.abstract, p.authors, p.categories, p.published_at)
            for p in papers
        ]
        with trace_span("repository.upsert_raw_papers", count=len(records)):
            async with self._pool.acquire() as conn:
                await conn.executemany(_UPSERT_RAW, records)
        log.info("repository.raw_upserted", count=len(records))
        return len(records)

    async def fetch_unsummarized(self, limit: int) -> list[RawPaper]:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(_FETCH_UNSUMMARIZED, limit)
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

    async def update_summaries(self, summaries: Sequence[tuple[str, str]]) -> int:
        if not summaries:
            return 0
        with trace_span("repository.update_summaries", count=len(summaries)):
            async with self._pool.acquire() as conn:
                await conn.executemany(_UPDATE_SUMMARY, summaries)
        log.info("repository.summaries_updated", count=len(summaries))
        return len(summaries)

    async def fetch_top_papers(self, limit: int) -> list[ScoredPaper]:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(_FETCH_TOP, limit)
        return [
            ScoredPaper(
                id=str(r["id"]),
                title=r["title"],
                themes=list(r["themes"]),
                score=r["score"],
            )
            for r in rows
        ]

    async def upsert_digest(
        self, date: datetime.date, summary: str, paper_ids: Sequence[str]
    ) -> None:
        ids = [uuid.UUID(pid) for pid in paper_ids]
        with trace_span("repository.upsert_digest", date=date.isoformat(), papers=len(ids)):
            async with self._pool.acquire() as conn:
                await conn.execute(_UPSERT_DIGEST, date, summary, ids)
        log.info("repository.digest_upserted", date=date.isoformat(), papers=len(ids))

    async def start_run(self) -> str:
        async with self._pool.acquire() as conn:
            value = await conn.fetchval(_START_RUN)
        run_id = str(value)
        log.info("run.started", run_id=run_id)
        return run_id

    async def complete_run(
        self,
        run_id: str,
        *,
        papers_crawled: int = 0,
        papers_summarized: int = 0,
        papers_classified: int = 0,
        papers_embedded: int = 0,
        papers_ranked: int = 0,
        papers_published: int = 0,
    ) -> None:
        async with self._pool.acquire() as conn:
            await conn.execute(
                _COMPLETE_RUN,
                uuid.UUID(run_id),
                papers_crawled,
                papers_summarized,
                papers_classified,
                papers_embedded,
                papers_ranked,
                papers_published,
            )
        log.info("run.completed", run_id=run_id)

    async def fail_run(self, run_id: str, error_summary: str) -> None:
        async with self._pool.acquire() as conn:
            await conn.execute(_FAIL_RUN, uuid.UUID(run_id), error_summary)
        log.info("run.failed", run_id=run_id, error=error_summary[:200])

    async def fetch_recent_runs(self, days: int) -> list[Run]:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(_FETCH_RECENT_RUNS, days)
        return [
            Run(
                id=str(r["id"]),
                started_at=r["started_at"],
                completed_at=r["completed_at"],
                status=r["status"],
                papers_crawled=r["papers_crawled"],
                papers_summarized=r["papers_summarized"],
                papers_classified=r["papers_classified"],
                papers_embedded=r["papers_embedded"],
                papers_ranked=r["papers_ranked"],
                papers_published=r["papers_published"],
                error_summary=r["error_summary"],
            )
            for r in rows
        ]

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

    async def fetch_unranked(self, limit: int) -> list[RawPaper]:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(_FETCH_UNRANKED, limit)
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

    async def mean_neighbor_distance(self, arxiv_id: str, neighbors: int) -> float | None:
        async with self._pool.acquire() as conn:
            value = await conn.fetchval(_NEIGHBOR_DISTANCE, arxiv_id, neighbors)
        return float(value) if value is not None else None

    async def update_scores(self, scores: Sequence[tuple[str, float]]) -> int:
        if not scores:
            return 0
        with trace_span("repository.update_scores", count=len(scores)):
            async with self._pool.acquire() as conn:
                await conn.executemany(_UPDATE_SCORE, scores)
        log.info("repository.scores_updated", count=len(scores))
        return len(scores)
