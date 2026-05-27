# Testing Strategy

## Philosophy

Most AI side projects test exactly nothing. ArxivDigest treats testing as the **single biggest signal of engineering seniority**. Three pyramid layers + a separate eval harness for AI quality. Everything runs in CI; nothing manual.

## Test pyramid

```
                ╱   ╲
               ╱  E2E ╲          5%   (slow, real DB, recorded LLMs)
              ╱─────────╲
             ╱integration╲      20%   (real adapters, mocked external)
            ╱─────────────╲
           ╱     unit       ╲   60%   (pure logic, fast, no mocks needed)
          ╱─────────────────╲
         ╱   property tests   ╲ 15%   (hypothesis: ranking + classification invariants)
        ╱─────────────────────╲
```

Plus a separate **eval harness** for AI output quality, gated in CI.

## Layer 1 — Unit tests (60%)

### Target: `agent/core/`

Pure domain logic — no I/O, no network, no DB. Fast (whole suite < 5 seconds).

```python
# tests/unit/core/test_ranking.py
from agent.core.ranking import score_novelty

def test_novelty_score_inversely_proportional_to_max_similarity():
    similarities = [0.95, 0.87, 0.82, 0.71]
    score = score_novelty(similarities)
    assert 0.0 <= score <= 1.0
    assert score < 0.5  # high similarity → low novelty


def test_novelty_score_handles_empty_similarities():
    assert score_novelty([]) == 1.0  # no prior art = max novelty
```

### What to test

- Scoring algorithms (`ranking.py`, `classification.py`)
- Prompt template rendering (formatting, escaping)
- Pydantic model validation
- Pure functions in `core/`

### What NOT to test in unit tests

- LLM adapters (mock-heavy → integration layer)
- DB writes (integration layer)
- HTTP calls (integration layer)

## Layer 2 — Integration tests (20%)

### Target: adapters with mocked external services

Real adapter code, mocked external calls. Catches wiring bugs that unit tests miss.

```python
# tests/integration/adapters/test_groq_adapter.py
import pytest
from respx import MockRouter
from agent.adapters.llm.groq import GroqAdapter

@pytest.mark.asyncio
async def test_groq_adapter_calls_correct_endpoint(respx_mock: MockRouter):
    respx_mock.post("https://api.groq.com/openai/v1/chat/completions").respond(
        json={
            "choices": [{"message": {"content": '{"theme": "agents"}'}}],
            "usage": {"prompt_tokens": 100, "completion_tokens": 20},
        }
    )
    
    adapter = GroqAdapter(api_key=SecretStr("test"), model="llama-3.3-70b")
    response = await adapter.complete("classify this paper")
    
    assert response.text == '{"theme": "agents"}'
    assert response.prompt_tokens == 100
```

### Real DB tests

Use **Supabase CLI** (`supabase start`) for a local Postgres in CI. Schema migrations applied; teardown after each test.

```python
# tests/integration/repository/test_supabase_paper_repo.py
@pytest.fixture
async def repo(supabase_test_db):
    return SupabasePaperRepository(supabase_test_db)

async def test_paper_persisted_with_idempotency(repo):
    paper = Paper(arxiv_id="2026.04.12345", title="...")
    await repo.upsert(paper)
    await repo.upsert(paper)  # second call should be no-op
    
    rows = await repo.find_by_arxiv_id("2026.04.12345")
    assert len(rows) == 1  # single row, idempotent
```

## Layer 3 — E2E tests (5%)

### Full pipeline with VCR-recorded LLMs

`pytest-vcr` records HTTP responses on first run, replays them deterministically forever. Zero LLM cost on CI; fully reproducible.

```python
# tests/integration/test_pipeline_e2e.py
@pytest.mark.vcr  # records to tests/integration/cassettes/test_full_run.yaml
async def test_full_pipeline_on_sample_papers(supabase_test_db, sample_arxiv_response):
    """End-to-end: 3 papers in → 3 published rows in DB."""
    
    orchestrator = build_orchestrator(
        db=supabase_test_db,
        source=StubArxivSource(papers=sample_arxiv_response),
    )
    
    result = await orchestrator.run(run_id=uuid4())
    
    assert result.papers_kept == 3
    assert result.status == "completed"
    
    rows = await supabase_test_db.fetch_all("SELECT * FROM papers")
    assert len(rows) == 3
    for row in rows:
        assert row["status"] == "published"
        assert row["summary"] is not None
        assert row["themes"]
```

### How VCR cassettes work

1. **First run** (locally with real API keys):
   ```bash
   PYTEST_RECORD_CASSETTES=true uv run pytest tests/integration/test_pipeline_e2e.py
   ```
   Real LLM calls happen; responses saved to `tests/integration/cassettes/*.yaml`.

2. **Every subsequent run** (CI + local):
   - Cassettes replayed; no real LLM calls; deterministic
   - LLM cost: **$0** per CI run

3. **When prompts change**:
   - Cassettes need re-recording
   - Reviewer sees cassette diff in PR — visible artifact of LLM behavior change

This is the pattern every senior LLM team converges to.

## Layer 4 — Property tests (15%)

`hypothesis` generates many random inputs to find edge cases unit tests miss.

```python
# tests/property/test_ranking_properties.py
from hypothesis import given, strategies as st
from agent.core.ranking import score_novelty

@given(similarities=st.lists(st.floats(min_value=0.0, max_value=1.0), max_size=100))
def test_novelty_score_always_in_unit_interval(similarities):
    score = score_novelty(similarities)
    assert 0.0 <= score <= 1.0

@given(
    sim1=st.lists(st.floats(min_value=0.0, max_value=1.0), min_size=1, max_size=50),
    extra=st.floats(min_value=0.95, max_value=1.0),
)
def test_adding_highly_similar_paper_decreases_novelty(sim1, extra):
    """If a new very-similar paper is added, novelty should not increase."""
    score_before = score_novelty(sim1)
    score_after = score_novelty(sim1 + [extra])
    assert score_after <= score_before
```

Property tests find:
- Edge cases (empty lists, NaN, single-element)
- Mathematical invariants that hold across all inputs
- Concurrency assumptions

Signal: "I test invariants, not just examples" is a senior-level statement.

## Eval harness (separate from tests)

### Why separate

Tests check that the code **works as written**. Evals check that the code **produces good AI outputs**. Different failure modes, different fix cycles.

### Structure

```
evals/
├── ground_truth.jsonl              ← 50 hand-labeled papers
├── run_evals.py                    ← runs eval harness
├── metrics/
│   └── history.jsonl               ← every eval run's results (append-only)
└── README.md
```

### `ground_truth.jsonl` format

```jsonl
{"arxiv_id": "2026.04.12345", "expected_themes": ["agents", "evaluation"], "is_relevant": true, "expected_summary_keywords": ["LangGraph", "multi-agent", "benchmark"]}
{"arxiv_id": "2026.04.12346", "expected_themes": ["efficiency"], "is_relevant": true, "expected_summary_keywords": ["quantization", "INT4", "Llama"]}
{"arxiv_id": "2026.04.12347", "expected_themes": [], "is_relevant": false}
```

### What gets measured

| Metric | Computed via | Target |
|---|---|---|
| **Classification F1** | sklearn over multi-label predictions vs `expected_themes` | ≥ 0.85 |
| **Relevance precision/recall** | binary classification vs `is_relevant` | precision ≥ 0.90, recall ≥ 0.85 |
| **Summary keyword coverage** | fraction of `expected_summary_keywords` present in generated summary | ≥ 0.70 |
| **Summary length distribution** | mean tokens, P95 tokens | mean 150-300, P95 < 500 |
| **Ranking stability** | Kendall tau between two consecutive runs on same papers | ≥ 0.80 |
| **Cost per paper** | sum LLM cost / paper count | < $0.01 |
| **Schema validation rate** | fraction of LLM outputs passing Pydantic validation first try | ≥ 0.95 |

### `run_evals.py`

```python
# evals/run_evals.py
import json
from pathlib import Path
from datetime import datetime, UTC

from agent.pipeline.orchestrator import build_orchestrator
from agent.settings import settings

def main():
    ground_truth = [json.loads(line) for line in (Path("evals/ground_truth.jsonl").read_text().splitlines())]
    
    orchestrator = build_orchestrator(settings=settings, eval_mode=True)
    
    results = []
    for entry in ground_truth:
        actual = orchestrator.process_paper(entry["arxiv_id"])
        results.append({
            "arxiv_id": entry["arxiv_id"],
            "actual_themes": actual.themes,
            "expected_themes": entry["expected_themes"],
            "actual_relevant": actual.relevant,
            "expected_relevant": entry["is_relevant"],
            # ...
        })
    
    metrics = compute_metrics(results)
    
    # Append to history
    history_line = {
        "timestamp": datetime.now(UTC).isoformat(),
        "git_sha": current_git_sha(),
        "metrics": metrics,
    }
    with Path("evals/metrics/history.jsonl").open("a") as f:
        f.write(json.dumps(history_line) + "\n")
    
    return metrics

if __name__ == "__main__":
    metrics = main()
    print(json.dumps(metrics, indent=2))
```

### CI gate

`.github/workflows/ci.yml`:

```yaml
- name: Run eval harness
  run: uv run python evals/run_evals.py > eval-result.json

- name: Check eval regression
  run: |
    BASELINE_F1=$(uv run python -c "import json; print(json.load(open('evals/baseline.json'))['classification_f1'])")
    CURRENT_F1=$(jq '.classification_f1' eval-result.json)
    DELTA=$(python -c "print($CURRENT_F1 - $BASELINE_F1)")
    if (( $(echo "$DELTA < -0.05" | bc -l) )); then
      echo "Eval regression: F1 dropped from $BASELINE_F1 to $CURRENT_F1"
      exit 1
    fi
```

PRs that drop F1 by > 5% are blocked. Prompt rollbacks become explicit, intentional acts.

### Updating the baseline

```bash
# After a deliberate prompt improvement that legitimately changes outputs:
uv run agent eval --update-baseline
```

This copies the latest `evals/metrics/history.jsonl` entry to `evals/baseline.json`. Reviewer sees the file diff in PR.

## Regression / golden tests

Pin output for a small set of "well-known" papers — if structure breaks, CI fails.

```python
# tests/regression/test_known_papers.py
import json
from pathlib import Path

GOLDEN_DIR = Path("tests/regression/golden")

@pytest.mark.parametrize("arxiv_id", ["2026.04.12345", "2026.04.12346"])
def test_paper_output_structure_unchanged(arxiv_id):
    actual = run_pipeline_on_paper(arxiv_id)
    golden = json.loads((GOLDEN_DIR / f"{arxiv_id}.json").read_text())
    
    # Structure must match exactly
    assert set(actual.keys()) == set(golden.keys())
    assert isinstance(actual["summary"], dict)
    assert set(actual["summary"].keys()) == {"problem", "approach", "result", "why_it_matters"}
```

These catch breaking schema changes that ripple through downstream code.

## Snapshot tests for the site

For the Next.js side, use **Playwright** for E2E snapshot tests:

```typescript
// apps/web/tests/e2e/digest.spec.ts
import { test, expect } from '@playwright/test';

test('today digest page renders papers correctly', async ({ page }) => {
  await page.goto('/');
  
  await expect(page.locator('h1')).toContainText("Today's Digest");
  await expect(page.locator('[data-testid="paper-card"]')).toHaveCount(40, { timeout: 10000 });
});

test('status page shows last 30 days', async ({ page }) => {
  await page.goto('/status');
  
  await expect(page.locator('[data-testid="day-dot"]')).toHaveCount(30);
});
```

## Pre-commit hooks

`.pre-commit-config.yaml`:

```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.8.0
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format
  
  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.13.0
    hooks:
      - id: mypy
        additional_dependencies: [pydantic>=2]
  
  - repo: https://github.com/gitleaks/gitleaks
    rev: v8.21.0
    hooks:
      - id: gitleaks
  
  - repo: https://github.com/PyCQA/bandit
    rev: 1.7.10
    hooks:
      - id: bandit
        args: [-r, src]
  
  - repo: local
    hooks:
      - id: pytest-fast
        name: pytest unit tests
        entry: uv run pytest tests/unit -x
        language: system
        pass_filenames: false
        types: [python]
```

Runs every commit. Fast (unit tests only); integration + eval run in CI.

## CI pipeline (`.github/workflows/ci.yml`)

```yaml
name: CI
on: [pull_request]

jobs:
  lint-typecheck:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v3
      - run: uv sync --frozen
      - run: uv run ruff check
      - run: uv run ruff format --check
      - run: uv run mypy src
      - run: uv run bandit -r src

  test-unit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v3
      - run: uv sync --frozen
      - run: uv run pytest tests/unit tests/property --cov=src/agent --cov-report=xml
      - uses: codecov/codecov-action@v5

  test-integration:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: pgvector/pgvector:pg16
        env: { POSTGRES_PASSWORD: postgres }
        ports: ['5432:5432']
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v3
      - run: uv sync --frozen
      - run: uv run python -m agent.scripts.migrate
      - run: uv run pytest tests/integration

  eval-gate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v3
      - run: uv sync --frozen
      - run: uv run python evals/run_evals.py > eval-result.json
      - run: |
          # Compare to baseline; fail if F1 dropped > 5%
          ./scripts/check-eval-regression.sh

  security:
    runs-on: ubuntu-latest
    steps:
      - uses: gitleaks/gitleaks-action@v2

  web-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: pnpm/action-setup@v4
      - run: pnpm install --frozen-lockfile
      - run: pnpm --filter web typecheck
      - run: pnpm --filter web lint
      - run: pnpm --filter web test
```

## Coverage targets

| Layer | Target | Enforced |
|---|---|---|
| `agent/core/` | ≥ 95% | CI fails below |
| `agent/pipeline/` | ≥ 85% | CI fails below |
| `agent/adapters/` | ≥ 70% | CI warning |
| `agent/observability/` | best effort | none |

Reported via Codecov (free tier).

## Local dev workflow

```bash
# Run fast tests (TDD inner loop)
uv run pytest tests/unit -x --ff

# Watch mode
uv run ptw tests/unit

# Run integration tests (requires local Supabase up)
supabase start
uv run pytest tests/integration

# Update VCR cassettes after intentional change
PYTEST_RECORD_CASSETTES=true uv run pytest tests/integration

# Run evals locally before pushing
uv run python evals/run_evals.py

# Full CI check before pushing
just ci  # justfile target running everything CI does
```

## What this signals on a resume

| Practice | Senior signal |
|---|---|
| Test pyramid with measured coverage | "I respect testing fundamentals" |
| VCR cassettes for LLM calls | "I think about CI cost of AI testing" |
| Property tests with hypothesis | "I test invariants, not just examples" |
| Eval CI gate | "I treat AI quality as a CI concern" |
| Regression / golden tests | "I prevent breaking schema changes" |
| Pre-commit hooks running tests | "I want fast feedback loops" |
| Coverage gates per package | "I enforce standards, not just measure them" |
| Snapshot tests for site | "I test the user-facing surface" |

## Cross-references

- [ARCHITECTURE.md](./ARCHITECTURE.md) — what we're testing
- [OBSERVABILITY.md](./OBSERVABILITY.md) — eval drift detection
- [PROMPTS.md](./PROMPTS.md) — prompt versioning gated by eval
- [adr/0004-hexagonal-architecture.md](./adr/0004-hexagonal-architecture.md) — why this architecture is easy to test
