"""Rank stage — score papers by novelty + LLM-judged impact.

Novelty comes from how far a paper sits from its nearest neighbors in embedding
space (pgvector cosine distance); impact is an LLM assessment. The two are
blended into ``papers.score``. Idempotent on ``score IS NULL``; requires the
embed stage to have run first.
"""

from __future__ import annotations

import structlog

from arxivdigest.adapters.observability.tracing import trace_span
from arxivdigest.domain.ranking import blend_score
from arxivdigest.ports.llm import LLMClient
from arxivdigest.ports.repository import Repository

log = structlog.get_logger(__name__)

_NEIGHBORS = 5


async def run_rank_stage(ranker: LLMClient, repository: Repository, *, limit: int) -> int:
    """Score up to ``limit`` unranked (but embedded) papers and persist the scores."""
    with trace_span("stage.rank", limit=limit):
        papers = await repository.fetch_unranked(limit)
        if not papers:
            log.info("rank.nothing_to_do")
            return 0

        updates: list[tuple[str, float]] = []
        for paper in papers:
            try:
                novelty = await repository.mean_neighbor_distance(paper.arxiv_id, _NEIGHBORS)
                impact = await ranker.score_impact(paper)
            except Exception:
                log.exception("rank.paper_failed", arxiv_id=paper.arxiv_id)
                continue
            score = blend_score(novelty, impact.score)
            updates.append((paper.arxiv_id, score))

        written = await repository.update_scores(updates)
        log.info("rank.persisted", written=written, fetched=len(papers))
    return written
