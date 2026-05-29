"""Groq-backed LLM adapter — implements the :class:`LLMClient` port.

Uses ``instructor`` to coerce the model's JSON output into a validated
:class:`PaperSummary`, with automatic re-prompting when validation fails.
"""

from __future__ import annotations

import instructor
import structlog
from groq import AsyncGroq

from arxivdigest.adapters.observability.tracing import trace_span
from arxivdigest.domain.models import PaperSummary, RawPaper
from arxivdigest.domain.prompts import summarize as summarize_prompt

log = structlog.get_logger(__name__)

# Groq's hosted Llama 3.3 70B — the summarize/classify/rank workhorse per STACK.md.
DEFAULT_MODEL = "llama-3.3-70b-versatile"

# Low temperature: summaries should be faithful, not creative.
_TEMPERATURE = 0.2
# instructor re-prompts this many times if the model returns invalid JSON.
_MAX_RETRIES = 2


class GroqSummarizer:
    """Summarizes papers via Groq + instructor."""

    def __init__(self, api_key: str, model: str = DEFAULT_MODEL) -> None:
        self._client = instructor.from_groq(AsyncGroq(api_key=api_key), mode=instructor.Mode.JSON)
        self._model = model

    async def summarize(self, paper: RawPaper) -> PaperSummary:
        with trace_span(
            "groq.summarize",
            arxiv_id=paper.arxiv_id,
            model=self._model,
            prompt_version=summarize_prompt.VERSION,
        ):
            summary: PaperSummary = await self._client.chat.completions.create(
                model=self._model,
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
