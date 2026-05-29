"""Ranking math — pure, no I/O.

Blends a novelty signal (how far a paper sits from its nearest neighbors in
embedding space) with an LLM impact score into the final ``papers.score``.
"""

from __future__ import annotations

NOVELTY_WEIGHT = 0.4
IMPACT_WEIGHT = 0.6
# Used when a paper has no neighbors yet (e.g. first paper of a run).
_NEUTRAL_NOVELTY = 0.5


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


def blend_score(novelty: float | None, impact: float) -> float:
    """Combine novelty (cosine distance to neighbors) and impact into a 0-1 score."""
    novelty_component = _NEUTRAL_NOVELTY if novelty is None else _clamp(novelty)
    return round(NOVELTY_WEIGHT * novelty_component + IMPACT_WEIGHT * _clamp(impact), 4)
