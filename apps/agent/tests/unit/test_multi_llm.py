"""MultiLLMClient failover behavior — verified with stub providers (no network)."""

from __future__ import annotations

from datetime import UTC, datetime

from arxivdigest.adapters.llm.multi import MultiLLMClient
from arxivdigest.domain.models import (
    Classification,
    ImpactAssessment,
    PaperSummary,
    RawPaper,
)

_PAPER = RawPaper(
    arxiv_id="2401.00001",
    title="Test",
    abstract="An abstract.",
    published_at=datetime(2026, 1, 1, tzinfo=UTC),
)


class StubLLM:
    """An LLMClient that returns tagged results, or raises if ``fail`` is set."""

    def __init__(self, tag: str, *, fail: bool = False) -> None:
        self.tag = tag
        self.fail = fail

    async def summarize(self, paper: RawPaper) -> PaperSummary:
        if self.fail:
            raise RuntimeError("primary down")
        return PaperSummary(problem=self.tag, approach="", result="", why_it_matters="")

    async def classify(self, paper: RawPaper) -> Classification:
        if self.fail:
            raise RuntimeError("primary down")
        return Classification(themes=[self.tag])

    async def score_impact(self, paper: RawPaper) -> ImpactAssessment:
        if self.fail:
            raise RuntimeError("primary down")
        return ImpactAssessment(score=0.5, reasoning=self.tag)


async def test_uses_primary_when_healthy() -> None:
    client = MultiLLMClient(primary=StubLLM("primary"), fallback=StubLLM("fallback"))
    summary = await client.summarize(_PAPER)
    assert summary.problem == "primary"


async def test_falls_back_when_primary_fails() -> None:
    client = MultiLLMClient(
        primary=StubLLM("primary", fail=True),
        fallback=StubLLM("fallback"),
    )
    summary = await client.summarize(_PAPER)
    classification = await client.classify(_PAPER)
    impact = await client.score_impact(_PAPER)
    assert summary.problem == "fallback"
    assert classification.themes == ["fallback"]
    assert impact.reasoning == "fallback"
