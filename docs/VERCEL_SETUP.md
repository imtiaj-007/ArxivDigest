# Vercel Setup

How to deploy `apps/web` to Vercel from this Turborepo. Most of this is one-time dashboard configuration — no `vercel.json` is needed for a standard Next.js app in a Turborepo.

## Branch → deployment mapping

| Branch | Vercel deployment | Env scope |
|---|---|---|
| `main` | Production (your real domain) | Production |
| `dev` | Preview (auto URL per push) | Preview |
| feature branches / PRs | Preview (auto URL) | Preview |

This mirrors the dev=staging / main=prod model: preview deploys act as staging.

## 1. Connect the repo

1. Go to https://vercel.com/new (logged in with the account you want — personal).
2. **Import** the `imtiaj-007/ArxivDigest` repo. Authorize the Vercel GitHub app for it if prompted (grant access to only this repo).
3. On the configure screen, **do not deploy yet** — set the options below first.

## 2. Project settings

| Setting | Value |
|---|---|
| **Root Directory** | `apps/web` ← critical. Click "Edit" and select it. |
| **Framework Preset** | Next.js (auto-detected once root dir is set) |
| **Build Command** | leave default (`next build`) — Vercel runs it inside `apps/web` |
| **Install Command** | leave default — Vercel detects pnpm workspaces and installs from the repo root |
| **Node.js Version** | 22.x (matches `.nvmrc`) |

Vercel auto-detects Turborepo and enables remote caching. The `pnpm-lock.yaml` at the repo root is used for installs.

## 3. Production branch

Project → **Settings → Git**:
- **Production Branch** = `main` (default).
- Leave "Automatically expose System Environment Variables" on.
- Preview deployments are created for all other branches + PRs by default — no action needed.

## 4. Environment variables

Project → **Settings → Environment Variables**. Vercel has three scopes: **Production**, **Preview**, **Development**. Set each variable to the right scope(s).

Pull the values from your local `.env` / password manager (same values as the GH `production` environment — see [CI_SECRETS.md](CI_SECRETS.md)).

### Set for BOTH Production + Preview

| Name | Notes |
|---|---|
| `DATABASE_URL` | Same Supabase URL (we share one DB across envs for now) |
| `GROQ_API_KEY` | |
| `GEMINI_API_KEY` | optional |
| `VOYAGE_API_KEY` | |
| `LANGFUSE_PUBLIC_KEY` | |
| `LANGFUSE_SECRET_KEY` | |
| `LANGFUSE_BASE_URL` | `https://cloud.langfuse.com` |
| `NEXT_PUBLIC_SENTRY_DSN` | browser error tracking |
| `SENTRY_DSN` | server-side error tracking |

> Note: most of these matter for the agent, not the web app. The web app currently only needs `DATABASE_URL` (to read papers) + the `NEXT_PUBLIC_SENTRY_*` / `SENTRY_*` vars. Setting the rest now is harmless and saves a round-trip when the web app grows.

### Set per-scope (different value each)

| Name | Production value | Preview value |
|---|---|---|
| `APP_ENV` | `production` | `preview` |
| `SENTRY_ENVIRONMENT` | `production` | `preview` |
| `NEXT_PUBLIC_SENTRY_ENVIRONMENT` | `production` | `preview` |
| `LOG_LEVEL` | `INFO` | `INFO` |

### Set for Production only (build-time, Sentry source maps)

| Name | Notes |
|---|---|
| `SENTRY_AUTH_TOKEN` | enables source-map upload during `next build`. Without it, builds still succeed but Sentry shows minified stack traces. |
| `SENTRY_ORG` | your org slug |
| `SENTRY_PROJECT` | `arxivdigest-web` |

## 5. First deploy

After settings are saved, trigger a deploy:
- Push to `main` (or click **Deploy** on the import screen), OR
- Redeploy from the **Deployments** tab.

Watch the build log. Expected: `next build` produces the same 5 routes we see locally (`/`, `/_not-found`, `/docs/[[...slug]]`).

If `SENTRY_AUTH_TOKEN` is set, you'll also see source maps upload near the end.

## 6. Verify

- Visit the production URL → landing page renders (ArxivDigest hero + status card).
- Visit `/docs` → Fumadocs page renders.
- Open a PR from a feature branch → Vercel bot comments with a preview URL.

## 7. Custom domain (later)

When ready (`arxivdigest.dev` or whatever you register):
- Project → **Settings → Domains → Add**.
- Follow Vercel's DNS instructions (A record / CNAME, or use Vercel nameservers).
- Production branch (`main`) serves the apex domain; previews get `*.vercel.app` URLs.

## Gotchas

- **Root Directory is the #1 thing people miss.** If you forget it, Vercel tries to build the repo root and fails (no Next.js app there).
- **`NEXT_PUBLIC_*` vars are baked at build time**, not runtime. Changing them requires a redeploy.
- **Preview deploys hitting the real DB** — since we share one Supabase project, preview deploys read/write the same `papers` table as production. Fine for now (read-only web app); revisit if previews start mutating data.
- **Sentry build wrapper without auth token** — builds fine, just no source maps. Not an error.
