"""Port: persistence of processed papers."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from arxivdigest.domain.models import SummarizedPaper


class Repository(Protocol):
    """Stores summarized papers, idempotent on arxiv_id."""

    async def upsert_papers(self, papers: Sequence[SummarizedPaper]) -> int:
        """Insert or update each paper by arxiv_id. Returns the number written."""
        ...
