"""Summarize stage — backfill summaries for papers that lack one.

Idempotent and status-driven: operates on rows where ``summary IS NULL`` (the
crawl stage ingests bare rows first). Per-paper bulkhead keeps one bad summary
from sinking the run.
"""

from __future__ import annotations

import structlog

from arxivdigest.adapters.observability.tracing import trace_span
from arxivdigest.ports.llm import LLMClient
from arxivdigest.ports.repository import Repository

log = structlog.get_logger(__name__)


async def run_summarize_stage(summarizer: LLMClient, repository: Repository, *, limit: int) -> int:
    """Summarize up to ``limit`` un-summarized papers and persist the summaries."""
    with trace_span("stage.summarize", limit=limit):
        papers = await repository.fetch_unsummarized(limit)
        if not papers:
            log.info("summarize.nothing_to_do")
            return 0

        updates: list[tuple[str, str]] = []
        for paper in papers:
            try:
                summary = await summarizer.summarize(paper)
            except Exception:
                log.exception("summarize.paper_failed", arxiv_id=paper.arxiv_id)
                continue
            updates.append((paper.arxiv_id, summary.model_dump_json()))

        written = await repository.update_summaries(updates)
        log.info("summarize.persisted", written=written, fetched=len(papers))
    return written
