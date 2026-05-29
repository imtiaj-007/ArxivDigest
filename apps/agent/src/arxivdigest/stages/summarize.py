"""Summarize stage — crawl recent papers, summarize each, persist.

Orchestrates the ports only (PaperSource, LLMClient, Repository); it has no
knowledge of arxiv, Groq, or Postgres. A per-paper bulkhead keeps one bad
summary from sinking the whole run.
"""

from __future__ import annotations

from collections.abc import Sequence

import structlog

from arxivdigest.adapters.observability.tracing import trace_span
from arxivdigest.domain.models import SummarizedPaper
from arxivdigest.ports.llm import LLMClient
from arxivdigest.ports.repository import Repository
from arxivdigest.ports.source import PaperSource

log = structlog.get_logger(__name__)


async def run_summarize_stage(
    source: PaperSource,
    summarizer: LLMClient,
    repository: Repository,
    *,
    categories: Sequence[str],
    limit: int,
    dry_run: bool = False,
) -> list[SummarizedPaper]:
    """Fetch up to ``limit`` recent papers, summarize each, and (unless dry-run) persist.

    Returns the successfully summarized papers.
    """
    with trace_span("stage.summarize", limit=limit, dry_run=dry_run):
        papers = await source.fetch_recent(categories, limit)

        summarized: list[SummarizedPaper] = []
        for paper in papers:
            try:
                summary = await summarizer.summarize(paper)
            except Exception:
                # Bulkhead: log and skip this paper, keep processing the rest.
                log.exception("summarize.paper_failed", arxiv_id=paper.arxiv_id)
                continue
            summarized.append(SummarizedPaper(paper=paper, summary=summary))

        if dry_run:
            log.info("summarize.dry_run", summarized=len(summarized), crawled=len(papers))
        else:
            written = await repository.upsert_papers(summarized)
            log.info(
                "summarize.persisted",
                written=written,
                summarized=len(summarized),
                crawled=len(papers),
            )
    return summarized
