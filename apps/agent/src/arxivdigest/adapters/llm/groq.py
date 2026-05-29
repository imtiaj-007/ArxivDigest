"""Groq-backed LLM adapter — implements the :class:`LLMClient` port.

Uses ``instructor`` to coerce model JSON into validated Pydantic models. A
tenacity backoff wraps every call so Groq rate-limit spikes (429) are retried
rather than dropped. Model split: summarize uses the 70B workhorse; classify
and impact scoring use the cheaper/higher-limit 8B instant model.
"""

from __future__ import annotations

import instructor
import structlog
from groq import AsyncGroq, RateLimitError
from instructor.exceptions import InstructorRetryException
from pydantic import BaseModel
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

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

# Groq's hosted Llama models per STACK.md.
DEFAULT_HEAVY_MODEL = "llama-3.3-70b-versatile"  # summarize
DEFAULT_FAST_MODEL = "llama-3.1-8b-instant"  # classify + impact

# Low temperature: faithful summaries + stable classification/scoring.
_TEMPERATURE = 0.2
# instructor re-prompts this many times if the model returns invalid JSON.
_MAX_RETRIES = 2


class GroqClient:
    """Summarizes, classifies, and scores papers via Groq + instructor."""

    def __init__(
        self,
        api_key: str,
        heavy_model: str = DEFAULT_HEAVY_MODEL,
        fast_model: str = DEFAULT_FAST_MODEL,
    ) -> None:
        self._client = instructor.from_groq(AsyncGroq(api_key=api_key), mode=instructor.Mode.JSON)
        self._heavy_model = heavy_model
        self._fast_model = fast_model

    @retry(
        retry=retry_if_exception_type((RateLimitError, InstructorRetryException)),
        wait=wait_exponential(multiplier=2, min=5, max=45),
        stop=stop_after_attempt(6),
        reraise=True,
    )
    async def _create[T: BaseModel](
        self, *, model: str, response_model: type[T], system: str, user: str
    ) -> T:
        result: T = await self._client.chat.completions.create(
            model=model,
            response_model=response_model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=_TEMPERATURE,
            max_retries=_MAX_RETRIES,
        )
        return result

    async def summarize(self, paper: RawPaper) -> PaperSummary:
        with trace_span(
            "groq.summarize",
            arxiv_id=paper.arxiv_id,
            model=self._heavy_model,
            prompt_version=summarize_prompt.VERSION,
        ):
            summary = await self._create(
                model=self._heavy_model,
                response_model=PaperSummary,
                system=summarize_prompt.SYSTEM,
                user=summarize_prompt.build_user_prompt(paper),
            )
        log.info("groq.summarized", arxiv_id=paper.arxiv_id)
        return summary

    async def classify(self, paper: RawPaper) -> Classification:
        with trace_span(
            "groq.classify",
            arxiv_id=paper.arxiv_id,
            model=self._fast_model,
            prompt_version=classify_prompt.VERSION,
        ):
            result = await self._create(
                model=self._fast_model,
                response_model=Classification,
                system=classify_prompt.SYSTEM,
                user=classify_prompt.build_user_prompt(paper),
            )
        # Guard against invented or excess slugs before the value leaves the adapter.
        themes = normalize_themes(result.themes)
        log.info("groq.classified", arxiv_id=paper.arxiv_id, themes=themes)
        return Classification(themes=themes)

    async def score_impact(self, paper: RawPaper) -> ImpactAssessment:
        with trace_span(
            "groq.score_impact",
            arxiv_id=paper.arxiv_id,
            model=self._fast_model,
            prompt_version=rank_prompt.VERSION,
        ):
            assessment = await self._create(
                model=self._fast_model,
                response_model=ImpactAssessment,
                system=rank_prompt.SYSTEM,
                user=rank_prompt.build_user_prompt(paper),
            )
        log.info("groq.scored_impact", arxiv_id=paper.arxiv_id, impact=assessment.score)
        return assessment
