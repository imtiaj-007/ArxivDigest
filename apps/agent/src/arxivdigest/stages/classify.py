"""Classify stage — assign taxonomy themes to papers that lack them.

Idempotent and status-driven: operates on rows where ``themes IS NULL``, so
re-running only processes the unclassified. Per-paper bulkhead keeps one bad
classification from sinking the run.
"""

from __future__ import annotations

import structlog

from arxivdigest.adapters.observability.tracing import trace_span
from arxivdigest.ports.llm import LLMClient
from arxivdigest.ports.repository import Repository

log = structlog.get_logger(__name__)


async def run_classify_stage(classifier: LLMClient, repository: Repository, *, limit: int) -> int:
    """Classify up to ``limit`` un-themed papers and persist their themes."""
    with trace_span("stage.classify", limit=limit):
        papers = await repository.fetch_unclassified(limit)
        if not papers:
            log.info("classify.nothing_to_do")
            return 0

        updates: list[tuple[str, list[str]]] = []
        for paper in papers:
            try:
                classification = await classifier.classify(paper)
            except Exception:
                log.exception("classify.paper_failed", arxiv_id=paper.arxiv_id)
                continue
            updates.append((paper.arxiv_id, classification.themes))

        written = await repository.update_themes(updates)
        log.info("classify.persisted", written=written, fetched=len(papers))
    return written
