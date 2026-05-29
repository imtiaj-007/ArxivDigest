"""``run`` command — the daily digest pipeline entrypoint.

Composes the adapters (arxiv source, Groq summarizer, Postgres repository) and
drives the summarize stage. This is what the GitHub Actions cron invokes via
``arxivdigest run --daily``.
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
from arxivdigest.adapters.llm.groq import GroqSummarizer
from arxivdigest.adapters.observability.tracing import trace_span
from arxivdigest.config import get_settings
from arxivdigest.stages.summarize import run_summarize_stage

log = structlog.get_logger()

DEFAULT_CATEGORIES = ["cs.AI", "cs.LG", "cs.CL"]
MANUAL_LIMIT = 5
DAILY_LIMIT = 50
CRAWL_TIMEOUT_S = 60.0


async def _run(categories: list[str], limit: int, dry_run: bool) -> int:
    settings = get_settings()
    if not settings.groq_api_key:
        raise RuntimeError("GROQ_API_KEY is not set")
    summarizer = GroqSummarizer(settings.groq_api_key)
    async with (
        httpx.AsyncClient(timeout=CRAWL_TIMEOUT_S) as client,
        pool_lifespan(settings.database_url) as pool,
    ):
        source = ArxivSource(client)
        repository = PostgresRepository(pool)
        summarized = await run_summarize_stage(
            source,
            summarizer,
            repository,
            categories=categories,
            limit=limit,
            dry_run=dry_run,
        )
    return len(summarized)


def run(
    limit: Annotated[
        int | None,
        typer.Option(help="Max papers to process. Defaults to 5, or 50 with --daily."),
    ] = None,
    daily: Annotated[
        bool,
        typer.Option("--daily", help="Daily cron mode: process the full daily batch."),
    ] = False,
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", help="Crawl + summarize but skip the DB write."),
    ] = False,
    category: Annotated[
        list[str] | None,
        typer.Option("--category", help="arxiv category to crawl (repeatable)."),
    ] = None,
) -> None:
    """Crawl recent arxiv papers, summarize them, and persist to the database."""
    categories = category or DEFAULT_CATEGORIES
    effective_limit = limit if limit is not None else (DAILY_LIMIT if daily else MANUAL_LIMIT)
    with trace_span("run", limit=effective_limit, daily=daily, dry_run=dry_run):
        processed = asyncio.run(_run(categories, effective_limit, dry_run))
    log.info("run.complete", processed=processed, dry_run=dry_run)
