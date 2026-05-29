"""Core domain entities — pure data, no I/O.

These models are the contract the pipeline stages pass between each other and
the shape adapters translate to/from (arxiv Atom, Groq JSON, Postgres rows).
"""

from __future__ import annotations

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
