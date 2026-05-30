"""Core domain entities — pure data, no I/O.

These models are the contract the pipeline stages pass between each other and
the shape adapters translate to/from (arxiv Atom, Groq JSON, Postgres rows).
"""

from __future__ import annotations

import datetime as _dt
from datetime import datetime

from pydantic import BaseModel, Field


class RawPaper(BaseModel):
    """A paper as crawled from arxiv, before any LLM processing."""

    arxiv_id: str = Field(description="arxiv identifier, e.g. '2401.01234' (version stripped)")
    title: str
    abstract: str
    authors: list[str] = Field(default_factory=list)
    categories: list[str] = Field(default_factory=list, description="arxiv category tags")
    published_at: datetime
    pdf_url: str | None = None


class PaperSummary(BaseModel):
    """Structured TL;DR produced by the summarize stage.

    Field descriptions double as extraction guidance for the instructor-backed
    LLM call — keep them tight and answerable from an abstract alone.
    """

    problem: str = Field(description="The problem or gap the paper addresses, in one sentence.")
    approach: str = Field(description="The core method or idea the authors propose.")
    result: str = Field(description="The main quantitative or qualitative result.")
    why_it_matters: str = Field(description="Why a practitioner should care, in one sentence.")


class SummarizedPaper(BaseModel):
    """A crawled paper paired with its generated summary — the unit persisted to DB."""

    paper: RawPaper
    summary: PaperSummary


class Classification(BaseModel):
    """Theme assignment produced by the classify stage."""

    themes: list[str] = Field(
        description="1-3 theme slugs from the provided taxonomy, most relevant first."
    )


class ScoredPaper(BaseModel):
    """A fully-processed paper row, used by the publish stage to build a digest."""

    id: str
    title: str
    themes: list[str]
    score: float


class ImpactAssessment(BaseModel):
    """LLM judgement of a paper's likely impact, used by the rank stage."""

    score: float = Field(
        ge=0.0,
        le=1.0,
        description="Likely impact: 0 = routine/incremental, 1 = landmark that changes practice.",
    )
    reasoning: str = Field(description="One-sentence justification for the score.")


class Run(BaseModel):
    """A single execution of the pipeline; one row in the ``runs`` table."""

    id: str
    started_at: _dt.datetime
    completed_at: _dt.datetime | None = None
    status: str  # 'running' | 'completed' | 'failed'
    papers_crawled: int = 0
    papers_summarized: int = 0
    papers_classified: int = 0
    papers_embedded: int = 0
    papers_ranked: int = 0
    papers_published: int = 0
    error_summary: str | None = None
