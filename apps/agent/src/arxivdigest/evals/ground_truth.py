"""Ground-truth dataset for the eval harness."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, Field

# apps/agent/src/arxivdigest/evals/ground_truth.py → repo root is parents[5]
_REPO_ROOT = Path(__file__).resolve().parents[5]
DEFAULT_GROUND_TRUTH_PATH = _REPO_ROOT / "evals" / "ground_truth.jsonl"


class GroundTruthEntry(BaseModel):
    """A single human-labeled paper."""

    arxiv_id: str
    expected_themes: list[str] = Field(default_factory=list)
    expected_summary_keywords: list[str] = Field(default_factory=list)


def load_ground_truth(path: Path = DEFAULT_GROUND_TRUTH_PATH) -> list[GroundTruthEntry]:
    """Read JSONL, skip unlabeled entries (themes == null/empty)."""
    if not path.exists():
        raise FileNotFoundError(f"ground truth not found at {path}; run `arxivdigest label` first")
    out: list[GroundTruthEntry] = []
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        data = json.loads(line)
        if not data.get("expected_themes"):
            continue  # skip unlabeled stubs
        out.append(GroundTruthEntry.model_validate(data))
    return out
