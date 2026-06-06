<div align="center">

# 📚 ArxivDigest

<p><em>Autonomous daily AI agent that scans new arxiv submissions, produces structured TL;DRs, classifies them by theme, and ranks them by novelty + impact — published every morning, unattended, at <strong>$0/month</strong>.</em></p>

<p>
  <a href="https://github.com/imtiaj-007/ArxivDigest/actions/workflows/daily-digest.yml"><img alt="daily-digest" src="https://github.com/imtiaj-007/ArxivDigest/actions/workflows/daily-digest.yml/badge.svg"></a>
  <a href="https://github.com/imtiaj-007/ArxivDigest/actions/workflows/ci.yml"><img alt="CI" src="https://github.com/imtiaj-007/ArxivDigest/actions/workflows/ci.yml/badge.svg"></a>
  <a href="./LICENSE"><img alt="License: Apache 2.0" src="https://img.shields.io/badge/license-Apache_2.0-blue"></a>
  <a href="https://arxiv-digest-preview.vercel.app/about"><img alt="cost" src="https://img.shields.io/badge/cost-%240%2Fmo-brightgreen"></a>
</p>

<p>
  <a href="https://arxiv-digest-preview.vercel.app/about"><img alt="micro F1" src="https://img.shields.io/badge/dynamic/json?label=micro%20F1&query=%24.classification.micro_f1&url=https%3A%2F%2Fraw.githubusercontent.com%2Fimtiaj-007%2FArxivDigest%2Fmain%2Fevals%2Flast_report.json&color=brightgreen"></a>
  <a href="https://arxiv-digest-preview.vercel.app/about"><img alt="macro F1" src="https://img.shields.io/badge/dynamic/json?label=macro%20F1&query=%24.classification.macro_f1&url=https%3A%2F%2Fraw.githubusercontent.com%2Fimtiaj-007%2FArxivDigest%2Fmain%2Fevals%2Flast_report.json&color=brightgreen"></a>
  <a href="https://arxiv-digest-preview.vercel.app/about"><img alt="schema validity" src="https://img.shields.io/badge/dynamic/json?label=schema%20validity&query=%24.schema_validity_rate&url=https%3A%2F%2Fraw.githubusercontent.com%2Fimtiaj-007%2FArxivDigest%2Fmain%2Fevals%2Flast_report.json&color=brightgreen"></a>
  <a href="https://arxiv-digest-preview.vercel.app/about"><img alt="keyword coverage" src="https://img.shields.io/badge/dynamic/json?label=kw%20coverage&query=%24.avg_keyword_coverage&url=https%3A%2F%2Fraw.githubusercontent.com%2Fimtiaj-007%2FArxivDigest%2Fmain%2Fevals%2Flast_report.json&color=brightgreen"></a>
</p>

<p>
  <a href="https://arxiv-digest-preview.vercel.app">🌐&nbsp;<strong>Live site</strong></a> &nbsp;·&nbsp;
  <a href="https://arxiv-digest-preview.vercel.app/docs">📖&nbsp;<strong>Docs</strong></a> &nbsp;·&nbsp;
  <a href="https://arxiv-digest-preview.vercel.app/docs/evals/history">📊&nbsp;<strong>Eval history</strong></a> &nbsp;·&nbsp;
  <a href="https://arxiv-digest-preview.vercel.app/status">🟢&nbsp;<strong>Status</strong></a> &nbsp;·&nbsp;
  <a href="./ROADMAP.md">🗺&nbsp;<strong>Roadmap</strong></a>
</p>

<p>
  <img alt="Python 3.12" src="https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white">
  <img alt="uv" src="https://img.shields.io/badge/uv-Astral-DE5FE9?logo=astral&logoColor=white">
  <img alt="LangGraph" src="https://img.shields.io/badge/LangGraph-stateful_agents-1C3C3C?logo=langchain&logoColor=white">
  <img alt="Groq" src="https://img.shields.io/badge/Groq-Llama_3.3_70B-F55036?logo=meta&logoColor=white">
  <img alt="Next.js 16" src="https://img.shields.io/badge/Next.js-16-000000?logo=nextdotjs&logoColor=white">
  <img alt="Tailwind v4" src="https://img.shields.io/badge/Tailwind-v4-06B6D4?logo=tailwindcss&logoColor=white">
  <img alt="Supabase" src="https://img.shields.io/badge/Supabase-Postgres_%2B_pgvector-3ECF8E?logo=supabase&logoColor=white">
  <img alt="Vercel" src="https://img.shields.io/badge/Vercel-Deploy-000000?logo=vercel&logoColor=white">
  <img alt="GitHub Actions" src="https://img.shields.io/badge/GH_Actions-cron-2088FF?logo=githubactions&logoColor=white">
  <img alt="Langfuse" src="https://img.shields.io/badge/Langfuse-traces-blue">
  <img alt="Sentry" src="https://img.shields.io/badge/Sentry-errors-362D59?logo=sentry&logoColor=white">
</p>

</div>

---

> **V0 closing.** Daily cron live · eval regression gate live · eval history with sparkline · stale-row sweeper recovers from CI SIGKILL · `last_report.json` + `history.jsonl` persisted to `main` on every cron. Micro F1 sustains in **0.85–0.91** on the 95-paper hand-labelled ground-truth set.

## ⚡ What it does

Every morning at **07:00 UTC**, a LangGraph pipeline runs end-to-end:

<table>
  <tr>
    <td align="center" width="80">1️⃣<br><strong>Crawl</strong></td>
    <td>Fetch the last day's <code>cs.AI</code> / <code>cs.LG</code> / <code>cs.CL</code> submissions from arxiv's Atom API.</td>
  </tr>
  <tr>
    <td align="center">2️⃣<br><strong>Summarize</strong></td>
    <td>Groq Llama 3.3 70B + <code>instructor</code> produces a structured TL;DR (problem / approach / result / why it matters), grounded strictly in the abstract.</td>
  </tr>
  <tr>
    <td align="center">3️⃣<br><strong>Classify</strong></td>
    <td>Llama 3.1 8B assigns 1–3 themes from a 14-theme taxonomy, post-validated against the canonical set.</td>
  </tr>
  <tr>
    <td align="center">4️⃣<br><strong>Embed</strong></td>
    <td>Local <code>BAAI/bge-large-en-v1.5</code> (1024-d) on CPU; vectors land in pgvector with an HNSW + cosine index.</td>
  </tr>
  <tr>
    <td align="center">5️⃣<br><strong>Rank</strong></td>
    <td>Blend pgvector novelty (cosine distance to nearest neighbours) with an LLM impact judgment into <code>papers.score</code>.</td>
  </tr>
  <tr>
    <td align="center">6️⃣<br><strong>Publish</strong></td>
    <td>Write a <code>digests</code> row from the top-K, fire on-demand revalidation so the site updates immediately.</td>
  </tr>
</table>

Each stage is **idempotent** and reads its own pending work from the database (`X IS NULL`), so the DB status columns *are* the resume checkpoint — a crashed run is recovered by re-running the graph. See [ADR-0007](https://arxiv-digest-preview.vercel.app/docs/adr/0007-db-status-as-resume-checkpoint).

## 🛡 Free-tier hardening for the daily run

<table>
<tr>
<td valign="top" width="220"><strong>🚦 Groq rate-limit safety</strong></td>
<td>Per-model <code>aiolimiter</code> token bucket (proactive pacing, never trips per-minute caps in the hot path) + <code>tenacity</code> backoff honouring Groq's <code>Retry-After</code> header + <code>MultiLLMClient</code> Gemini failover (dormant; activated by setting <code>GEMINI_API_KEY</code>).</td>
</tr>
<tr>
<td valign="top"><strong>📡 arxiv 429 backoff</strong></td>
<td>5-attempt exponential backoff, then graceful empty-list return so the run goes green on a no-op day rather than red.</td>
</tr>
<tr>
<td valign="top"><strong>🧠 Local embeddings</strong></td>
<td>BGE-large runs on CPU; no API, no rate limit, model weights cached across GH Actions runs.</td>
</tr>
<tr>
<td valign="top"><strong>🪣 Per-paper bulkhead</strong></td>
<td>One failed call is logged and skipped — the run continues. Failure counted in <code>schema_validity_rate</code>.</td>
</tr>
<tr>
<td valign="top"><strong>🧹 Stale-row sweeper</strong></td>
<td>If CI SIGKILLs the agent mid-pipeline, the next run reconciles abandoned <code>runs</code> rows before starting. <code>/status</code> never gets stuck on a ghost.</td>
</tr>
<tr>
<td valign="top"><strong>📦 Eval persist-back</strong></td>
<td>Every cron commits <code>last_report.json</code> + <code>history.jsonl</code> to <code>main</code> with <code>[skip ci]</code>. Quality history survives the ephemeral runner; <code>/docs/evals/history</code> sparkline updates on the next Vercel rebuild.</td>
</tr>
</table>

Runs autonomously, **$0/month** on free tiers, every LLM call traced in Langfuse, every uncaught error in Sentry, every run recorded in the `runs` table and rendered as a 30-day grid on `/status`.

## 🌐 Public surface

| Route | What |
|---|---|
| `/papers` | Latest ranked digest |
| `/papers/[arxiv_id]` | Per-paper detail + 5 cosine-NN similar papers |
| `/themes/[slug]` | Theme-filtered list |
| `/archive/[year]/[month]` | Month-filtered list with prev/next nav |
| `/status` | 30-day run grid + recent runs table |
| `/about` | Stack, cost ledger, live quality metrics |
| `/docs/*` | Engineering docs: methodology · architecture · stack · prompts · testing · evals · observability · security · runbooks · ADRs |

## 🗺 Roadmap

| Phase | Timeframe | Highlights |
|---|---|---|
| **V0** &nbsp;*(closing)* | now | Pipeline · cron · eval gate · history page · sweeper · persist-back |
| **V1** | 1–2 months | RSS feed · semantic search · ground-truth 95 → 200 · per-PR eval gate |
| **V2** &nbsp;*(traction-gated)* | 3–6 months | Email digest · custom themes · cross-encoder re-ranking · paper-relationships graph |
| **V3** &nbsp;*(scale-driven)* | open | Self-hosted LLM fallback · multi-region failover |

Full ⬜ / 🟡 / ✅ checklist in [**ROADMAP.md**](./ROADMAP.md) · internal phase plan + risk register in [**docs/PLANNING.md**](./docs/PLANNING.md).

## 📖 Documentation

<details>
<summary><strong>Engineering + ops docs (live on the site)</strong></summary>

| Doc | Live URL |
|---|---|
| Methodology | [/docs/methodology](https://arxiv-digest-preview.vercel.app/docs/methodology) |
| Theme taxonomy | [/docs/themes](https://arxiv-digest-preview.vercel.app/docs/themes) |
| Architecture (Mermaid diagrams) | [/docs/architecture](https://arxiv-digest-preview.vercel.app/docs/architecture) |
| Tech stack | [/docs/stack](https://arxiv-digest-preview.vercel.app/docs/stack) |
| Prompts | [/docs/prompts](https://arxiv-digest-preview.vercel.app/docs/prompts) |
| Testing | [/docs/testing](https://arxiv-digest-preview.vercel.app/docs/testing) |
| Eval harness — overview | [/docs/evals](https://arxiv-digest-preview.vercel.app/docs/evals) |
| Eval harness — full history (sparkline + per-theme F1) | [/docs/evals/history](https://arxiv-digest-preview.vercel.app/docs/evals/history) |
| Observability | [/docs/observability](https://arxiv-digest-preview.vercel.app/docs/observability) |
| Security | [/docs/security](https://arxiv-digest-preview.vercel.app/docs/security) |
| Runbooks | [/docs/runbooks](https://arxiv-digest-preview.vercel.app/docs/runbooks) |
| Architecture Decision Records (8 + counting) | [/docs/adr](https://arxiv-digest-preview.vercel.app/docs/adr) |

</details>

<details>
<summary><strong>Repo-only docs (setup + meta)</strong></summary>

| Doc | Purpose |
|---|---|
| [PROJECT.md](./docs/PROJECT.md) | Vision, scope, success criteria, non-goals |
| [ROADMAP.md](./ROADMAP.md) | Public single-page view of V0 → V3 |
| [PLANNING.md](./docs/PLANNING.md) | Internal phase plan, week-by-week, risk register |
| [CONTRIBUTING.md](./CONTRIBUTING.md) | Workflow + attribution requirement (Apache 2.0) |
| [CI_SECRETS.md](./docs/CI_SECRETS.md) | GH Actions secrets + variables setup |
| [VERCEL_SETUP.md](./docs/VERCEL_SETUP.md) | Web deployment + env vars |

</details>

## 🚀 Quick start

```bash
# Install
pnpm install
uv sync --directory apps/agent

# Run the agent locally (5 papers)
cd apps/agent && uv run arxivdigest run --limit 5

# Run the web app locally
pnpm --filter web dev

# Unit tests (fast, no infra)
pnpm test
uv run --directory apps/agent pytest tests/unit/ -q

# Integration tests (need a real Postgres — set TEST_DATABASE_URL)
TEST_DATABASE_URL='postgresql://...' \
    uv run --directory apps/agent pytest tests/integration/ -q
```

You'll need a `.env` at the repo root with `DATABASE_URL`, `GROQ_API_KEY`, plus optional observability keys. See [`.env.example`](./.env.example).

For the full contributor workflow (branch naming, lint stack, attribution requirement), see [**CONTRIBUTING.md**](./CONTRIBUTING.md).

## 🧰 Tech stack — one line

**Python 3.12** *(uv + LangGraph + instructor + Groq + sentence-transformers)* → **Supabase Postgres + pgvector** → **Next.js 16** *(App Router + Tailwind v4 + shadcn base-nova + Fumadocs)* on **Vercel**. Orchestrated by **GitHub Actions cron**. Observed via **Langfuse + Sentry + structlog**.

## 🤝 Contributing

PRs welcome — bug fixes, doc improvements, ADR follow-ups, small UX wins. See [**CONTRIBUTING.md**](./CONTRIBUTING.md) for the workflow.

Two house rules from the license:

1. **Inbound = outbound.** PRs are accepted under Apache 2.0.
2. **Attribution stays with the code.** Forks and derivative work must keep the [NOTICE](./NOTICE) and credit the upstream repo.

## 📜 License

[**Apache License 2.0**](./LICENSE) — permissive grant, attribution required via [NOTICE](./NOTICE).

If you fork, copy, or build on this code, please retain the NOTICE file and credit the original project at [github.com/imtiaj-007/ArxivDigest](https://github.com/imtiaj-007/ArxivDigest). Pull requests welcome — please don't strip attribution.

---

<div align="center">
  <sub>Built by <a href="https://github.com/imtiaj-007">SK Imtiaj Uddin</a> · <a href="https://arxiv-digest-preview.vercel.app">arxiv-digest-preview.vercel.app</a></sub>
</div>
