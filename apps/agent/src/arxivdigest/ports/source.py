"""Port: a source of papers to process."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from arxivdigest.domain.models import RawPaper


class PaperSource(Protocol):
    """Fetches recent papers for a set of arxiv categories."""

    async def fetch_recent(
        self,
        categories: Sequence[str],
        limit: int,
    ) -> list[RawPaper]:
        """Return up to ``limit`` of the most recent submissions across ``categories``."""
        ...
