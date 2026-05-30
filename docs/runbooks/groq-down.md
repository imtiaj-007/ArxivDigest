# Runbook: Groq is down or rate-limiting hard

When the daily cron starts failing on Groq calls — `RateLimitError` loops,
`APIStatusError` 5xx, or just dead silence — this is the first place to look.

## Symptoms

- `daily-digest` GH Actions runs go red, with `summarize.paper_failed` or
  `rank.paper_failed` repeating in the run log.
- `/status` shows today's square as red.
- `/papers` is stale (yesterday's digest still up).

## Quick triage (≤ 2 min)

1. **Check Groq's status page** — https://groqstatus.com/
2. **Read the latest run's log:**
   ```sh
   gh run view --workflow daily-digest.yml --log | tail -150
   ```
3. **Classify the error:**
   - `429 RateLimitError` repeating → TPM exhaustion (most common; usually
     local-account-burn or unusually long abstracts).
   - `5xx` / connection timeouts → Groq-side outage.
   - `400` with model name → the model was retired/renamed; update
     `DEFAULT_HEAVY_MODEL` / `DEFAULT_FAST_MODEL` in
     `apps/agent/src/arxivdigest/adapters/llm/groq.py`.

## Mitigations

### Groq is down (5xx, timeouts)

The `MultiLLMClient` wrapper exists for exactly this case, but Gemini's
free tier is currently exhausted, so failover is effectively a no-op.

- **Wait it out.** Every stage is idempotent: paper rows with `summary IS NULL`
  (or `themes IS NULL`, etc.) get retried on the next cron. One missed day
  doesn't break anything downstream.
- **Activate Gemini failover if urgent.** Set `GEMINI_API_KEY` in the
  GH `production` env. The agent constructs `MultiLLMClient(primary=Groq,
  fallback=Gemini)` whenever the key is present; on the next run, any Groq
  failure routes to Gemini automatically.

### Groq is rate-limiting (persistent 429)

In steady state the per-model `AsyncLimiter` token bucket (15 req/min on 70B,
25 req/min on 8B) should keep us under the cap. If 429s still escape:

1. **Reduce the rates** in `apps/agent/src/arxivdigest/adapters/llm/groq.py`
   (`_HEAVY_RPM`, `_FAST_RPM`) and re-deploy.
2. **Wait for the daily quota to reset.** Free-tier 70B is 6000 req/day; 8B
   is 14400 req/day. The cron uses ~50 + ~100 = 150 calls/day, well under —
   so if you're hitting the daily cap, something's wrong (concurrent runs?).
3. **Inspect the actual quota error** — the message includes both the metric
   (`requests_per_min` vs `tokens_per_min` vs `requests_per_day`) and the
   limit value.

### Re-running

```sh
gh workflow run daily-digest.yml
gh run watch
```

## Recovery checks

- **Workflow:** `gh run list --workflow daily-digest.yml --limit 3` — top
  entry should be green.
- **Database state:**
  ```sh
  cd apps/agent && uv run python -c "
  import asyncio
  from arxivdigest.config import get_settings
  from arxivdigest.adapters.db.postgres import pool_lifespan
  async def main():
      s = get_settings()
      async with pool_lifespan(s.database_url) as pool, pool.acquire() as conn:
          for q in ['summary IS NULL', 'themes IS NULL', 'embedding IS NULL', 'score IS NULL']:
              n = await conn.fetchval(f'SELECT count(*) FROM papers WHERE {q}')
              print(f'  {q}: {n}')
          d = await conn.fetchrow('SELECT date, array_length(paper_ids,1) AS n FROM digests ORDER BY date DESC LIMIT 1')
          print(f'  latest digest: {d}')
  asyncio.run(main())
  "
  ```
  All four counts should be 0; latest digest date should be today (UTC).
- **Site:** `/status` shows a fresh green square; `/papers` ranks today's
  papers at the top.

## Background

- **Free-tier Groq limits:** 6000/day on `llama-3.3-70b-versatile`, 14400/day
  on `llama-3.1-8b-instant`. Per-minute TPM is what bites in bursts; the
  `aiolimiter` mitigates that proactively (see
  [methodology → rate-limit defenses](https://arxiv-digest-preview.vercel.app/docs/methodology)).
- **Failover dormancy:** Re-enabling Gemini is one workflow line —
  `GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}` in `daily-digest.yml`.
  Code is already wired.
- **Bulkhead behavior:** Per-paper failures are logged and skipped, not fatal.
  Even with Groq half-broken, the run still records a `runs` row and the
  successful papers ship in today's digest.
