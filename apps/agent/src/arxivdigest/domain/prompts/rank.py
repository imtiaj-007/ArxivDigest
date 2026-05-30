"""Rank-stage prompt (v2) — LLM impact assessment.

v2 (2026-05-30): tightened output-shape contract. The 8B model would
occasionally return `[{"description": "..."}]` (array-wrapped, wrong field
names) instead of `{"score": ..., "reasoning": ...}`, defeating instructor's
schema validation; the additional explicit-shape rules eliminate that drift.
"""

from __future__ import annotations

from arxivdigest.domain.models import RawPaper

VERSION = "rank/v2"

SYSTEM = (
    "You assess the likely impact of an arxiv paper for working AI/ML engineers. "
    "Rate impact from 0 to 1: 0 means routine or incremental, 1 means a landmark "
    "result likely to change practice. Be calibrated and skeptical — most papers "
    "land between 0.3 and 0.6. Judge only from the title and abstract; do not reward "
    "hype or grand claims that the abstract does not substantiate.\n\n"
    "Output format (strict): return ONLY a single JSON object with exactly two keys: "
    '`score` (a number between 0 and 1) and `reasoning` (one sentence explaining the score). '
    "Do NOT wrap the object in an array. Do NOT include any other keys, prefaces, or commentary."
)


def build_user_prompt(paper: RawPaper) -> str:
    return f"Title: {paper.title}\n\nAbstract:\n{paper.abstract}"
