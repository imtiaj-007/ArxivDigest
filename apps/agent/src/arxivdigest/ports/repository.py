"""Port: persistence of processed papers."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from arxivdigest.domain.models import RawPaper, SummarizedPaper


class Repository(Protocol):
    """Stores summarized papers, idempotent on arxiv_id."""

    async def upsert_papers(self, papers: Sequence[SummarizedPaper]) -> int:
        """Insert or update each paper by arxiv_id. Returns the number written."""
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
