"""Multi-provider LLM adapter — Groq primary with Gemini failover.

Implements the :class:`LLMClient` port by delegating to a primary client and,
if that call fails (e.g. Groq rate-limit exhaustion), retrying once on a
fallback client. Each provider already does its own internal retries; this is
the last line of defense before a paper is dropped by the stage bulkhead.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable

import structlog

from arxivdigest.domain.models import Classification, ImpactAssessment, PaperSummary, RawPaper
from arxivdigest.ports.llm import LLMClient

log = structlog.get_logger(__name__)


class MultiLLMClient:
    """Routes each operation to ``primary``; on failure, falls back to ``fallback``."""

    def __init__(self, primary: LLMClient, fallback: LLMClient) -> None:
        self._primary = primary
        self._fallback = fallback

    async def _with_failover[T](self, op: str, call: Callable[[LLMClient], Awaitable[T]]) -> T:
        try:
            return await call(self._primary)
        except Exception as exc:
            log.warning("llm.failover", op=op, error=type(exc).__name__)
            return await call(self._fallback)

    async def summarize(self, paper: RawPaper) -> PaperSummary:
        return await self._with_failover("summarize", lambda c: c.summarize(paper))

    async def classify(self, paper: RawPaper) -> Classification:
        return await self._with_failover("classify", lambda c: c.classify(paper))

    async def score_impact(self, paper: RawPaper) -> ImpactAssessment:
        return await self._with_failover("score_impact", lambda c: c.score_impact(paper))
