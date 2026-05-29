"""Groq-backed LLM adapter — implements the :class:`LLMClient` port.

Uses ``instructor`` to coerce model JSON into validated Pydantic models, with
automatic re-prompting on validation failure. Summarize uses the 70B workhorse;
classify uses the cheaper/faster 8B instant model.
"""

from __future__ import annotations

import instructor
import structlog
from groq import AsyncGroq

from arxivdigest.adapters.observability.tracing import trace_span
from arxivdigest.domain.models import Classification, PaperSummary, RawPaper
from arxivdigest.domain.prompts import classify as classify_prompt
from arxivdigest.domain.prompts import summarize as summarize_prompt
from arxivdigest.domain.themes import normalize_themes

log = structlog.get_logger(__name__)

# Groq's hosted Llama models per STACK.md.
DEFAULT_SUMMARIZE_MODEL = "llama-3.3-70b-versatile"
DEFAULT_CLASSIFY_MODEL = "llama-3.1-8b-instant"

# Low temperature: faithful summaries + stable classification.
_TEMPERATURE = 0.2
# instructor re-prompts this many times if the model returns invalid JSON.
_MAX_RETRIES = 2


class GroqClient:
    """Summarizes and classifies papers via Groq + instructor."""

    def __init__(
        self,
        api_key: str,
        summarize_model: str = DEFAULT_SUMMARIZE_MODEL,
        classify_model: str = DEFAULT_CLASSIFY_MODEL,
    ) -> None:
        self._client = instructor.from_groq(AsyncGroq(api_key=api_key), mode=instructor.Mode.JSON)
        self._summarize_model = summarize_model
        self._classify_model = classify_model

    async def summarize(self, paper: RawPaper) -> PaperSummary:
        with trace_span(
            "groq.summarize",
            arxiv_id=paper.arxiv_id,
            model=self._summarize_model,
            prompt_version=summarize_prompt.VERSION,
        ):
            summary: PaperSummary = await self._client.chat.completions.create(
                model=self._summarize_model,
                response_model=PaperSummary,
                messages=[
                    {"role": "system", "content": summarize_prompt.SYSTEM},
                    {"role": "user", "content": summarize_prompt.build_user_prompt(paper)},
                ],
                temperature=_TEMPERATURE,
                max_retries=_MAX_RETRIES,
            )
        log.info("groq.summarized", arxiv_id=paper.arxiv_id)
        return summary

    async def classify(self, paper: RawPaper) -> Classification:
        with trace_span(
            "groq.classify",
            arxiv_id=paper.arxiv_id,
            model=self._classify_model,
            prompt_version=classify_prompt.VERSION,
        ):
            result: Classification = await self._client.chat.completions.create(
                model=self._classify_model,
                response_model=Classification,
                messages=[
                    {"role": "system", "content": classify_prompt.SYSTEM},
                    {"role": "user", "content": classify_prompt.build_user_prompt(paper)},
                ],
                temperature=_TEMPERATURE,
                max_retries=_MAX_RETRIES,
            )
        # Guard against invented or excess slugs before the value leaves the adapter.
        themes = normalize_themes(result.themes)
        log.info("groq.classified", arxiv_id=paper.arxiv_id, themes=themes)
        return Classification(themes=themes)
