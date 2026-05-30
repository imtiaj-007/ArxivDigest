"""Port: persistence of processed papers."""

from __future__ import annotations

import datetime
from collections.abc import Sequence
from typing import Protocol

from arxivdigest.domain.models import RawPaper, ScoredPaper, SummarizedPaper


class Repository(Protocol):
    """Stores summarized papers, idempotent on arxiv_id."""

    async def upsert_papers(self, papers: Sequence[SummarizedPaper]) -> int:
        """Insert or update each paper by arxiv_id. Returns the number written."""
        ...

    async def upsert_raw_papers(self, papers: Sequence[RawPaper]) -> int:
        """Insert crawled papers as bare rows (no generated fields). Returns the number written."""
        ...

    async def fetch_unsummarized(self, limit: int) -> list[RawPaper]:
        """Return up to ``limit`` papers that have no summary yet."""
        ...

    async def update_summaries(self, summaries: Sequence[tuple[str, str]]) -> int:
        """Set summary JSON for each (arxiv_id, summary). Returns the number updated."""
        ...

    async def fetch_top_papers(self, limit: int) -> list[ScoredPaper]:
        """Return the top ``limit`` fully-processed papers by score."""
        ...

    async def upsert_digest(
        self, date: datetime.date, summary: str, paper_ids: Sequence[str]
    ) -> None:
        """Insert or update the digest for ``date``."""
        ...

    async def fetch_unembedded(self, limit: int) -> list[tuple[str, str, str]]:
        """Return up to ``limit`` (arxiv_id, title, abstract) for papers lacking an embedding."""
        ...

    async def update_embeddings(self, embeddings: Sequence[tuple[str, str]]) -> int:
        """Set the embedding for each (arxiv_id, pgvector_literal). Returns the number updated."""
        ...

    async def fetch_unclassified(self, limit: int) -> list[RawPaper]:
        """Return up to ``limit`` papers that have no themes yet."""
        ...

    async def update_themes(self, themes: Sequence[tuple[str, list[str]]]) -> int:
        """Set themes for each (arxiv_id, theme_slugs). Returns the number updated."""
        ...

    async def fetch_unranked(self, limit: int) -> list[RawPaper]:
        """Return up to ``limit`` embedded-but-unscored papers."""
        ...

    async def mean_neighbor_distance(self, arxiv_id: str, neighbors: int) -> float | None:
        """Mean cosine distance from this paper to its ``neighbors`` nearest others.

        Higher = more novel. None when there are no other embedded papers.
        """
        ...

    async def update_scores(self, scores: Sequence[tuple[str, float]]) -> int:
        """Set the score for each (arxiv_id, score). Returns the number updated."""
        ...
