"""Port: LLM-backed operations over papers.

One port per provider-swappable capability. For the Week-1 slice that is just
``summarize``; classify/rank land here as the pipeline grows.
"""

from __future__ import annotations

from typing import Protocol

from arxivdigest.domain.models import Classification, PaperSummary, RawPaper


class LLMClient(Protocol):
    """An LLM provider for the paper-processing operations."""

    async def summarize(self, paper: RawPaper) -> PaperSummary:
        """Produce a structured :class:`PaperSummary` from a paper's title + abstract."""
        ...

    async def classify(self, paper: RawPaper) -> Classification:
        """Assign 1-3 taxonomy themes to a paper."""
        ...
