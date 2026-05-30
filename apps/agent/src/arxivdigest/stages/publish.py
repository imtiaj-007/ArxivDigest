"""Publish stage — assemble the day's digest row from the top-ranked papers.

V0 builds a templated summary (count + leading themes + top titles). An
LLM-written overview can replace ``_build_summary`` later. Idempotent: upserts
one digest row per date.
"""

from __future__ import annotations

import datetime
from collections import Counter
from collections.abc import Sequence

import structlog

from arxivdigest.adapters.observability.tracing import trace_span
from arxivdigest.domain.models import ScoredPaper
from arxivdigest.ports.repository import Repository

log = structlog.get_logger(__name__)

DEFAULT_TOP_K = 10
_HIGHLIGHTS = 5


def _build_summary(papers: Sequence[ScoredPaper]) -> str:
    theme_counts = Counter(theme for paper in papers for theme in paper.themes)
    top_themes = ", ".join(slug for slug, _ in theme_counts.most_common(5)) or "—"
    lines = [f"Top {len(papers)} papers today. Leading themes: {top_themes}.", ""]
    lines += [f"- ({paper.score:.2f}) {paper.title}" for paper in papers[:_HIGHLIGHTS]]
    return "\n".join(lines)


async def run_publish_stage(
    repository: Repository,
    *,
    top_k: int = DEFAULT_TOP_K,
    date: datetime.date | None = None,
) -> int:
    """Write/refresh the digest for ``date`` (default: today UTC) from the top papers."""
    digest_date = date or datetime.datetime.now(datetime.UTC).date()
    with trace_span("stage.publish", date=digest_date.isoformat(), top_k=top_k):
        top = await repository.fetch_top_papers(top_k)
        if not top:
            log.info("publish.nothing_to_do")
            return 0
        summary = _build_summary(top)
        await repository.upsert_digest(digest_date, summary, [paper.id for paper in top])
        log.info("publish.persisted", date=digest_date.isoformat(), papers=len(top))
    return len(top)
