"""``run`` command — the daily digest pipeline entrypoint.

Composes the adapters and drives the LangGraph pipeline. This is what the
GitHub Actions cron invokes via ``arxivdigest run --daily``.
"""

from __future__ import annotations

import asyncio
from typing import Annotated

import httpx
import structlog
import typer

from arxivdigest.adapters.arxiv.source import ArxivSource
from arxivdigest.adapters.db.postgres import pool_lifespan
from arxivdigest.adapters.db.repository import PostgresRepository
from arxivdigest.adapters.embeddings.voyage import VoyageEmbedder
from arxivdigest.adapters.llm.groq import GroqClient
from arxivdigest.adapters.observability.tracing import trace_span
from arxivdigest.config import get_settings
from arxivdigest.graph.builder import PipelineState, run_pipeline

log = structlog.get_logger()

DEFAULT_CATEGORIES = ["cs.AI", "cs.LG", "cs.CL"]
MANUAL_LIMIT = 5
DAILY_LIMIT = 50
CRAWL_TIMEOUT_S = 60.0


async def _run(categories: list[str], limit: int) -> PipelineState:
    settings = get_settings()
    if not settings.groq_api_key:
        raise RuntimeError("GROQ_API_KEY is not set")
    if not settings.voyage_api_key:
        raise RuntimeError("VOYAGE_API_KEY is not set")
    llm = GroqClient(settings.groq_api_key)
    embedder = VoyageEmbedder(settings.voyage_api_key)
    async with (
        httpx.AsyncClient(timeout=CRAWL_TIMEOUT_S) as client,
        pool_lifespan(settings.database_url) as pool,
    ):
        final = await run_pipeline(
            ArxivSource(client),
            llm,
            embedder,
            PostgresRepository(pool),
            categories=categories,
            limit=limit,
        )
    return final


def run(
    limit: Annotated[
        int | None,
        typer.Option(help="Papers to crawl this run. Defaults to 5, or 50 with --daily."),
    ] = None,
    daily: Annotated[
        bool,
        typer.Option("--daily", help="Daily cron mode: crawl the full daily batch."),
    ] = False,
    category: Annotated[
        list[str] | None,
        typer.Option("--category", help="arxiv category to crawl (repeatable)."),
    ] = None,
) -> None:
    """Run the daily pipeline: crawl → summarize → classify → embed → rank → publish."""
    categories = category or DEFAULT_CATEGORIES
    effective_limit = limit if limit is not None else (DAILY_LIMIT if daily else MANUAL_LIMIT)
    with trace_span("run", limit=effective_limit, daily=daily):
        final = asyncio.run(_run(categories, effective_limit))
    log.info(
        "run.complete",
        crawled=final.get("crawled", 0),
        summarized=final.get("summarized", 0),
        classified=final.get("classified", 0),
        embedded=final.get("embedded", 0),
        ranked=final.get("ranked", 0),
        published=final.get("published", 0),
    )
