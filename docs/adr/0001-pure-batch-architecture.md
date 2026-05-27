# ADR-0001 — Pure Python batch agent, no FastAPI

**Status:** Accepted
**Date:** 2026-05-26
**Decider:** Imtiaj

## Context

ArxivDigest's agent runs as a **daily cron job**: pull yesterday's papers, process them, write to DB, exit. The agent has no need to receive incoming HTTP requests; it's a closed-loop pipeline triggered by a scheduler.

A common reflex when building Python services is to wrap them in FastAPI (or similar). This adds an HTTP server, request handlers, exposed endpoints, and the requirement to host a long-running process. The question: should we do that here?

## Decision

**No HTTP server. The agent is a pure Python batch process exposed as a Typer CLI.**

Entry point is `agent digest` (and related subcommands like `eval`, `health`, `backfill`). GitHub Actions cron invokes this CLI directly. The process runs to completion and exits.

## Alternatives considered

### A. FastAPI service with a `/run` endpoint

Cron hits the endpoint instead of invoking the CLI directly.

**Rejected because:**

- Adds an always-on HTTP server requiring a host (Fly.io / Render free tiers are flaky; Vercel has 60s function limit, too short for our ~10min runs)
- Wider attack surface (rate limiting, auth, CORS, OWASP)
- More moving parts to monitor (uptime, latency, certs)
- HTTP layer adds nothing for a batch use case

### B. Celery / RQ task queue

Cron enqueues a task; worker dequeues and processes.

**Rejected because:**

- Requires a message broker (Redis / RabbitMQ) — another always-on service
- Queue value is parallelism + retries + scheduling — we have none of those needs for a daily single job
- Adds operational complexity disproportionate to benefit

### C. Serverless function (Vercel / AWS Lambda / Cloudflare Workers)

Wrap the agent in a serverless function and invoke on schedule.

**Rejected because:**

- All free serverless tiers have execution time caps (10-60s); our pipeline takes ~10min
- Cold start overhead per invocation
- Limited disk + memory for ML/embeddings workloads

### D. Always-on Python worker on a tiny VPS

Process started once, runs forever, internal scheduler triggers daily.

**Rejected because:**

- Always-on costs money
- Hand-rolled scheduling is fragile compared to cron
- One process loop crash kills everything until manual restart

## Decision

**Pure Python CLI invoked by GitHub Actions cron.** Simplest, cheapest, most observable. If we later need HTTP (webhook receivers, manual triggers), add FastAPI as a separate entrypoint over the same `core/` business logic — non-breaking because of hexagonal architecture (see ADR-0004).

## Consequences

### Positive

- **Zero ops** for the agent itself — GitHub Actions handles scheduling, retries, logs, secret injection
- **$0/month** — uses free GH Actions minutes
- **Reproducible** — each invocation is a fresh process; no state leakage between runs
- **Easy testing** — no HTTP layer to mock; agent is just functions called with inputs
- **Observable by default** — GitHub Actions UI shows every run, exit code, full stdout

### Negative / accepted trade-offs

- **No on-demand runs from a UI** — manual triggers go through `gh workflow run` or pushing a commit. Acceptable for V0; can add a Vercel-hosted FastAPI endpoint later if needed.
- **No real-time progress for users** — the daily site updates only after the run finishes. Acceptable for a daily-cadence product.
- **GH Actions free tier cap of 2000min/month** — current usage ~900min/month, but a ceiling that needs monitoring.

### When to revisit

Re-evaluate this decision if any of:
- Multiple human stakeholders need to trigger on-demand runs frequently
- Webhook-driven workflows become necessary (e.g. paper submission notifications)
- Run frequency increases beyond daily (real-time / hourly)
- GH Actions free tier becomes insufficient

## References

- Related: [ADR-0004 (hexagonal architecture)](./0004-hexagonal-architecture.md) — makes adding FastAPI later a non-breaking change
- [ARCHITECTURE.md](../ARCHITECTURE.md#agent-pipeline-appsagent)
