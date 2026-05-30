"""Gemini-backed LLM adapter — implements the :class:`LLMClient` port.

Used as the failover provider behind Groq (see :mod:`arxivdigest.adapters.llm.multi`).
Wraps Gemini 2.0 Flash via instructor's google-genai provider.
"""

from __future__ import annotations

import instructor
import structlog
from pydantic import BaseModel

from arxivdigest.adapters.observability.tracing import trace_span
from arxivdigest.domain.models import (
    Classification,
    ImpactAssessment,
    PaperSummary,
    RawPaper,
)
from arxivdigest.domain.prompts import classify as classify_prompt
from arxivdigest.domain.prompts import rank as rank_prompt
from arxivdigest.domain.prompts import summarize as summarize_prompt
from arxivdigest.domain.themes import normalize_themes

log = structlog.get_logger(__name__)

DEFAULT_MODEL = "gemini-2.0-flash-001"
_MAX_RETRIES = 2


class GeminiClient:
    """Summarizes, classifies, and scores papers via Gemini + instructor."""

    def __init__(self, api_key: str, model: str = DEFAULT_MODEL) -> None:
        self._client = instructor.from_provider(
            f"google/{model}", async_client=True, api_key=api_key
        )
        self._model = model

    async def _create[T: BaseModel](self, *, response_model: type[T], system: str, user: str) -> T:
        result: T = await self._client.chat.completions.create(
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            response_model=response_model,
            max_retries=_MAX_RETRIES,
        )
        return result

    async def summarize(self, paper: RawPaper) -> PaperSummary:
        with trace_span("gemini.summarize", arxiv_id=paper.arxiv_id, model=self._model):
            summary = await self._create(
                response_model=PaperSummary,
                system=summarize_prompt.SYSTEM,
                user=summarize_prompt.build_user_prompt(paper),
            )
        log.info("gemini.summarized", arxiv_id=paper.arxiv_id)
        return summary

    async def classify(self, paper: RawPaper) -> Classification:
        with trace_span("gemini.classify", arxiv_id=paper.arxiv_id, model=self._model):
            result = await self._create(
                response_model=Classification,
                system=classify_prompt.SYSTEM,
                user=classify_prompt.build_user_prompt(paper),
            )
        themes = normalize_themes(result.themes)
        log.info("gemini.classified", arxiv_id=paper.arxiv_id, themes=themes)
        return Classification(themes=themes)

    async def score_impact(self, paper: RawPaper) -> ImpactAssessment:
        with trace_span("gemini.score_impact", arxiv_id=paper.arxiv_id, model=self._model):
            assessment = await self._create(
                response_model=ImpactAssessment,
                system=rank_prompt.SYSTEM,
                user=rank_prompt.build_user_prompt(paper),
            )
        log.info("gemini.scored_impact", arxiv_id=paper.arxiv_id, impact=assessment.score)
        return assessment
