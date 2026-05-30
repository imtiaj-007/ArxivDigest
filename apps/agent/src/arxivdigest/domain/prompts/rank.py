"""Rank-stage prompt (v1) — LLM impact assessment."""

from __future__ import annotations

from arxivdigest.domain.models import RawPaper

VERSION = "rank/v1"

SYSTEM = (
    "You assess the likely impact of an arxiv paper for working AI/ML engineers. "
    "Rate impact from 0 to 1: 0 means routine or incremental, 1 means a landmark "
    "result likely to change practice. Be calibrated and skeptical — most papers "
    "land between 0.3 and 0.6. Judge only from the title and abstract; do not reward "
    "hype or grand claims that the abstract does not substantiate."
)


def build_user_prompt(paper: RawPaper) -> str:
    return f"Title: {paper.title}\n\nAbstract:\n{paper.abstract}"
