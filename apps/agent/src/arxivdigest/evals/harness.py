"""Eval harness — re-runs classify on the ground-truth set and computes metrics.

For now (Phase 1) the harness measures the classify stage only:
- multi-label classification F1 (micro + macro)
- per-theme F1
- schema validity rate (fraction of LLM calls that returned a valid Classification)

Phase 2 will add summary-keyword coverage + token tracking.

The harness re-runs the agent against the labels — it does NOT just compare the
DB's stored themes. That way the metric reflects the *current* prompt + model,
so prompt/model changes show up immediately in the next eval.
"""

from __future__ import annotations

import datetime as _dt
import json
import platform
from typing import Any

import structlog
from pydantic import BaseModel, Field

from arxivdigest.adapters.observability.tracing import trace_span
from arxivdigest.domain.themes import normalize_themes
from arxivdigest.evals.ground_truth import GroundTruthEntry
from arxivdigest.evals.metrics import (
    average,
    keyword_coverage,
    multilabel_classification_metrics,
    per_theme_f1,
)
from arxivdigest.ports.llm import LLMClient
from arxivdigest.ports.repository import Repository

log = structlog.get_logger(__name__)


class PaperResult(BaseModel):
    arxiv_id: str
    expected_themes: list[str]
    predicted_themes: list[str] | None = None
    keyword_coverage: float | None = None
    success: bool = True
    error: str | None = None


class EvalReport(BaseModel):
    timestamp: _dt.datetime = Field(default_factory=lambda: _dt.datetime.now(_dt.UTC))
    git_sha: str | None = None
    host: str = Field(default_factory=platform.node)

    total: int
    processed: int  # papers we actually got a prediction for
    schema_validity_rate: float  # processed / total

    classification: dict[str, float]  # micro + macro precision/recall/F1
    per_theme_f1: dict[str, float]
    avg_keyword_coverage: float  # fraction of expected_keywords found, avg across papers

    papers: list[PaperResult]

    def summary(self) -> str:
        c = self.classification
        return (
            f"papers={self.processed}/{self.total} "
            f"schema={self.schema_validity_rate:.2%} "
            f"micro_f1={c['micro_f1']:.3f} macro_f1={c['macro_f1']:.3f} "
            f"kw_cov={self.avg_keyword_coverage:.3f}"
        )


def _summary_to_text(summary_json: str | None) -> str | None:
    """Render the stored {problem, approach, result, why_it_matters} JSON to flat text."""
    if not summary_json:
        return None
    try:
        data = json.loads(summary_json)
    except json.JSONDecodeError:
        return summary_json  # legacy plain text
    if isinstance(data, dict):
        return " ".join(str(v) for v in data.values() if isinstance(v, str))
    return None


async def run_eval(
    repository: Repository,
    llm: LLMClient,
    ground_truth: list[GroundTruthEntry],
    *,
    git_sha: str | None = None,
) -> EvalReport:
    """Re-classify each ground-truth paper and score the agent against the labels."""
    if not ground_truth:
        raise ValueError("ground truth is empty — run `arxivdigest label` first")

    log.info("eval.started", total=len(ground_truth))
    ids = [gt.arxiv_id for gt in ground_truth]
    papers = await repository.fetch_papers_by_ids(ids)
    summary_map = await repository.fetch_summary_map(ids)
    by_id = {p.arxiv_id: p for p in papers}

    predicted_sets: list[set[str]] = []
    expected_sets: list[set[str]] = []
    coverages: list[float] = []
    results: list[PaperResult] = []

    with trace_span("eval.run", total=len(ground_truth)):
        for n, gt in enumerate(ground_truth, start=1):
            paper = by_id.get(gt.arxiv_id)
            if paper is None:
                results.append(PaperResult(
                    arxiv_id=gt.arxiv_id, expected_themes=gt.expected_themes,
                    success=False, error="paper not in DB",
                ))
                continue
            try:
                classification = await llm.classify(paper)
            except Exception as exc:
                log.warning("eval.classify_failed", arxiv_id=gt.arxiv_id, error=type(exc).__name__)
                results.append(PaperResult(
                    arxiv_id=gt.arxiv_id, expected_themes=gt.expected_themes,
                    success=False, error=type(exc).__name__,
                ))
                continue

            predicted = normalize_themes(classification.themes)
            predicted_sets.append(set(predicted))
            expected_sets.append(set(gt.expected_themes))

            # Keyword coverage uses the DB's stored summary (cheap, reflects whichever
            # prompt was active when it was written). Use --regenerate-all later if you
            # want this to also test a freshly-generated summary.
            summary_text = _summary_to_text(summary_map.get(gt.arxiv_id))
            cov: float | None = None
            if summary_text is not None and gt.expected_summary_keywords:
                cov = keyword_coverage(summary_text, gt.expected_summary_keywords)
                coverages.append(cov)

            results.append(PaperResult(
                arxiv_id=gt.arxiv_id,
                expected_themes=gt.expected_themes,
                predicted_themes=predicted,
                keyword_coverage=cov,
            ))
            if n % 25 == 0:
                log.info("eval.progress", done=n, total=len(ground_truth))

    class_metrics = multilabel_classification_metrics(predicted_sets, expected_sets)
    by_theme = per_theme_f1(predicted_sets, expected_sets)
    successes = sum(1 for r in results if r.success)
    avg_cov = average(coverages)

    report = EvalReport(
        git_sha=git_sha,
        total=len(ground_truth),
        processed=successes,
        schema_validity_rate=successes / len(ground_truth),
        classification=class_metrics,
        per_theme_f1=by_theme,
        avg_keyword_coverage=avg_cov,
        papers=results,
    )
    log.info("eval.completed", **{k: round(v, 4) for k, v in class_metrics.items()})
    return report


def report_as_dict(report: EvalReport) -> dict[str, Any]:
    return report.model_dump(mode="json")
