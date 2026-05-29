"""Summarize-stage prompt (v1).

Prompts are kept as code per docs/PROMPTS.md — type-checked, diffable, composable.
The versioned ``prompts/<stage>/vN.py`` layout + per-call DB recording arrive with
the Week-2 prompt-versioning scaffold; for now this single module is the contract.
"""

from __future__ import annotations

from arxivdigest.domain.models import RawPaper

VERSION = "summarize/v1"

SYSTEM = (
    "You are a research-paper summarizer for working AI/ML engineers. "
    "Produce a structured TL;DR that helps a reader decide whether the full paper "
    "is worth their time. Tone: technical but accessible, no marketing language. "
    "Base every field strictly on the supplied title and abstract — never invent "
    "results, numbers, or claims the abstract does not state."
)


def build_user_prompt(paper: RawPaper) -> str:
    authors = ", ".join(paper.authors) or "unknown"
    return (
        f"Title: {paper.title}\n"
        f"Authors: {authors}\n"
        f"Categories: {', '.join(paper.categories)}\n\n"
        f"Abstract:\n{paper.abstract}"
    )
