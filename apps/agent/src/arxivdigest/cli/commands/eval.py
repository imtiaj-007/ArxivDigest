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
# `evals/last_report.json` is kept as a local-only debug artifact (gitignored);
# the eval_runs DB table is the canonical source for everything user-facing.
DEFAULT_REPORT_PATH = _REPO_ROOT / "evals" / "last_report.json"
# Legacy JSONL path — backfill-eval-history still reads it on demand; nothing
# else writes to it after step 3 of the DB migration.
HISTORY_PATH = _REPO_ROOT / "evals" / "metrics" / "history.jsonl"
DEFAULT_BASELINE_PATH = _REPO_ROOT / "evals" / "baseline.json"

# Keys we compare to the baseline file. Anything not in this set is informational.
_GATED_METRICS = ("micro_f1", "macro_f1", "schema_validity_rate", "avg_keyword_coverage")


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
        repository = PostgresRepository(pool)
        report = await run_eval(repository, llm, gt, git_sha=git_sha)
        await _persist_to_db(repository, report)
        return report


async def _persist_to_db(repository: PostgresRepository, report: EvalReport) -> None:
    """Best-effort eval row insert. Logs and swallows on failure.

    Canonical sink for eval results — replaces the JSONL-in-git pattern from
    V0 W4 that fought main's branch protection and grew the repo a row per
    day forever. Errors are swallowed so a transient connection failure
    doesn't fail the eval gate; the last_report.json on disk is the only
    local-debug record left, and re-running `arxivdigest eval` recovers it.
    """
    try:
        await repository.insert_eval_run(
            ran_at=report.timestamp,
            git_sha=report.git_sha,
            processed=report.processed,
            total=report.total,
            micro_f1=report.classification["micro_f1"],
            macro_f1=report.classification["macro_f1"],
            schema_validity_rate=report.schema_validity_rate,
            avg_keyword_coverage=report.avg_keyword_coverage,
            per_theme_f1=dict(report.per_theme_f1),
            per_paper=[p.model_dump(mode="json") for p in report.papers],
        )
    except Exception as exc:
        # asyncpg.UndefinedTableError before the migration is applied is the
        # only one we expect; any other failure (transient connection, etc.)
        # is also tolerable since the JSONL append still records this run.
        log.warning(
            "eval.db_persist_failed",
            error=str(exc)[:200],
            action="falling back to JSONL-only record",
        )


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
    fail_on_regression: Annotated[
        bool,
        typer.Option(
            "--fail-on-regression",
            help="Exit non-zero if any metric falls below evals/baseline.json.",
        ),
    ] = False,
) -> None:
    """Re-classify the ground-truth set and write a JSON metrics report."""
    # CI sets GITHUB_SHA; local runs leave it None (sha is just for traceability).
    git_sha = os.environ.get("GITHUB_SHA")
    with trace_span("eval", limit=limit):
        report = asyncio.run(_run(ground_truth, limit, git_sha))
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report.model_dump(mode="json"), indent=2) + "\n")
    typer.echo(report.summary())
    typer.echo(f"report written to {output} (local debug artifact only)")
    if fail_on_regression:
        _enforce_baseline(report)


def _enforce_baseline(report: EvalReport) -> None:
    """Compare report metrics to evals/baseline.json; exit non-zero on regression."""
    if not DEFAULT_BASELINE_PATH.exists():
        typer.secho(
            f"baseline file not found at {DEFAULT_BASELINE_PATH} — skipping regression check",
            fg=typer.colors.YELLOW,
        )
        return
    baseline = {
        k: v
        for k, v in json.loads(DEFAULT_BASELINE_PATH.read_text()).items()
        if not k.startswith("_") and isinstance(v, (int, float))
    }
    actual = {
        "micro_f1": report.classification["micro_f1"],
        "macro_f1": report.classification["macro_f1"],
        "schema_validity_rate": report.schema_validity_rate,
        "avg_keyword_coverage": report.avg_keyword_coverage,
    }
    failures: list[str] = []
    for key in _GATED_METRICS:
        floor = baseline.get(key)
        if floor is None:
            continue
        observed = actual[key]
        if observed < floor:
            failures.append(f"  {key}: {observed:.4f} < baseline {floor}")
    if failures:
        typer.secho("REGRESSION:", fg=typer.colors.RED, bold=True)
        for line in failures:
            typer.echo(line)
        raise typer.Exit(code=1)
    typer.secho("baseline OK", fg=typer.colors.GREEN)


def backfill_history_cmd(
    history_path: Annotated[
        Path,
        typer.Option(help="Path to evals/metrics/history.jsonl to import."),
    ] = HISTORY_PATH,
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", help="Show what would be inserted; do not write."),
    ] = False,
) -> None:
    """One-off: import the legacy JSONL history rows into eval_runs.

    Idempotent — checks the (ran_at) of each line against existing rows so
    re-running doesn't duplicate. Run once after applying the migration; the
    JSONL keeps being written by `arxivdigest eval` as a redundant log.
    """
    if not history_path.exists():
        typer.secho(f"No history at {history_path} — nothing to backfill.", fg=typer.colors.YELLOW)
        return
    rows: list[dict[str, object]] = []
    for raw in history_path.read_text().splitlines():
        line = raw.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError as exc:
            log.warning("eval.backfill_skip_malformed_line", error=str(exc), line=line[:80])
    typer.echo(f"Found {len(rows)} JSONL rows to consider.")
    if dry_run:
        for r in rows:
            typer.echo(f"  would insert ran_at={r.get('timestamp')} micro_f1={r.get('micro_f1')}")
        return
    asyncio.run(_backfill_async(rows))


def _as_str(value: object) -> str | None:
    return value if isinstance(value, str) else None


def _as_num(value: object, default: float = 0.0) -> float:
    return float(value) if isinstance(value, (int, float)) else default


async def _backfill_async(rows: list[dict[str, object]]) -> None:
    import datetime as _dt
    settings = get_settings()
    async with pool_lifespan(settings.database_url) as pool:
        repository = PostgresRepository(pool)
        # Cheap dedup: pull all existing ran_at values once; insert only the
        # ones not already present (timestamp-level uniqueness — eval runs
        # never land in the same second by accident, and even if they do the
        # extra row is harmless rather than a hard error).
        async with pool.acquire() as conn:
            existing = {r["ran_at"] for r in await conn.fetch("SELECT ran_at FROM eval_runs")}
        inserted = 0
        for r in rows:
            ts_raw = _as_str(r.get("timestamp"))
            if ts_raw is None:
                continue
            ran_at = _dt.datetime.fromisoformat(ts_raw)
            if ran_at in existing:
                continue
            per_theme_raw = r.get("per_theme_f1")
            per_theme: dict[str, float] = {}
            if isinstance(per_theme_raw, dict):
                per_theme = {
                    k: float(v)
                    for k, v in per_theme_raw.items()
                    if isinstance(v, (int, float))
                }
            await repository.insert_eval_run(
                ran_at=ran_at,
                git_sha=_as_str(r.get("git_sha")),
                processed=int(_as_num(r.get("processed"))),
                total=int(_as_num(r.get("total"))),
                micro_f1=_as_num(r.get("micro_f1")),
                macro_f1=_as_num(r.get("macro_f1")),
                schema_validity_rate=_as_num(r.get("schema_validity_rate")),
                avg_keyword_coverage=_as_num(r.get("avg_keyword_coverage")),
                per_theme_f1=per_theme,
                per_paper=None,  # JSONL never carried per-paper detail
            )
            inserted += 1
        typer.secho(
            f"backfill: inserted {inserted}/{len(rows)} ({len(existing)} already present)",
            fg=typer.colors.GREEN,
        )


