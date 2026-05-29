"""Crawl stage — ingest recent arxiv papers as bare rows.

Writes only the crawled metadata (no summary/themes/embedding/score); the
downstream stages backfill those. Idempotent: ON CONFLICT DO NOTHING, so
re-crawling never clobbers already-processed papers.
"""

from __future__ import annotations

from collections.abc import Sequence

import structlog

from arxivdigest.adapters.observability.tracing import trace_span
from arxivdigest.ports.repository import Repository
from arxivdigest.ports.source import PaperSource

log = structlog.get_logger(__name__)


async def run_crawl_stage(
    source: PaperSource,
    repository: Repository,
    *,
    categories: Sequence[str],
    limit: int,
) -> int:
    """Fetch up to ``limit`` recent papers and upsert them as bare rows."""
    with trace_span("stage.crawl", limit=limit):
        papers = await source.fetch_recent(categories, limit)
        written = await repository.upsert_raw_papers(papers)
        log.info("crawl.persisted", crawled=len(papers), written=written)
    return written
