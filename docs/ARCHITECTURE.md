# Architecture

## System overview

ArxivDigest is two independently deployable subsystems sharing a single Postgres database:

```
                       GitHub Actions (cron)
                       daily 06:00 UTC
                              │
                              ▼
         ┌────────────────────────────────────┐
         │   apps/agent — Python batch agent  │
         │   - crawls arxiv                   │
         │   - calls Groq / Gemini / Voyage   │
         │   - writes to Supabase             │
         └────────────────┬───────────────────┘
                          │
                          ▼
         ┌────────────────────────────────────┐
         │   Supabase Postgres + pgvector     │
         │   - papers, themes, runs           │
         │   - embeddings (1024-dim)          │
         │   - llm_audit, prompt_versions     │
         └────────────────┬───────────────────┘
                          │
                          ▼
         ┌────────────────────────────────────┐
         │   apps/web — Next.js 15 site       │
         │   - SSR/ISR digest pages           │
         │   - Fumadocs for /docs MDX         │
         │   - shadcn/ui components           │
         └────────────────┬───────────────────┘
                          │
                          ▼
                    ┌──────────┐
                    │  Vercel  │
                    │  (CDN)   │
                    └──────────┘

Side channels:
  • Langfuse Cloud  — LLM call traces
  • Sentry          — error monitoring
  • Drizzle Studio  — local DB inspection
  • Supabase Studio — production DB inspection
```

The two subsystems share **only the database schema** as their contract. The agent never serves HTTP. The site never invokes the agent. They are temporally decoupled — the agent writes, the site reads.

## Why this shape

- **Agent as batch, not service** — daily cron pattern doesn't need an HTTP server; batch is simpler, cheaper, fewer attack surfaces (see [ADR-0001](./adr/0001-pure-batch-architecture.md))
- **Database as integration boundary** — both subsystems agree on schema; can evolve independently if contract is preserved
- **Site is mostly static** — pre-rendered or ISR; reads from Postgres at build/revalidate time; near-zero runtime cost
- **GitHub Actions for orchestration** — free, observable, version-controlled (cron config is just YAML in repo)

## Agent pipeline (apps/agent)

### Stages (LangGraph state machine)

```
       ┌──────────┐
       │  START   │
       └────┬─────┘
            ▼
    ┌───────────────┐
    │   CRAWL       │ arxiv API → raw papers
    └───────┬───────┘
            ▼
    ┌───────────────┐
    │  RELEVANCE    │ cheap LLM (Llama 3.1 8B Instant)
    │  FILTER       │ drop noise, keep ~30-50
    └───────┬───────┘
            ▼
    ┌───────────────┐
    │  CLASSIFY     │ Llama 3.3 70B → 1-3 themes per paper
    └───────┬───────┘
            ▼
    ┌───────────────┐
    │  EMBED        │ Voyage → 1024-dim vectors
    └───────┬───────┘
            ▼
    ┌───────────────┐
    │  SUMMARIZE    │ Llama 3.3 70B → structured TL;DR
    │               │ (problem / approach / result / why)
    └───────┬───────┘
            ▼
    ┌───────────────┐
    │  RANK         │ novelty score (vs recent embeddings)
    │               │ + impact score (LLM reasoning)
    └───────┬───────┘
            ▼
    ┌───────────────┐
    │  PUBLISH      │ write papers + runs + audit to Supabase
    │               │ trigger Vercel rebuild via webhook
    └───────┬───────┘
            ▼
       ┌──────────┐
       │   END    │
       └──────────┘

  After each stage: persist checkpoint to DB.
  On crash: resume from last checkpoint.
  On per-paper failure: route to DLQ, continue with remaining.
```

### Architecture pattern — hexagonal (ports + adapters)

Domain logic and infrastructure are separated:

- **`agent/core/`** — pure business logic. No I/O. No network. Easy to unit-test.
  - Ranking algorithms
  - Classification rules + heuristics
  - Prompt templates (as code)
- **`agent/ports/`** — `typing.Protocol` interfaces.
  - `LLMClient`, `Embedder`, `PaperSource`, `Repository`
- **`agent/adapters/`** — concrete implementations.
  - `GroqAdapter`, `GeminiAdapter`, `MultiLLMAdapter` (failover)
  - `VoyageEmbedder`, `LocalEmbedder`
  - `ArxivSource`
  - `SupabaseRepository`
- **`agent/pipeline/`** — LangGraph orchestration over the ports
- **`agent/observability/`** — logging, tracing, metrics setup
- **`agent/infra/`** — retry, rate-limit, HTTP client config

See [ADR-0004](./adr/0004-hexagonal-architecture.md) for rationale.

### Stage-by-stage detail

| Stage | Input | Output | LLM model | Cost ceiling | Failure handling |
|---|---|---|---|---|---|
| **Crawl** | yesterday's date | ~100-150 papers (raw) | none | n/a | Hard timeout 5min; retry once on transient HTTP errors |
| **Relevance** | raw papers | ~30-50 kept | Llama 3.1 8B Instant | 100 calls / run | Drop on filter error; log to DLQ |
| **Classify** | filtered papers | papers with 1-3 themes each | Llama 3.3 70B | 50 calls / run | Per-paper retry 3x; DLQ on persistent fail |
| **Embed** | classified papers | 1024-dim vectors | Voyage `voyage-3-lite` | 1M tokens / run | Fallback to local `sentence-transformers` |
| **Summarize** | classified papers | structured summary (Pydantic) | Llama 3.3 70B | 50 calls / run | instructor lib auto-retries on schema fail |
| **Rank** | summarized papers + embedding | novelty + impact scores | Llama 3.3 70B | 50 calls / run | Default to neutral score on fail; flag for review |
| **Publish** | ranked papers | DB rows + Vercel rebuild | none | n/a | Atomic write per paper; rebuild idempotent |

## Site (apps/web)

### Routes

```
/                           today's digest (SSR, cache 15min)
/archive/[year]/[month]     month-by-month browse (ISR, 1hr)
/papers/[arxiv_id]          per-paper detail (ISR, 24hr)
/themes/[slug]              theme-filtered list (ISR, 1hr)
/status                     last 30 days of agent runs (SSR, no-cache)
/about                      methodology, eval scores, costs (SSR, daily)
/docs/[[...slug]]           Fumadocs-rendered MDX (static)
```

### Why this rendering mix

- **Today's digest** — SSR with short revalidate; updated every ~15min while agent might be running
- **Archive pages** — ISR with 1hr revalidate; rarely change after the day completes
- **Paper detail** — ISR with 24hr revalidate; effectively static after first generation
- **Status page** — SSR no-cache; must always show fresh data
- **Docs** — static, generated at build time from MDX

### Component library

`shadcn/ui` + Tailwind CSS. Components copied into `apps/web/components/ui/`, not npm-installed, allowing full customization. Built on Radix UI primitives for accessibility.

### Search

- **Site search** — Pagefind (built-in to Astro… but on Next.js, use FlexSearch client-side or Postgres FTS5 server-side)
- **Semantic search** (V1) — pgvector cosine similarity over `paper_embeddings` table

## Database schema (Supabase Postgres + pgvector)

### Core tables

```sql
-- Papers being tracked
papers (
  id              uuid pk,
  arxiv_id        text unique not null,
  title           text not null,
  abstract        text not null,
  authors         jsonb,                -- list of {name, affiliation?}
  arxiv_published_at  timestamptz,
  arxiv_categories    text[],
  pdf_url         text,
  
  -- Generated fields (versioned)
  summary             jsonb,            -- {problem, approach, result, why_it_matters}
  summary_model       text,             -- e.g. "groq/llama-3.3-70b"
  summary_prompt_ver  text,             -- e.g. "summarize/v3"
  
  themes              text[],           -- array of theme slugs
  classify_model      text,
  classify_prompt_ver text,
  classify_confidence numeric(3,2),
  
  novelty_score       numeric(3,2),
  impact_score        numeric(3,2),
  rank_model          text,
  rank_prompt_ver     text,
  rank_reasoning      text,
  
  status              text not null check (status in ('pending','classified','summarized','ranked','published','failed','dlq')),
  
  created_at          timestamptz default now(),
  updated_at          timestamptz default now(),
  deleted_at          timestamptz,        -- soft delete
  
  -- For idempotency + replays
  run_id              uuid references runs(id)
);

create index idx_papers_arxiv_published on papers (arxiv_published_at desc);
create index idx_papers_status on papers (status) where deleted_at is null;
create index idx_papers_themes on papers using gin (themes);

-- Vector embeddings (separate table to allow multiple embeddings per paper)
paper_embeddings (
  id              uuid pk,
  paper_id        uuid references papers(id) on delete cascade,
  embedding       vector(1024) not null,
  embedder_model  text not null,           -- e.g. "voyage-3-lite"
  created_at      timestamptz default now()
);

create index idx_paper_embeddings_hnsw on paper_embeddings 
  using hnsw (embedding vector_cosine_ops);

-- Themes (curated list)
themes (
  slug            text pk,                  -- e.g. "agents", "retrieval", "efficiency"
  name            text not null,
  description     text,
  display_order   integer
);

-- Run records (one per daily execution)
runs (
  id              uuid pk,
  started_at      timestamptz not null,
  completed_at    timestamptz,
  status          text not null check (status in ('running','completed','failed','partial')),
  stage           text,                     -- last stage entered
  papers_crawled  integer default 0,
  papers_kept     integer default 0,
  papers_failed   integer default 0,
  total_cost_usd  numeric(10,4) default 0,
  total_tokens    bigint default 0,
  error_summary   text,
  heartbeat_at    timestamptz,              -- updated every 30s during run
  github_run_url  text
);

create index idx_runs_started on runs (started_at desc);

-- Every LLM call (audit + cost tracking + replay)
llm_audit (
  id                uuid pk,
  run_id            uuid references runs(id),
  paper_id          uuid references papers(id),
  stage             text not null,
  provider          text not null,          -- "groq" | "gemini" | "cerebras"
  model             text not null,
  prompt_version    text not null,
  prompt_tokens     integer,
  completion_tokens integer,
  latency_ms        integer,
  cost_usd_estimate numeric(10,6),
  cached            boolean default false,
  retry_count       integer default 0,
  error             text,
  created_at        timestamptz default now()
);

create index idx_llm_audit_run on llm_audit (run_id);
create index idx_llm_audit_created on llm_audit (created_at desc);

-- Failed papers (DLQ for manual review)
failed_papers (
  arxiv_id        text pk,
  last_error      text,
  retry_count     integer default 0,
  first_failed_at timestamptz default now(),
  last_failed_at  timestamptz default now()
);

-- Prompt versions (immutable history)
prompt_versions (
  id              uuid pk,
  stage           text not null,            -- "relevance" | "classify" | "summarize" | "rank"
  version         text not null,            -- e.g. "v3"
  prompt_text     text not null,
  shadow_of       text,                     -- null if active; else version it shadows
  created_at      timestamptz default now(),
  active_from     timestamptz,
  active_until    timestamptz,
  unique (stage, version)
);
```

### Row-Level Security (RLS)

```sql
-- Anonymous (site visitors) can read published papers only
alter table papers enable row level security;

create policy "anon reads published papers" on papers
  for select using (status = 'published' and deleted_at is null);

create policy "service role full access" on papers
  for all to service_role using (true);

-- Embeddings: anon read for similar-paper search
create policy "anon reads embeddings" on paper_embeddings
  for select using (true);

-- runs, llm_audit, failed_papers, prompt_versions: service role only
alter table runs enable row level security;
alter table llm_audit enable row level security;
alter table failed_papers enable row level security;
alter table prompt_versions enable row level security;
-- (no anon select policy → effectively private)
```

### Migrations

All migrations live in `packages/db/migrations/` as Drizzle-generated SQL files, checked into git. Both agent and site read from the same generated schema definitions. See [ADR-0006](./adr/) (TBD) for the shared-schema pattern.

## Data flow

### Daily run sequence

```
06:00:00  GitHub Actions cron fires
06:00:10  Workflow checks out repo, runs `uv sync`
06:00:30  agent health — pings all external deps (Groq, Gemini, Voyage, Supabase)
06:00:35  agent digest starts
06:00:40    insert run row (status: 'running'); start heartbeat task
06:00:45    crawl arxiv (last 24h, cs.AI + cs.LG + cs.CL) → ~120 papers raw
06:01:00    parallel relevance filter (semaphore=10) → ~40 papers kept
06:02:00    parallel classify (semaphore=8) → assigned themes
06:03:00    parallel embed (semaphore=20) → 1024-dim vectors
06:04:00    parallel summarize (semaphore=5) → structured summaries
06:05:00    parallel rank (semaphore=5) → novelty + impact scores
06:06:00    publish: write all rows; update run status; trigger Vercel deploy
06:06:30  agent digest exits; workflow ends
06:07:00  Vercel rebuilds site; new content live within ~2-3min
06:10:00  Site shows today's digest
```

End-to-end: ~10 minutes. Well within GH Actions free tier budget.

### Per-paper lineage

Every paper row carries enough metadata to **regenerate any field**:

- Want to re-summarize all papers with new prompt? Find papers where `summary_prompt_ver != current_version` → re-run summarize stage on each → DB write.
- Want to compare classifier v3 vs v4? Run v4 in shadow mode (writes to `papers_shadow`); compare F1 on eval set; promote v4 once it beats v3 by margin.

## Failure modes + recovery

| Failure | Detection | Recovery |
|---|---|---|
| **Groq down** | HTTP 5xx / timeout | Failover to Gemini per call; if both down, fail the run and alert |
| **Voyage down** | HTTP error | Fallback to local `sentence-transformers` model (`all-MiniLM-L6-v2` 384-dim → upgrade to 1024 when Voyage recovers) |
| **Supabase paused** | Connection error | Auto-resume via first request; one-time latency spike acceptable |
| **GH Actions runner crash mid-run** | `heartbeat_at` stale > 1hr | Next run sees stale heartbeat; marks failed; picks up from last checkpoint |
| **Single paper fails LLM call** | Exception in stage | Bulkhead pattern: catch + log + send to DLQ; continue with remaining papers |
| **Schema validation fail on LLM output** | instructor lib catches Pydantic exception | Auto-retry with reformulated prompt up to 3x; DLQ on persistent fail |
| **Cost ceiling exceeded** | Running token total > config limit | Hard stop pipeline; log; alert |
| **Eval F1 drops > 5%** | Nightly eval CI check | Block deploy; alert; rollback to previous prompt version |
| **arxiv API rate limit** | HTTP 429 | Honour `Retry-After`; back off; if persistent, skip the run (next day will get 48h window) |

## Scalability plan

Current scale is comfortable on free tiers. Growth path:

| Volume tier | Papers/day | DB size | LLM cost/mo | Action needed |
|---|---|---|---|---|
| **Current (V0)** | 50-100 | <1GB | $0 | None |
| **V1 — covered subjects extended** | 200-300 | 5GB | $0 (still in free) | None |
| **V1.5 — embeddings + retrieval expanded** | 200-300 | 10GB | $5-10 | Supabase Pro ($25/mo) once over 8GB |
| **V2 — daily-paper count + extra LLM passes (critique, etc.)** | 500/day | 30GB | $30-50 | Paid Groq tier; consider self-hosted vLLM on Runpod |
| **V3 — multi-domain (full cs.*)** | 1500/day | 100GB+ | $200+ | Distinct architecture: ditch GH Actions, move to dedicated worker (Render / Railway $25/mo) |

The architecture has no fundamental blockers up to V2 scale. Beyond V2, the question is whether the project earns the cost — answered by traction.

## Security considerations

- **Secrets** — only in GitHub Actions secrets and `.env.local` (gitignored); never in code; all loaded via `pydantic.SecretStr`
- **Supabase keys** — service role key only used by agent (in GH Actions secret); anon key only used by site (public, RLS-restricted)
- **No user input handling in V0** — eliminates entire class of injection issues
- **Dependency hygiene** — Renovate / Dependabot enabled; weekly review
- **Pre-commit hooks** — `gitleaks` and `bandit` block leaked secrets and common vulnerabilities

Full details in [SECURITY.md](./SECURITY.md).

## Observability summary

- **Logs** — structlog JSON output to stdout; captured by GH Actions; key fields: `run_id`, `paper_id`, `stage`, `arxiv_id`
- **LLM traces** — every LLM call logged to Langfuse with full prompt + completion + cost
- **Errors** — Sentry captures exceptions; alerts on first error in 24h
- **Eval drift** — nightly eval harness; F1 trend chart on `/about`
- **Run history** — `runs` table powers public `/status` page (last 30 days of green/red dots)
- **Cost** — `llm_audit` aggregates → dashboard on `/about`

Full details in [OBSERVABILITY.md](./OBSERVABILITY.md).

## Cross-references

- [PROJECT.md](./PROJECT.md) — vision and scope
- [STACK.md](./STACK.md) — tech stack rationale
- [TESTING.md](./TESTING.md) — how this architecture is validated
- [PROMPTS.md](./PROMPTS.md) — prompt versioning + shadow rollout details
- [adr/](./adr/) — decisions referenced inline above
