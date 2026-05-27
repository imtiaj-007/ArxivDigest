# Observability + Monitoring

## Philosophy

Every production AI system should answer four questions at any moment:

1. **Is it running?** — uptime, last successful run
2. **Is it correct?** — eval scores, schema validation rates
3. **Is it healthy?** — error rate, latency, retry rate
4. **Is it efficient?** — cost per output, token usage trends

ArxivDigest instruments all four from V0. None of it is optional.

## Four pillars

| Pillar | Tool | Cost | What we capture |
|---|---|---|---|
| **Logs** | structlog (JSON to stdout) + GH Actions log retention | Free | Every stage entry/exit, every paper transition, every error |
| **LLM traces** | Langfuse Cloud (free 50K obs/mo) | Free | Every LLM call: prompt, completion, model, tokens, cost, latency, retries |
| **Errors** | Sentry (free 5000 errors/mo) | Free | Unhandled exceptions, breadcrumbs leading to error |
| **Metrics + run history** | Postgres `runs` + `llm_audit` tables | Free | Daily run results, eval F1 over time, cost trends |

## Structured logging (structlog)

### Setup

```python
# agent/observability/logging.py
import structlog
import logging
import sys

def configure_logging(log_level: str = "INFO", json_output: bool = True) -> None:
    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]
    
    renderer = (
        structlog.processors.JSONRenderer()
        if json_output
        else structlog.dev.ConsoleRenderer(colors=True)
    )
    
    structlog.configure(
        processors=shared_processors + [renderer],
        wrapper_class=structlog.make_filtering_bound_logger(
            logging.getLevelName(log_level.upper())
        ),
        cache_logger_on_first_use=True,
    )
```

### Context propagation

Every log line carries:

- `run_id` — set once per agent invocation via `structlog.contextvars.bind_contextvars(run_id=...)`
- `paper_id` — added when processing a specific paper
- `stage` — set at stage entry
- `provider`, `model`, `prompt_version` — added inside LLM call wrapper

### Example output

```json
{
  "level": "info",
  "event": "summarize_paper_completed",
  "timestamp": "2026-05-26T06:04:32.123Z",
  "run_id": "run_a8c2",
  "paper_id": "2026.04.12345",
  "stage": "summarize",
  "provider": "groq",
  "model": "llama-3.3-70b-versatile",
  "prompt_version": "summarize/v3",
  "prompt_tokens": 1842,
  "completion_tokens": 412,
  "latency_ms": 1893,
  "cost_usd_estimate": 0.0021
}
```

### Why JSON

- GH Actions captures stdout → can be downloaded as artifact
- Easy to grep / pipe through `jq` for ad-hoc analysis
- Standard format for log aggregators (Loki, ELK, Splunk) if migrated later
- Local dev: set `json_output=False` to get pretty colored output via `ConsoleRenderer`

## LLM trace observability (Langfuse)

### What we trace

Every LLM call goes through `agent.adapters.llm.instrumented.InstrumentedLLM`, which wraps the underlying Groq/Gemini adapter with Langfuse instrumentation.

For each call we capture:

| Field | Source |
|---|---|
| `prompt` (full text) | Caller |
| `completion` (full text) | LLM response |
| `model`, `provider` | Adapter config |
| `prompt_tokens`, `completion_tokens`, `cost_usd` | Response metadata |
| `latency_ms` | Wall clock |
| `parent_trace_id` | LangGraph run |
| `tags` | `stage`, `prompt_version`, `paper_id` |
| `metadata` | Full structured context |

### Trace structure

Each daily run is one Langfuse **trace**. Within it:

- One **observation** per stage (e.g. `crawl`, `classify_paper`)
- One **generation** per LLM call (nested inside its stage)
- One **embedding** observation per Voyage call

### Public dashboard

Once enough data accumulates, create a Langfuse public dashboard linking from `/about` on the site. Shows:

- Daily LLM cost trend
- Per-model latency P50/P95/P99
- Cache hit rate
- Schema validation failure rate

This is **resume gold** — interviewers can click and see real traces of real production runs.

### Sample integration

```python
# agent/adapters/llm/instrumented.py
from langfuse import Langfuse
from agent.ports.llm import LLMClient

class InstrumentedLLM:
    def __init__(self, inner: LLMClient, langfuse: Langfuse) -> None:
        self._inner = inner
        self._langfuse = langfuse
    
    async def complete(self, prompt: str, *, stage: str, prompt_version: str, **kwargs):
        generation = self._langfuse.generation(
            name=f"{stage}.{prompt_version}",
            model=self._inner.model_name,
            input=prompt,
            metadata={"stage": stage, "prompt_version": prompt_version},
        )
        try:
            response = await self._inner.complete(prompt, **kwargs)
            generation.end(
                output=response.text,
                usage_details={
                    "input": response.prompt_tokens,
                    "output": response.completion_tokens,
                },
            )
            return response
        except Exception as e:
            generation.end(level="ERROR", status_message=str(e))
            raise
```

## Error monitoring (Sentry)

### What we capture

- All unhandled exceptions
- Caught-but-significant exceptions (use `sentry_sdk.capture_exception(e)` explicitly)
- Breadcrumbs from structlog calls (auto-integrated)
- Tag every event with `run_id`, `stage`, `provider`

### Setup

```python
# agent/observability/tracing.py
import sentry_sdk
from agent.settings import settings

def configure_sentry() -> None:
    if not settings.sentry_dsn:
        return  # local dev: skip
    
    sentry_sdk.init(
        dsn=settings.sentry_dsn.get_secret_value(),
        environment=settings.environment,
        release=settings.git_sha,
        traces_sample_rate=0.1,
        profiles_sample_rate=0.1,
    )
```

### Alert policies

| Condition | Action |
|---|---|
| First error of any type in 24h | Email |
| Same error 5+ times in 1h | Email + Slack (if wired) |
| New unique error fingerprint | Email + GitHub issue auto-created |
| Run failure (caught at top-level) | Email |

## Run history + metrics (Postgres)

### `runs` table — every daily execution

See [ARCHITECTURE.md](./ARCHITECTURE.md#core-tables) for schema. Used by:

- `/status` page — last 30 days as green/red dots
- Cost dashboard — sum `total_cost_usd` over windows
- Eval drift detection — joins with eval-run table

### `llm_audit` table — every LLM call

Granular cost + latency + retry data per call. Used by:

- Per-model cost attribution
- Cache hit rate (`cached = true`)
- Schema retry rate (filter `retry_count > 0`)
- Slowest-prompt-by-latency analysis

## Public status page

`/status` reads from the `runs` table:

```
Last 30 days of daily runs:

  ████████░██████████░██████░░██████░░  (green = success, red = fail)

Latest run:
  ✓ 2026-05-26 06:00 UTC — 47 papers processed in 8m 23s
  
Last 7 days metrics:
  Average run time:    8m 12s
  Papers/day average:  43
  Cost/day average:    $0.00 (free tier)
  Cache hit rate:      62%
  Eval F1 (latest):    0.92
```

Build this in Week 3 of V0. It looks impressive on a portfolio.

## Cost tracking

### `llm_audit` aggregation

Every LLM call writes:

```sql
INSERT INTO llm_audit (
  run_id, paper_id, stage, provider, model,
  prompt_version, prompt_tokens, completion_tokens,
  latency_ms, cost_usd_estimate, cached, retry_count
) VALUES (...);
```

Cost estimate is computed client-side using a price table per model (kept in `agent.observability.pricing`). Update when providers change pricing.

### Dashboard surfaces

`/about` page renders:

- Total LLM calls last 30 days
- Total tokens consumed
- Total estimated cost: **$0.00** (currently always — but the engineering matters)
- Cache hit rate (lower = more spend)
- Per-provider breakdown
- Per-stage breakdown

### Cost ceiling enforcement

```python
class CostBudget:
    def __init__(self, max_usd_per_run: float) -> None:
        self.max = max_usd_per_run
        self.spent = 0.0
    
    def record(self, cost_usd: float) -> None:
        self.spent += cost_usd
        if self.spent > self.max:
            raise CostCeilingExceeded(
                f"Spent ${self.spent:.4f} > limit ${self.max}"
            )
```

Wired into the pipeline state; checked before every LLM call. Default ceiling: **$1 per daily run** (we'll be 100× under this on free tiers, but the guard exists).

## Heartbeat + orphan detection

### How it works

Agent spawns an async task on startup:

```python
async def heartbeat(run_id: UUID, repo: Repository, interval_s: int = 30) -> None:
    while True:
        await asyncio.sleep(interval_s)
        await repo.update_run_heartbeat(run_id, now())
```

### Orphan detector

A small standalone GH Actions workflow runs every 6 hours (`detect-orphans.yml`):

```python
# scripts/detect_orphans.py
stale_runs = repo.find_runs(
    status="running",
    heartbeat_older_than=timedelta(hours=1),
)
for run in stale_runs:
    repo.mark_run_failed(run.id, reason="heartbeat_stale")
    sentry_sdk.capture_message(
        f"Orphan run detected: {run.id}",
        level="warning",
    )
```

Without this, a hung run shows as "running" forever in dashboards.

## SLO documentation (self-imposed)

Even without a customer, defining SLOs signals senior thinking. Documented in `/about`:

| SLO | Target | Window | Action if breached |
|---|---|---|---|
| **Daily run success** | 99% | Rolling 30 days | Investigate; runbook |
| **Run duration** | P95 < 15min | Rolling 7 days | Profile slowest stage |
| **Eval F1 (classification)** | ≥ 0.85 sustained | Rolling 14 days | Rollback prompt version |
| **Schema validation rate** | ≥ 98% | Rolling 7 days | Prompt engineering pass |
| **Cache hit rate** | ≥ 50% | Rolling 7 days | Investigate cache invalidation |
| **Cost / paper** | < $0.01 | Per run | Cost ceiling alert |
| **Site uptime** | 99.9% (Vercel covers this) | Monthly | n/a — managed |

## Alert routing

| Alert | Channel | Frequency limit |
|---|---|---|
| Cron run failed | Email | per run |
| Cron didn't fire by 06:30 UTC | Email | per occurrence |
| Eval F1 dropped > 5% | Email | once per regression event |
| New Sentry error | Email | first per fingerprint per day |
| Sentry error rate spike | Email + Slack (if wired) | hourly max |
| Cost ceiling hit | Email | per occurrence |
| Supabase quota at 80% | Email | weekly |

Set up via:
- Sentry alert rules (UI)
- GH Actions `if: failure()` + email step (or use Apprise for multi-channel)
- Custom GH Action `eval-drift.yml` that runs nightly + alerts on regression

## Local dev observability

When running locally (`agent digest --dry-run`):

- Logs render as colored console output (not JSON)
- LLM traces still go to Langfuse (separate "dev" project)
- Sentry calls are no-ops (DSN unset)
- Cost tracking still records to local SQLite for testing

This is critical — observability bugs should be caught locally, not in production.

## Privacy + retention

- **Logs in GH Actions**: 90 days retention (GitHub default for public repos)
- **Langfuse traces**: 30 days on free tier; longer with paid (not needed for V0)
- **Sentry events**: 90 days on free tier
- **DB tables**: indefinite retention; `deleted_at` soft delete; never hard-delete production data

No PII handled in V0 (arxiv data is fully public; no user accounts). If V2 adds user accounts: full PII audit + GDPR considerations.

## What to instrument NEXT (V1+)

Deferred but valuable:

- **OpenTelemetry** distributed tracing — overkill for batch but signals deep observability knowledge
- **Prometheus metrics endpoint** — only if we move off batch into a long-running service
- **Custom Grafana dashboard** — when we have enough metrics to justify it
- **Eval anomaly detection** — automatic flag if any single eval metric deviates > 2σ from rolling average
- **Slack / Discord alert routing** — once a community channel exists

## Quick reference — where to look when X happens

| Symptom | First place to look |
|---|---|
| Cron didn't fire | GH Actions Actions tab |
| Run failed | Sentry → most recent error |
| Eval F1 dropped | `evals/metrics/history.jsonl` chart on `/about` |
| Specific paper looks wrong | Langfuse trace for that `paper_id` |
| Slow run | `llm_audit` query: `SELECT stage, AVG(latency_ms) FROM llm_audit WHERE run_id = ? GROUP BY stage` |
| Costs spiking | `llm_audit` cost aggregation by stage + provider |
| Schema validation failures | `llm_audit WHERE retry_count > 0` |
| Site stale / not updating | Vercel deploy log + last `runs` completion |
| Supabase paused | Supabase dashboard |

## Cross-references

- [ARCHITECTURE.md](./ARCHITECTURE.md) — system design that this observes
- [TESTING.md](./TESTING.md) — eval harness that feeds drift metrics
- [PROMPTS.md](./PROMPTS.md) — prompt versioning tracked here
- [SECURITY.md](./SECURITY.md) — logs respect PII guidelines (no secrets ever)
