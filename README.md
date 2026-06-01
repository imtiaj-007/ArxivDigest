# ArxivDigest

[![daily-digest](https://github.com/imtiaj-007/ArxivDigest/actions/workflows/daily-digest.yml/badge.svg)](https://github.com/imtiaj-007/ArxivDigest/actions/workflows/daily-digest.yml)
[![CI](https://github.com/imtiaj-007/ArxivDigest/actions/workflows/ci.yml/badge.svg)](https://github.com/imtiaj-007/ArxivDigest/actions/workflows/ci.yml)
[![micro F1](https://img.shields.io/badge/dynamic/json?label=micro%20F1&query=%24.classification.micro_f1&url=https%3A%2F%2Fraw.githubusercontent.com%2Fimtiaj-007%2FArxivDigest%2Fmain%2Fevals%2Flast_report.json&color=brightgreen)](https://arxiv-digest-preview.vercel.app/about)
[![schema validity](https://img.shields.io/badge/dynamic/json?label=schema%20validity&query=%24.schema_validity_rate&url=https%3A%2F%2Fraw.githubusercontent.com%2Fimtiaj-007%2FArxivDigest%2Fmain%2Fevals%2Flast_report.json&color=brightgreen)](https://arxiv-digest-preview.vercel.app/about)
[![keyword coverage](https://img.shields.io/badge/dynamic/json?label=kw%20coverage&query=%24.avg_keyword_coverage&url=https%3A%2F%2Fraw.githubusercontent.com%2Fimtiaj-007%2FArxivDigest%2Fmain%2Fevals%2Flast_report.json&color=brightgreen)](https://arxiv-digest-preview.vercel.app/about)
[![cost](https://img.shields.io/badge/cost-%240%2Fmo-brightgreen)](https://arxiv-digest-preview.vercel.app/about)
[![license: MIT](https://img.shields.io/badge/license-MIT-blue)](./LICENSE)

> Autonomous daily AI agent that scans new arxiv `cs.AI` / `cs.LG` / `cs.CL` submissions, produces structured TL;DRs, classifies them by theme, and ranks them by novelty + impact — published every morning, unattended, at $0/month.

**Status:** V0 Weeks 1–4 in progress. Daily cron live, eval harness with CI regression gate live.
**Live:** [arxiv-digest-preview.vercel.app](https://arxiv-digest-preview.vercel.app)
**Reference:** [/docs/methodology](https://arxiv-digest-preview.vercel.app/docs/methodology) (engineering deep-dive) · [/docs/themes](https://arxiv-digest-preview.vercel.app/docs/themes) (taxonomy) · [/status](https://arxiv-digest-preview.vercel.app/status) (30-day run grid) · [/about](https://arxiv-digest-preview.vercel.app/about) (quality + cost ledger)

## What it does

Every morning at 07:00 UTC, a LangGraph pipeline:

1. **Crawl** — fetch the last day's `cs.AI` / `cs.LG` / `cs.CL` submissions from arxiv's Atom API.
2. **Summarize** — Groq Llama 3.3 70B + `instructor` produces a structured TL;DR (problem / approach / result / why it matters), grounded strictly in the abstract.
3. **Classify** — Llama 3.1 8B assigns 1–3 themes from a 14-theme taxonomy (post-validated against the canonical set).
4. **Embed** — local `BAAI/bge-large-en-v1.5` (1024-d) on CPU; vectors land in pgvector with an HNSW + cosine index.
5. **Rank** — blend pgvector novelty (cosine distance to nearest neighbors) with an LLM impact judgment into `papers.score`.
6. **Publish** — write a `digests` row from the top-K, fire on-demand revalidation so the site updates immediately.

Each stage is idempotent and reads its own pending work from the database (`X IS NULL`), so the DB status columns *are* the resume checkpoint — a crashed run is recovered by re-running the graph.

Free-tier hardening for the daily run:
- **Groq:** per-model `aiolimiter` token bucket (proactive pacing, never trips per-minute caps in the hot path) + `tenacity` backoff honoring Groq's `Retry-After` header + `MultiLLMClient` Gemini failover (dormant; can be activated by setting `GEMINI_API_KEY`).
- **Embeddings:** local model, no API, no rate limit, model weights cached in GH Actions.
- **Per-paper bulkhead:** one failed call is logged and skipped — the run continues.

Runs autonomously, costs **$0/month** on free tiers, every LLM call traced in Langfuse, every uncaught error captured in Sentry, every run recorded in the `runs` table and rendered as a 30-day grid on `/status`.

## Public surface

| Route | What |
|---|---|
| `/papers` | Latest ranked digest |
| `/papers/[arxiv_id]` | Per-paper detail + 5 cosine-NN similar papers |
| `/themes/[slug]` | Theme-filtered list |
| `/archive/[year]/[month]` | Month-filtered list with prev/next nav |
| `/status` | 30-day run grid + recent runs table |
| `/about` | Stack, cost ledger, live quality metrics |
| `/docs/*` | Engineering docs (Fumadocs): methodology, architecture, stack, prompts, testing, evals, observability, security, runbooks, ADRs |

## Documentation index

Engineering + ops docs live on the **site** so they're easy to browse and stay
versioned alongside the code that generates them:

| Doc | Live URL |
|---|---|
| Methodology | [/docs/methodology](https://arxiv-digest-preview.vercel.app/docs/methodology) |
| Theme taxonomy | [/docs/themes](https://arxiv-digest-preview.vercel.app/docs/themes) |
| Architecture | [/docs/architecture](https://arxiv-digest-preview.vercel.app/docs/architecture) |
| Tech stack | [/docs/stack](https://arxiv-digest-preview.vercel.app/docs/stack) |
| Prompts | [/docs/prompts](https://arxiv-digest-preview.vercel.app/docs/prompts) |
| Testing | [/docs/testing](https://arxiv-digest-preview.vercel.app/docs/testing) |
| Eval harness | [/docs/evals](https://arxiv-digest-preview.vercel.app/docs/evals) |
| Observability | [/docs/observability](https://arxiv-digest-preview.vercel.app/docs/observability) |
| Security | [/docs/security](https://arxiv-digest-preview.vercel.app/docs/security) |
| Runbooks | [/docs/runbooks](https://arxiv-digest-preview.vercel.app/docs/runbooks) |
| Architecture Decision Records | [/docs/adr](https://arxiv-digest-preview.vercel.app/docs/adr) |

Repo-only (setup + meta — not user-facing):

| Doc | Purpose |
|---|---|
| [PROJECT.md](./docs/PROJECT.md) | Vision, scope, success criteria, non-goals |
| [PLANNING.md](./docs/PLANNING.md) | Phases (V0 → V1 → V2), week-by-week roadmap |
| [CI_SECRETS.md](./docs/CI_SECRETS.md) | GH Actions secrets + variables setup |
| [VERCEL_SETUP.md](./docs/VERCEL_SETUP.md) | Web deployment + env vars |

## Quick start

```bash
# Install
pnpm install
uv sync --directory apps/agent

# Run the agent locally (5 papers)
cd apps/agent && uv run arxivdigest run --limit 5

# Run the web app locally
pnpm --filter web dev

# Tests
pnpm test
uv run --directory apps/agent pytest
```

You'll need a `.env` at the repo root with `DATABASE_URL`, `GROQ_API_KEY`, plus optional observability keys. See [.env.example](./.env.example).

## Tech stack (one-line)

Python 3.12 (uv + LangGraph + instructor + Groq + sentence-transformers) → Supabase Postgres + pgvector → Next.js 16 (App Router + Tailwind v4 + shadcn base-nova + Fumadocs) on Vercel. Orchestrated by GitHub Actions cron. Observed via Langfuse + Sentry + structlog.

## License

MIT (see [LICENSE](./LICENSE))
