# CI Secrets and Variables

How environment variables map to GitHub Actions for ArxivDigest.

## Principle

- **Secrets** — sensitive values that should never appear in logs or browser bundles (API keys with billing impact, DB passwords).
- **Variables** — non-sensitive config that's safe to read in workflow logs (hostnames, public DSNs by design, env names, log levels).
- **Environments** — access boundary. `production` secrets are only readable by workflows that explicitly opt into `environment: production`, and (via branch protection rules) only when running on `main`.

We use **GitHub Environments** for the access boundary. All current values live under the `production` environment. A `staging` environment will be added when there's a non-production workflow that needs its own values.

---

## production environment

### Secrets — `gh secret set <NAME> --env production`

| Name | Source | Notes |
|---|---|---|
| `DATABASE_URL` | Supabase Studio → Database → Connection string (URI, **Transaction** pooler, port 6543) | `postgresql://postgres.<ref>:<password>@<region>.pooler.supabase.com:6543/postgres` |
| `GROQ_API_KEY` | https://console.groq.com/keys | Starts with `gsk_...` |
| `GEMINI_API_KEY` | https://aistudio.google.com/apikey | Starts with `AIza...` — failover only, can defer |
| `VOYAGE_API_KEY` | https://dash.voyageai.com → API Keys | Starts with `pa-...` |
| `LANGFUSE_PUBLIC_KEY` | Langfuse Cloud → Settings → API Keys | Starts with `pk-lf-...` — despite the name, this is an auth credential |
| `LANGFUSE_SECRET_KEY` | Same screen | Starts with `sk-lf-...` |
| `SENTRY_AUTH_TOKEN` | https://sentry.io/settings/<org>/auth-tokens/ | Scopes: `project:releases` + `org:read`. Build-time only (Vercel + CI source-map upload). |

### Variables — `gh variable set <NAME> --env production --body <value>`

| Name | Value | Why a var, not a secret |
|---|---|---|
| `APP_ENV` | `production` | Just an env tag |
| `SENTRY_ENVIRONMENT` | `production` | Sentry env tag |
| `NEXT_PUBLIC_SENTRY_ENVIRONMENT` | `production` | Browser-visible by design |
| `LOG_LEVEL` | `INFO` | Plain config |
| `LANGFUSE_HOST` | `https://cloud.langfuse.com` | Public URL |
| `SENTRY_DSN` | `https://<hash>@<org>.ingest.sentry.io/<project-id>` | **Sentry DSNs are public-safe by design** — they ship in browser bundles and are rate-limited per project |
| `NEXT_PUBLIC_SENTRY_DSN` | Same DSN as above (or the web-project DSN if you created two Sentry projects) | Browser-visible |
| `SENTRY_ORG` | Your Sentry org slug, e.g. `imtiaj` | From `sentry.io/organizations/<slug>/` |
| `SENTRY_PROJECT` | Next.js project slug, e.g. `arxivdigest-web` | Used by `withSentryConfig` for source-map upload |

---

## Setup via `gh` CLI

Make sure your personal GitHub account (`imtiaj-007`) is the active `gh` auth — `gh auth status` should show it. If not: `gh auth login` and pick personal.

### 1. Create the production environment

```sh
gh api -X PUT repos/imtiaj-007/ArxivDigest/environments/production -f deployment_branch_policy=null
```

Then in the GitHub UI (Settings → Environments → production), optionally:
- Set **Deployment branches and tags** → "Selected branches" → add `main` only. Prevents accidental use of prod secrets from other branches.
- Enable **Required reviewers** if you want manual approval before any prod-env workflow runs (overkill for a personal project).

### 2. Set secrets

```sh
# Replace the right-hand values with real ones from your password manager.
gh secret set DATABASE_URL          --env production --body "postgresql://..."
gh secret set GROQ_API_KEY          --env production --body "gsk_..."
gh secret set GEMINI_API_KEY        --env production --body "AIza..."
gh secret set VOYAGE_API_KEY        --env production --body "pa-..."
gh secret set LANGFUSE_PUBLIC_KEY   --env production --body "pk-lf-..."
gh secret set LANGFUSE_SECRET_KEY   --env production --body "sk-lf-..."
gh secret set SENTRY_AUTH_TOKEN     --env production --body "sntrys_..."
```

Or pipe from your local `.env` to avoid pasting into the terminal:

```sh
gh secret set DATABASE_URL --env production < <(grep '^DATABASE_URL=' .env | cut -d= -f2-)
```

### 3. Set variables

```sh
gh variable set APP_ENV                         --env production --body "production"
gh variable set SENTRY_ENVIRONMENT              --env production --body "production"
gh variable set NEXT_PUBLIC_SENTRY_ENVIRONMENT  --env production --body "production"
gh variable set LOG_LEVEL                       --env production --body "INFO"
gh variable set LANGFUSE_HOST                   --env production --body "https://cloud.langfuse.com"
gh variable set SENTRY_DSN                      --env production --body "https://...@sentry.io/..."
gh variable set NEXT_PUBLIC_SENTRY_DSN          --env production --body "https://...@sentry.io/..."
gh variable set SENTRY_ORG                      --env production --body "<your-org-slug>"
gh variable set SENTRY_PROJECT                  --env production --body "arxivdigest-web"
```

### 4. Verify

```sh
gh secret list   --env production
gh variable list --env production
```

Should list 7 secrets and 9 variables.

### 5. Trigger a test run

Via UI: **Actions → daily-digest → Run workflow**.

Or CLI:

```sh
gh workflow run daily-digest.yml
```

Watch logs: `gh run watch`.

---

## Adding `staging` later

When you add a workflow that needs staging values (e.g. an integration test job on `dev` PRs):

1. Create the environment:
   ```sh
   gh api -X PUT repos/imtiaj-007/ArxivDigest/environments/staging
   ```
2. Set its branch policy to `dev` only.
3. Duplicate the secrets/vars under `--env staging`, swapping the values that differ — only `APP_ENV`, `SENTRY_ENVIRONMENT`, `NEXT_PUBLIC_SENTRY_ENVIRONMENT` (and potentially `DATABASE_URL` if you spin up a separate Supabase project).
4. Add `environment: staging` to the new workflow.

## Vercel parity

Vercel has its own env-var UI (project → Settings → Environment Variables) with three scopes: **Production / Preview / Development**. Mirror the same split:

- All **secrets** above → also set in Vercel under **Production** (and Preview if you want preview deploys to talk to real services).
- `SENTRY_AUTH_TOKEN` → Vercel Production only (build-time source maps).
- Non-secret **variables** → set in Vercel as plain env vars at the same scope.

We'll wire this in Phase 6 Step 4 (Vercel link).
