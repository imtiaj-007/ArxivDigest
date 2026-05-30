"""LangGraph pipeline — orders the stages crawl → summarize → classify → embed
→ rank → publish.

State is deliberately thin: each stage is idempotent and reads its own pending
work from the DB (``X IS NULL``), so the database status columns *are* the
resume checkpoint. Re-running the graph after a crash re-enters every node, but
each one only processes what's still outstanding.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import TypedDict, cast

from langgraph.graph import END, START, StateGraph

from arxivdigest.ports.embeddings import Embedder
from arxivdigest.ports.llm import LLMClient
from arxivdigest.ports.repository import Repository
from arxivdigest.ports.source import PaperSource
from arxivdigest.stages.classify import run_classify_stage
from arxivdigest.stages.crawl import run_crawl_stage
from arxivdigest.stages.embed import run_embed_stage
from arxivdigest.stages.publish import run_publish_stage
from arxivdigest.stages.rank import run_rank_stage
from arxivdigest.stages.summarize import run_summarize_stage

# Backfill stages drain outstanding work (including stragglers from prior runs),
# so they run with a generous cap independent of the per-run crawl limit.
BACKFILL_LIMIT = 200


class PipelineState(TypedDict, total=False):
    categories: list[str]
    limit: int
    crawled: int
    summarized: int
    classified: int
    embedded: int
    ranked: int
    published: int


async def run_pipeline(
    source: PaperSource,
    llm: LLMClient,
    embedder: Embedder,
    repository: Repository,
    *,
    categories: Sequence[str],
    limit: int,
) -> PipelineState:
    """Build, compile, and run the daily pipeline graph; return the final state."""

    async def crawl(state: PipelineState) -> PipelineState:
        n = await run_crawl_stage(
            source, repository, categories=state["categories"], limit=state["limit"]
        )
        return {"crawled": n}

    async def summarize(state: PipelineState) -> PipelineState:
        return {"summarized": await run_summarize_stage(llm, repository, limit=BACKFILL_LIMIT)}

    async def classify(state: PipelineState) -> PipelineState:
        return {"classified": await run_classify_stage(llm, repository, limit=BACKFILL_LIMIT)}

    async def embed(state: PipelineState) -> PipelineState:
        return {"embedded": await run_embed_stage(embedder, repository, limit=BACKFILL_LIMIT)}

    async def rank(state: PipelineState) -> PipelineState:
        return {"ranked": await run_rank_stage(llm, repository, limit=BACKFILL_LIMIT)}

    async def publish(state: PipelineState) -> PipelineState:
        return {"published": await run_publish_stage(repository)}

    graph = StateGraph(PipelineState)
    for name, node in [
        ("crawl", crawl),
        ("summarize", summarize),
        ("classify", classify),
        ("embed", embed),
        ("rank", rank),
        ("publish", publish),
    ]:
        graph.add_node(name, node)
    graph.add_edge(START, "crawl")
    graph.add_edge("crawl", "summarize")
    graph.add_edge("summarize", "classify")
    graph.add_edge("classify", "embed")
    graph.add_edge("embed", "rank")
    graph.add_edge("rank", "publish")
    graph.add_edge("publish", END)

    compiled = graph.compile()
    result = await compiled.ainvoke({"categories": list(categories), "limit": limit})
    return cast(PipelineState, result)
