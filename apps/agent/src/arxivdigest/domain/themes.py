"""Curated theme taxonomy for classification.

V0 keeps the taxonomy in code (vs the DB ``themes`` table in ARCHITECTURE.md) —
simpler to evolve and diff while the set is still settling. ``other`` is the
fallback when nothing else fits, so a paper always gets at least one theme.
"""

from __future__ import annotations

from collections.abc import Sequence

from pydantic import BaseModel

_MAX_THEMES = 3


class Theme(BaseModel):
    slug: str
    name: str
    description: str


THEMES: list[Theme] = [
    Theme(slug="llm", name="Large Language Models",
          description="LLM architectures, training, scaling, inference."),
    Theme(slug="agents", name="Agents & Tool Use",
          description="Autonomous agents, planning, tool/function calling, multi-agent systems."),
    Theme(slug="retrieval", name="Retrieval & RAG",
          description="Retrieval-augmented generation, embeddings, vector search, memory."),
    Theme(slug="reasoning", name="Reasoning",
          description="Chain-of-thought, math, code, planning, problem-solving."),
    Theme(slug="efficiency", name="Efficiency & Systems",
          description="Quantization, distillation, KV-cache, serving, inference speedups."),
    Theme(slug="rl", name="Reinforcement Learning",
          description="RL, RLHF, preference optimization, alignment training."),
    Theme(slug="vision", name="Computer Vision",
          description="Image/video understanding, generation, diffusion, multimodal vision."),
    Theme(slug="multimodal", name="Multimodal",
          description="Vision-language, audio, cross-modal models and benchmarks."),
    Theme(slug="speech", name="Speech & Audio",
          description="ASR, TTS, audio generation and understanding."),
    Theme(slug="robotics", name="Robotics & Embodied AI",
          description="Manipulation, control, embodied agents, sim-to-real."),
    Theme(slug="safety", name="Safety & Alignment",
          description="Alignment, interpretability, red-teaming, evaluation of risks."),
    Theme(slug="data", name="Data & Benchmarks",
          description="Datasets, benchmarks, evaluation methodology, data curation."),
    Theme(slug="theory", name="ML Theory",
          description="Optimization, generalization, learning theory, statistics."),
    Theme(slug="other", name="Other",
          description="Anything that doesn't fit the themes above."),
]

THEME_SLUGS: frozenset[str] = frozenset(theme.slug for theme in THEMES)
FALLBACK_THEME = "other"


def taxonomy_for_prompt() -> str:
    """Render the taxonomy as ``slug — description`` lines for an LLM prompt."""
    return "\n".join(f"- {theme.slug}: {theme.description}" for theme in THEMES)


def normalize_themes(raw: Sequence[str]) -> list[str]:
    """Keep only known slugs (deduped, order-preserved, capped); fall back if empty.

    Guards against the LLM inventing slugs or returning too many — so the stage
    always persists a valid 1-to-``_MAX_THEMES`` theme list.
    """
    seen: list[str] = []
    for slug in raw:
        candidate = slug.strip().lower()
        if candidate in THEME_SLUGS and candidate not in seen:
            seen.append(candidate)
    if not seen:
        return [FALLBACK_THEME]
    return seen[:_MAX_THEMES]
