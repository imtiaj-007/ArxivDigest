# Tech Stack

## At a glance

| Layer | Pick | Free tier | Why |
|---|---|---|---|
| **Monorepo** | Turborepo + pnpm workspaces | Free | Vercel-native; mixed-language friendly |
| **Frontend framework** | Next.js 15 (App Router) | Free | Industry default; resume signal; SSR/ISR built-in |
| **Frontend language** | TypeScript | Free | Type safety; standard |
| **Content / docs** | Fumadocs (MDX) | Free | Built for content-heavy sites |
| **UI components** | shadcn/ui + Radix | Free | Copy-into-repo; full control; accessible |
| **Styling** | Tailwind CSS 4 | Free | Standard; works with shadcn |
| **Site hosting** | Vercel Hobby | 100GB bw, 100GB-hr functions | Best Next.js DX; hobby fine for personal projects |
| **Database** | Supabase Postgres + pgvector | 500MB DB, 5GB bw, 2 projects | Full SQL; vector search built-in; built-in auth/storage when needed |
| **DB ORM (TS side)** | Drizzle ORM | Free | Type-safe; minimal runtime; migrations |
| **DB client (Python side)** | supabase-py + asyncpg | Free | Official client + async direct connection |
| **Agent language** | Python 3.12 | Free | AI/ML standard; full library ecosystem |
| **Agent deps** | uv (Astral) | Free | 10-100× faster than Poetry; current 2026 standard |
| **Agent framework** | LangGraph | Free | Stateful multi-agent; checkpointing built-in |
| **LLM (primary)** | Groq — Llama 3.3 70B | 6000 req/day | ~500 tok/s; free tier generous |
| **LLM (cheap loop)** | Groq — Llama 3.1 8B Instant | Higher limits | Filter / classify; faster + cheaper |
| **LLM (failover)** | Gemini 2.0 Flash | 1500 req/day | When Groq throttles |
| **LLM output validation** | instructor lib + Pydantic | Free | Auto-retry on schema fail |
| **Embeddings (primary)** | Voyage AI `voyage-3-lite` | 50M tok/mo | Best benchmark scores |
| **Embeddings (fallback)** | sentence-transformers `MiniLM` | Free (local) | Runs in GH Actions |
| **Cron / compute** | GitHub Actions | 2000 min/mo | Free, observable, version-controlled YAML |
| **LLM trace observability** | Langfuse Cloud | 50K obs/mo | Best-in-class for LLM tracing |
| **Error monitoring** | Sentry | 5000 errors/mo | Standard |
| **Structured logging** | structlog | Free | JSON output; parseable; standard |
| **Linting + formatting (Py)** | ruff | Free | Replaces black/flake8/isort/pyupgrade |
| **Type checking (Py)** | mypy strict mode | Free | Standard |
| **Testing (Py)** | pytest + pytest-asyncio + pytest-vcr + hypothesis + polyfactory | Free | Full pyramid + property tests + LLM record/replay |
| **Security (Py)** | bandit + gitleaks | Free | Static analysis + secret detection |
| **Pre-commit** | pre-commit | Free | Standard |
| **Linting (TS)** | ESLint + Prettier | Free | Standard |
| **Type checking (TS)** | tsc strict | Free | Standard |
| **Testing (TS)** | Vitest + Testing Library + Playwright | Free | Standard |
| **CI/CD** | GitHub Actions | 2000 min/mo | Same as agent cron |
| **Dependency updates** | Renovate (or Dependabot) | Free | Automated PRs |
| **Resilience** | tenacity + aiolimiter + circuitbreaker | Free | Retries + rate limit + circuit break |
| **HTTP client** | httpx (Py) / native fetch (TS) | Free | Modern, async-ready |
| **CLI framework** | Typer | Free | FastAPI-ergonomics for CLI |
| **Domain** | Cloudflare Registrar (`arxivdigest.dev`) | ~₹1000/yr (at-cost) | Cheapest registrar; could skip with github.io |

**Total monthly cost: $0** (excluding optional ~₹83/month for custom domain)

## Why these specific picks

### Python over TypeScript for the agent

Even though the rest of the stack is TypeScript, the agent stays Python because:

- AI/ML resume signal is Python-first
- Library ecosystem maturity: `instructor`, `langgraph`, arxiv clients all Python-first
- Hiring filters: most AI/ML roles list Python as hard requirement
- Mixed-language monorepo is normal; Turborepo doesn't care

A TS agent (Bun + LangGraph.js) would work technically, but reads as "didn't choose the standard tool for the job" in an AI engineering interview.

### `uv` over Poetry

See [ADR-0003](./adr/0003-uv-over-poetry.md). TL;DR: in 2026, `uv` is the de-facto choice; Poetry reads as "2022-era".

### Supabase over Cloudflare D1

See [ADR-0002](./adr/0002-supabase-over-cloudflare-d1.md). TL;DR: real Postgres beats SQLite for vector search + complex queries; Supabase RLS gives us auth-ready security from day 1.

### Vercel over Cloudflare Pages

Both work and both are free. Vercel chosen for:
- Best Next.js DX (it's Vercel's framework)
- Native ISR support without config
- Cleaner monorepo support (auto-detects `apps/web` subdir)
- Built-in OG image generation

Cloudflare Pages would save ~5% deploy time and offer unlimited bandwidth, but the Next.js feature support is slightly behind. For a Next.js project, Vercel is the lower-friction choice.

### Hexagonal architecture (ports + adapters) for the agent

See [ADR-0004](./adr/0004-hexagonal-architecture.md). TL;DR: separates pure domain logic from infrastructure; "how would you swap LLM providers?" is a 3-line answer (swap adapter); signals senior thinking.

### LangGraph over plain Python state machine

For V0, plain `if/else` works fine. LangGraph chosen for:
- Built-in checkpointing (matches our crash-recovery design)
- Built-in observability hooks (works with Langfuse out of the box)
- Resume signal (LangGraph is the dominant agent framework in 2026)
- Visualizable state machine (helps in interview walkthroughs)

Alternative considered: write plain Python orchestration with a `Step` dataclass and a sequential runner. Cleaner code, less framework lock-in, but loses the "I know LangGraph" resume bullet.

### Drizzle over Prisma / Kysely / TypeORM

For the TS side reading from Supabase:

| Tool | Why not |
|---|---|
| Prisma | Heavyweight; codegen ceremony; ORM-shaped not SQL-shaped |
| Kysely | Pure query builder; nice but no migration story |
| TypeORM | Old; reflection-based; awkward TS types |
| **Drizzle** | SQL-first; lightweight; great TS types; Supabase-friendly; current trendy choice |

### Fumadocs for the docs section

For the `/docs` portion of the site:

- Built for MDX content-heavy sites (our `/docs` and `/papers/[id]` pages benefit)
- Has built-in search, navigation, OG images, code highlighting
- Designed by Fuma Nama (active maintainer, well-respected)
- Plays nice with Next.js App Router

Alternative considered: pure Next.js + MDX without Fumadocs. More control, more code. Fumadocs is the pareto-optimal pick.

### shadcn/ui over Material UI / Chakra / Mantine

shadcn/ui isn't a library — it's a copy-paste collection of accessible Radix-based components styled with Tailwind. Why this over MUI/Chakra:

- **Components live in your repo** — fully customizable, no version migration pain
- **Radix primitives** — best-in-class accessibility (WCAG-compliant)
- **Industry standard 2026** — every modern Next.js project uses it
- **No bundle size cost** — only ship what you use

## Free-tier headroom

| Service | Free limit | Expected daily use | Headroom |
|---|---|---|---|
| GitHub Actions | 2000 min/mo | ~30 min/day = 900 min/mo | **2.2×** |
| Vercel Hobby | 100GB bw, 100GB-hr | ~5GB bw, mostly static | **20×+** |
| Supabase | 500MB DB, 5GB bw | <100MB DB initially | **5-50×** |
| Groq Llama 3.3 70B | 6000 req/day | ~500 req/day | **12×** |
| Groq Llama 3.1 8B | 14400 req/day | ~800 req/day | **18×** |
| Gemini 2.0 Flash | 1500 req/day | failover only, ~50 | **30×** |
| Voyage AI | 50M tok/mo | ~1M tok/mo | **50×** |
| Langfuse | 50K obs/mo | ~5K/mo | **10×** |
| Sentry | 5000 errors/mo | <50 | **100×** |
| Cloudflare Vectorize (if used) | 30M vectors | <10K vectors | **3000×** |

Even at 10× current growth, all services stay within free tiers.

## Stack readiness assessment

| Stack element | Maturity (2026) | Risk of becoming legacy in 2 years | Notes |
|---|---|---|---|
| Next.js | Very high | Low | Industry default |
| TypeScript | Very high | Negligible | — |
| Python 3.12 | Very high | Low | LTS-shape; 3.13/3.14 backward compatible |
| `uv` | High (newer) | Low | Astral backing strong; momentum visible |
| LangGraph | Medium-high | Medium | Newer; could be replaced by next-gen framework |
| Supabase | High | Low | YC-backed; widely adopted |
| Groq | Medium-high | Medium | Hardware play; depends on Groq's commercial trajectory |
| Voyage AI | Medium | Medium | Smaller player; could get acquired/sunset |
| Vercel | Very high | Low | Dominant Next.js host |
| shadcn/ui | High | Medium | Code-copy model; no runtime lock-in even if abandoned |

**Worst-case migration paths** all exist and aren't catastrophic:
- LangGraph → CrewAI / AutoGen / pure Python
- Groq → OpenAI / Anthropic / self-hosted vLLM
- Voyage → OpenAI embeddings / sentence-transformers
- Supabase → Postgres on Render / Neon / Railway
- Vercel → Cloudflare Pages / Netlify

## Alternatives considered + rejected

| Considered | Rejected because |
|---|---|
| FastAPI for agent | Over-engineered for batch job; HTTP layer adds nothing |
| Poetry for Python deps | Slower than uv; reads as 2022-era |
| Cloudflare D1 (SQLite) | Less powerful for pgvector + complex queries |
| Cloudflare Pages | Worse Next.js feature parity than Vercel |
| Astro for site | Less industry signal than Next.js |
| Plain MDX without Fumadocs | More code to write; less polish |
| MUI / Chakra UI | Bundle weight; less customizable |
| Material Tailwind | Less mature than shadcn |
| Prisma | Codegen ceremony; ORM-shaped not SQL-shaped |
| Pinecone for vectors | Costs money; pgvector free + good enough |
| OpenAI for LLMs | Costs money; Groq + Gemini cover free-tier needs |
| Anthropic for LLMs | Same as above; could revisit if free tier added |
| LangChain (not Graph) | Less stateful; harder to checkpoint |
| Webpack bundler | Next.js handles bundling |
| Custom CI | GH Actions does it free |
| Docker for agent | Overhead for a daily 10min job; uv-run in GH Actions is sufficient |
| Kubernetes anything | Massive overkill |

## When to revisit stack decisions

| Trigger | Re-evaluate |
|---|---|
| Daily LLM cost > $50/mo | Groq paid tier vs self-hosted vLLM on Runpod |
| Daily DB writes > 100K | Supabase Pro ($25/mo) or move to Neon |
| Vercel bw > 80GB/mo | Cloudflare Pages or Pro plan |
| 10K+ vectors with poor search recall | Migrate from pgvector to Qdrant |
| GH Actions hits 2000min/mo | Move cron to Cloudflare Workers Cron (free) or Fly cron ($1.94/mo) |
| Multiple engineers contributing | Add ESLint config package, more lint enforcement, stricter PR review |
| Customer-facing deployment (not just portfolio) | Add SOC 2-relevant controls; review Supabase region; consider Pro tier for SLA |

## Cross-references

- [ARCHITECTURE.md](./ARCHITECTURE.md) — how the stack pieces fit
- [PROJECT.md](./PROJECT.md) — why the project exists
- [adr/](./adr/) — specific decisions in detail
