"""Port: persistence of processed papers."""

from __future__ import annotations

import datetime
from collections.abc import Sequence
from typing import Protocol

from arxivdigest.domain.models import RawPaper, Run, ScoredPaper, SummarizedPaper


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

    async def start_run(self) -> str:
        """Insert a 'running' row in ``runs`` and return its id."""
        ...

    async def sweep_stale_running(self, max_age_minutes: int = 60) -> list[str]:
        """Mark abandoned 'running' rows as failed; return swept ids.

        Recovers from SIGKILL (CI timeout, runner preemption) where the
        agent's exception handler never landed a terminal status.
        """
        ...

    async def complete_run(
        self,
        run_id: str,
        *,
        papers_crawled: int = 0,
        papers_summarized: int = 0,
        papers_classified: int = 0,
        papers_embedded: int = 0,
        papers_ranked: int = 0,
        papers_published: int = 0,
    ) -> None:
        """Mark a run as completed, set completed_at, write final per-stage counts."""
        ...

    async def fail_run(self, run_id: str, error_summary: str) -> None:
        """Mark a run as failed and record the error summary."""
        ...

    async def fetch_recent_runs(self, days: int) -> list[Run]:
        """Return runs started within the last ``days`` days, newest first."""
        ...

    async def insert_eval_run(
        self,
        *,
        ran_at: datetime.datetime,
        git_sha: str | None,
        processed: int,
        total: int,
        micro_f1: float,
        macro_f1: float,
        schema_validity_rate: float,
        avg_keyword_coverage: float,
        per_theme_f1: dict[str, float],
        per_paper: list[dict[str, object]] | None = None,
    ) -> str:
        """Persist one eval run row; return the new row id.

        Backs ``/docs/evals/history`` + the ``/about`` quality numbers + the
        README badge endpoints. Replaces the JSONL-in-git pattern.
        """
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

    async def fetch_papers_by_ids(self, arxiv_ids: Sequence[str]) -> list[RawPaper]:
        """Return papers matching the given arxiv_ids (any order; missing ones simply omitted)."""
        ...

    async def fetch_summary_map(self, arxiv_ids: Sequence[str]) -> dict[str, str | None]:
        """Return {arxiv_id: raw_summary_json (or None)} for the given ids."""
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
