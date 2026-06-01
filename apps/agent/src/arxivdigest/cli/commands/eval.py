"""``arxivdigest eval`` — re-classify the ground-truth set and report metrics."""

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
from typing import Annotated

import structlog
import typer

from arxivdigest.adapters.db.postgres import pool_lifespan
from arxivdigest.adapters.db.repository import PostgresRepository
from arxivdigest.adapters.llm.gemini import GeminiClient
from arxivdigest.adapters.llm.groq import GroqClient
from arxivdigest.adapters.llm.multi import MultiLLMClient
from arxivdigest.adapters.observability.tracing import trace_span
from arxivdigest.config import get_settings
from arxivdigest.evals.ground_truth import DEFAULT_GROUND_TRUTH_PATH, load_ground_truth
from arxivdigest.evals.harness import EvalReport, run_eval
from arxivdigest.ports.llm import LLMClient

log = structlog.get_logger()

# apps/agent/src/arxivdigest/cli/commands/eval.py → repo root is parents[6]
_REPO_ROOT = Path(__file__).resolve().parents[6]
DEFAULT_REPORT_PATH = _REPO_ROOT / "evals" / "last_report.json"
HISTORY_PATH = _REPO_ROOT / "evals" / "metrics" / "history.jsonl"


async def _run(
    ground_truth_path: Path, limit: int | None, git_sha: str | None,
) -> EvalReport:
    settings = get_settings()
    if not settings.groq_api_key:
        raise RuntimeError("GROQ_API_KEY is not set")
    gt = load_ground_truth(ground_truth_path)
    if limit is not None:
        gt = gt[:limit]
    llm: LLMClient = GroqClient(settings.groq_api_key)
    if settings.gemini_api_key:
        llm = MultiLLMClient(primary=llm, fallback=GeminiClient(settings.gemini_api_key))
    async with pool_lifespan(settings.database_url) as pool:
        return await run_eval(PostgresRepository(pool), llm, gt, git_sha=git_sha)


def eval_cmd(
    limit: Annotated[
        int | None,
        typer.Option(help="Process only the first N ground-truth entries (smoke runs)."),
    ] = None,
    ground_truth: Annotated[
        Path,
        typer.Option(help="Path to ground-truth JSONL."),
    ] = DEFAULT_GROUND_TRUTH_PATH,
    output: Annotated[
        Path,
        typer.Option(help="Where to write the JSON report."),
    ] = DEFAULT_REPORT_PATH,
) -> None:
    """Re-classify the ground-truth set and write a JSON metrics report."""
    # CI sets GITHUB_SHA; local runs leave it None (sha is just for traceability).
    git_sha = os.environ.get("GITHUB_SHA")
    with trace_span("eval", limit=limit):
        report = asyncio.run(_run(ground_truth, limit, git_sha))
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report.model_dump(mode="json"), indent=2) + "\n")
    _append_history(report)
    typer.echo(report.summary())
    typer.echo(f"report written to {output}")


def _append_history(report: EvalReport) -> None:
    """Append a compact one-line summary of this run for trend tracking."""
    HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    line = {
        "timestamp": report.timestamp.isoformat(),
        "git_sha": report.git_sha,
        "processed": report.processed,
        "total": report.total,
        "schema_validity_rate": round(report.schema_validity_rate, 4),
        "micro_f1": round(report.classification["micro_f1"], 4),
        "macro_f1": round(report.classification["macro_f1"], 4),
        "avg_keyword_coverage": round(report.avg_keyword_coverage, 4),
    }
    with HISTORY_PATH.open("a") as f:
        f.write(json.dumps(line) + "\n")
