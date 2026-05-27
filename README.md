# ArxivDigest

> Autonomous multi-agent system that scans daily arxiv AI/ML submissions, classifies them across research themes, ranks by novelty and practical impact, and publishes a structured digest to a public archive.

**Status:** 🚧 Pre-V0 — see [docs/PLANNING.md](./docs/PLANNING.md)
**Live demo:** TBD
**Architecture:** [docs/ARCHITECTURE.md](./docs/ARCHITECTURE.md)

## What it does

Every morning at 06:00 UTC, an agent pipeline:

1. Pulls the last 24h of arxiv submissions in `cs.AI` / `cs.LG` / `cs.CL`
2. Filters for relevance (cheap LLM pass)
3. Classifies each paper across 15 research themes
4. Generates a structured summary (problem / approach / result / why it matters)
5. Ranks by novelty + practical impact, anchored against historical context
6. Publishes a markdown digest to a public site
7. Logs every LLM call to Langfuse for trace observability

Runs autonomously, costs $0/month on free tiers, fully observable.

## Documentation index

| Doc | Purpose |
|---|---|
| [PROJECT.md](./docs/PROJECT.md) | Vision, scope, success criteria, non-goals |
| [ARCHITECTURE.md](./docs/ARCHITECTURE.md) | System design, components, data flow, failure modes |
| [PLANNING.md](./docs/PLANNING.md) | Phases (V0 → V1 → V2), week-by-week roadmap |
| [STACK.md](./docs/STACK.md) | Tech stack with rationale, alternatives considered |
| [OBSERVABILITY.md](./docs/OBSERVABILITY.md) | Logging, metrics, tracing, alerts, SLOs |
| [TESTING.md](./docs/TESTING.md) | Test pyramid, eval harness, regression gates |
| [PROMPTS.md](./docs/PROMPTS.md) | Prompt design, versioning, shadow rollouts |
| [SECURITY.md](./docs/SECURITY.md) | Secrets, RLS, supply chain, hardening |
| [adr/](./docs/adr/) | Architecture Decision Records |

## Quick start (when V0 ships)

```bash
# Install dependencies
pnpm install
uv sync --directory apps/agent

# Run agent locally
uv run --directory apps/agent agent digest --dry-run

# Run site locally
pnpm --filter web dev

# Run tests
pnpm test
uv run --directory apps/agent pytest
```

## Tech stack (one-line summary)

Python 3.12 batch agent (uv + LangGraph + Groq + Voyage + Pydantic) → Supabase Postgres + pgvector → Next.js 15 + Fumadocs + shadcn site on Vercel. Orchestrated daily via GitHub Actions. Observed via Langfuse + Sentry + structured logs.

## License

MIT (see [LICENSE](./LICENSE))
