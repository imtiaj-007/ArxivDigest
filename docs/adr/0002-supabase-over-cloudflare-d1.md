# ADR-0002 — Supabase Postgres over Cloudflare D1

**Status:** Accepted
**Date:** 2026-05-26
**Decider:** Imtiaj

## Context

ArxivDigest needs a database for:
- Structured paper records + metadata
- Vector embeddings for similarity search (~1024-dim)
- Run history + LLM audit log
- Future: users + subscriptions (V1+)

Two free-tier options stood out:
- **Cloudflare D1** — SQLite at the edge, generous free tier, simple, edge-distributed
- **Supabase** — managed Postgres + pgvector + auth + storage, free tier with usage caps

## Decision

**Use Supabase Postgres + pgvector.**

Drizzle ORM owns the schema (in `packages/db`). The agent uses `asyncpg` for direct connection (fast, long-lived); the Next.js site uses Supabase's HTTP client (PgBouncer mode for serverless).

## Alternatives considered

### A. Cloudflare D1 (SQLite at edge)

**Strengths:**
- Pure edge-distributed; ultra-low latency for site queries
- 5GB storage free
- Same vendor as Cloudflare Pages — single dashboard
- SQLite is dead simple

**Rejected because:**
- **No native vector type** — would need to store vectors as JSON or BLOB, with cosine in application code. Slow as data grows.
- **Limited JSON support** vs Postgres (`jsonb`, GIN indexes, operators)
- **No FTS for hybrid search** at the level we'd want
- **No managed auth** — would need to add it ourselves at V1+
- **Limited concurrent write throughput** — fine for our daily cron, but a ceiling
- Less mature ecosystem of tooling (ORMs, migration tools)

### B. Neon (managed Postgres)

**Strengths:**
- Free tier: 500MB storage; very Postgres-native
- Branching feature (cool for dev/preview)

**Rejected because:**
- No built-in auth (would need to add later)
- No built-in storage (would need separate S3-like)
- Smaller free tier than Supabase

### C. PlanetScale (managed MySQL/Vitess)

**Strengths:**
- Branching workflow
- Strong scaling story

**Rejected because:**
- Sunset their free hobby tier in 2024
- MySQL lacks pgvector — would need separate vector store
- Less momentum than Postgres in AI/ML community

### D. Self-hosted Postgres on Fly / Railway

**Strengths:**
- Full control
- pgvector available

**Rejected because:**
- Free tiers come with disk/uptime caveats
- Backup, monitoring, scaling all become our problem
- No built-in auth or storage

## Decision

**Supabase wins on the combined criteria:**

- ✅ Full Postgres with pgvector (vector search built-in)
- ✅ Row-Level Security (RLS) — the firewall around our DB
- ✅ Built-in auth (for V1+ subscriptions, no rework)
- ✅ Built-in storage (for V1+ PDFs caching, no rework)
- ✅ Built-in REST/RPC APIs (consumable from site)
- ✅ Healthy free tier (500MB DB, 5GB bandwidth)
- ✅ Studio UI for ad-hoc queries during dev + interviews
- ✅ Strong TypeScript ecosystem (`@supabase/supabase-js`, Drizzle integration)
- ✅ Mature dump/restore for backups

## Consequences

### Positive

- One service for DB + auth + storage — fewer dependencies, simpler mental model
- `pgvector` HNSW index handles future embedding queries at scale
- RLS is a real security boundary (the agent uses service-role; the site uses anon key — separate firewalls)
- Drizzle schema is a single source of truth shared by `apps/web` (TS) and `apps/agent` (Python via generated SQL)
- Interview demos: "let me show you the actual data" — Supabase Studio is gorgeous

### Negative / accepted trade-offs

- **Free tier projects pause after 7 days of inactivity** — auto-resume on first request, but cold-start latency. Daily cron pings every day, so won't trigger in normal operation.
- **500MB storage cap** — sufficient for V0 + V1; need Supabase Pro ($25/mo) when we cross ~8GB
- **5GB monthly bandwidth** — comfortable for V0; need to watch as site traffic grows
- **Not edge-distributed** — single-region (we'll use Asia Southeast or US-East). Adds ~50-100ms vs D1 for global users. Acceptable; site uses Vercel edge cache for most reads anyway.
- **Adds a vendor dependency** — if Supabase becomes paid-only or pivots, migration to Neon or self-hosted Postgres is straightforward (Drizzle ORM is provider-agnostic)

### When to revisit

- DB exceeds 8GB → upgrade to Supabase Pro ($25/mo) OR migrate to Neon/Render
- Bandwidth exceeds 5GB/mo → same upgrade path
- Need true multi-region writes → Postgres-as-a-Service doesn't help; would need different DB architecture (e.g. CockroachDB)
- If we needed offline-first sync → SQLite (D1) actually wins

## References

- Related: [ARCHITECTURE.md](../ARCHITECTURE.md#database-schema-supabase-postgres--pgvector)
- Related: [SECURITY.md](../SECURITY.md#3-row-level-security-rls)
- [Supabase free tier limits](https://supabase.com/pricing)
- [pgvector docs](https://github.com/pgvector/pgvector)
