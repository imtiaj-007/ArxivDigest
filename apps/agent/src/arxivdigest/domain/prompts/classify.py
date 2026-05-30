"""Classify-stage prompt (v1)."""

from __future__ import annotations

from arxivdigest.domain.models import RawPaper
from arxivdigest.domain.themes import taxonomy_for_prompt

VERSION = "classify/v1"

SYSTEM = (
    "You classify arxiv papers into research themes. Choose the 1-3 themes that "
    "best describe the paper, using ONLY the slugs from the provided taxonomy. "
    "Prefer fewer, more specific themes over many loose ones. Return the slugs, "
    "most relevant first."
)


def build_user_prompt(paper: RawPaper) -> str:
    return (
        f"Taxonomy (slug: description):\n{taxonomy_for_prompt()}\n\n"
        f"Title: {paper.title}\n\n"
        f"Abstract:\n{paper.abstract}"
    )
