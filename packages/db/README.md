# @repo/db

Shared database schema (Drizzle ORM) for ArxivDigest. Both `apps/web` (Next.js) and `apps/agent` (Python) target the same Supabase Postgres + pgvector instance — this package is the single source of truth for the schema.

The TypeScript schema in `src/schema.ts` is consumed directly by `apps/web` via Drizzle. The Python agent uses raw asyncpg (`apps/agent/src/arxivdigest/adapters/db/postgres.py`) against the same tables.

## Tables

| Table   | Purpose                                                          |
| ------- | ---------------------------------------------------------------- |
| papers  | One row per arxiv paper. Holds title, abstract, Voyage embedding (1024-d), pipeline outputs (summary, score). |
| digests | One row per published day. Holds the day's intro summary + ordered `paper_ids[]`. |

Indexes: unique `arxiv_id`, descending `published_at`, **HNSW cosine** on `embedding`, unique `date` on digests.

## First-time Supabase setup

The migration file does **not** include `CREATE EXTENSION vector;` — Drizzle doesn't manage extensions. Enable it once via Supabase Studio:

1. Open the Supabase project → **SQL Editor** → **New query**.
2. Paste and run:
   ```sql
   CREATE EXTENSION IF NOT EXISTS vector;
   ```
3. Verify in **Database → Extensions** — `vector` should be listed as enabled.

## Applying the migration

The migration SQL is at `packages/db/drizzle/0000_ordinary_lady_deathstrike.sql`. Three ways to apply it; pick whichever is convenient:

### Option A — Paste into Supabase SQL Editor (simplest)

1. Open `packages/db/drizzle/0000_*.sql`, copy contents.
2. Supabase Studio → **SQL Editor** → paste → **Run**.
3. Verify in **Database → Tables**: `papers` and `digests` should appear.

### Option B — `pnpm run db:migrate` (Drizzle Kit, requires DATABASE_URL)

```sh
# from packages/db/
export DATABASE_URL='postgresql://postgres.<ref>:<password>@<region>.pooler.supabase.com:6543/postgres'
pnpm run db:migrate
```

Drizzle tracks applied migrations in a `__drizzle_migrations` table — safe to re-run; already-applied migrations are skipped.

### Option C — `psql` (for power users)

```sh
psql "$DATABASE_URL" -f drizzle/0000_*.sql
```

## DATABASE_URL — where to set it

Use Supabase's **transaction-mode pooler** URL (port 6543), not the direct connection (5432). The pooler is required for serverless workloads and is what asyncpg/postgres-js expect when `statement_cache_size=0` / `prepare:false` is set.

| Where                | How                                                                              |
| -------------------- | -------------------------------------------------------------------------------- |
| Local dev (web)      | `apps/web/.env.local` — `DATABASE_URL=postgresql://...`                           |
| Local dev (agent)    | `apps/agent/.env` (loaded via python-dotenv) or shell `export`                    |
| Drizzle Kit commands | Either `.env` at `packages/db/` or shell `export` before running                  |
| Vercel               | Project → Settings → Environment Variables → `DATABASE_URL` (Production + Preview) |
| GitHub Actions       | Repo → Settings → Secrets → Actions → `DATABASE_URL`                              |

Connection-string format from Supabase:
```
postgresql://postgres.<project-ref>:<password>@<region>.pooler.supabase.com:6543/postgres
```

Find it in Supabase Studio → **Project Settings → Database → Connection string → URI → "Transaction"** mode.

## Verifying the schema after apply

From Supabase SQL Editor:

```sql
-- tables exist
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'public' AND table_name IN ('papers', 'digests');

-- pgvector enabled, HNSW index built
SELECT indexname, indexdef FROM pg_indexes
WHERE tablename = 'papers' AND indexname = 'papers_embedding_idx';

-- vector column has correct dimension
SELECT column_name, udt_name FROM information_schema.columns
WHERE table_name = 'papers' AND column_name = 'embedding';
```

## Scripts

```sh
pnpm db:generate   # diff schema.ts vs last snapshot → emit new SQL migration (offline, no DATABASE_URL needed)
pnpm db:migrate    # apply pending migrations (needs DATABASE_URL)
pnpm db:push       # push schema directly without a migration file (use sparingly, for prototypes only)
pnpm db:studio     # open Drizzle Studio at https://local.drizzle.studio
```

## Adding a new migration

1. Edit `src/schema.ts`.
2. `pnpm db:generate` — Drizzle writes a new `00NN_*.sql` plus updated snapshot.
3. Review the SQL for safety (per [feedback memory](../../MEMORY.md): never edit a migration after it has been applied to any env ≥ dev).
4. Commit both the schema change and the generated migration in the same PR.
5. Apply via Option A/B/C above.

## Known gotchas

- **Vector dimension is locked to 1024.** Matches Voyage `voyage-3` / `voyage-3-large`. Changing it requires recreating the column + reindexing. Decide carefully.
- **HNSW index build time grows with row count.** Fine at <100k rows. Re-evaluate at >1M rows (consider `lists` parameter on IVFFlat as alternative).
- **Supabase pooler kills idle connections.** Long-lived clients (`postgres-js`, `asyncpg`) need reconnection logic if you keep them open across requests. Short-lived per-request pools are simplest.
