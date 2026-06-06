# Roadmap

The public, single-page view. Detail (deadlines, risk register, weekly
checklists, success metrics) lives in
[`docs/PLANNING.md`](./docs/PLANNING.md) — this file is the **what**;
that one is the **how and why**.

Status legend: ✅ shipped · 🟡 in progress · ⬜ planned · ⏸ deferred

---

## V0 — Working pipeline + public site &nbsp; *(closing now)*

The minimum that earns the right to call this a "production" agent.

- ✅ End-to-end LangGraph pipeline: crawl → relevance → classify → embed → summarize → rank → publish
- ✅ Daily GitHub Actions cron (07:00 UTC, ~14-20 min)
- ✅ Public site at [arxiv-digest-preview.vercel.app](https://arxiv-digest-preview.vercel.app) — papers, status, archive, about, /docs
- ✅ 95-paper hand-labeled ground-truth set + `arxivdigest eval` harness (multi-label F1, schema validity, keyword coverage)
- ✅ Daily-cron eval regression gate (`--fail-on-regression`) — see [ADR-0008](./apps/web/content/docs/adr/0008-daily-cron-eval-gate.mdx)
- ✅ Eval history page at `/docs/evals/history` (sortable, paginated, sparkline, per-theme F1)
- ✅ Cron-side persistence of `last_report.json` + `history.jsonl` to `main` with `[skip ci]`
- ✅ Sentry + Langfuse + structlog observability
- ✅ Stale-`runs` sweeper recovers from SIGKILL'd CI runs
- ✅ Architecture diagrams + 8 ADRs + runbooks at `/docs`
- ✅ Apache 2.0 license + NOTICE (attribution required) + CONTRIBUTING
- ⬜ Architecture deep-dive blog post
- ⬜ 90-second demo Loom
- ⬜ GitHub profile pin
- ⬜ 14 consecutive green daily runs

**Exit criterion:** 14-day green streak + one published writeup + pinned on profile.

---

## V1 — Polish + community pull &nbsp; *(1-2 months after V0)*

Turn the working system into something worth subscribing to.

### Quality / eval

- ⬜ Ground-truth set 95 → 200 papers (thin in `cs.RO` + `cs.CR` today)
- ⬜ Per-PR eval gate (currently daily-only) running against a labelled subset for speed
- ⬜ Drift detector — alert when per-theme F1 dips week-on-week even if above floor
- ⬜ Adversarial eval set — 20 papers picked to stress classify
- ⬜ Property-based tests for ranking + classification via hypothesis
- ⬜ Shadow prompt experiment — v2 in parallel with v1 for 7 days; eval decides promotion

### Content / UX

- ✅ **RSS feed at `/feed.xml`** — 50 most recent ranked papers, auto-discovered via `<link rel="alternate">`
- ⬜ Semantic search bar over summaries (pgvector already wired)
- ⬜ Filter UI on `/papers` — theme, date range, impact-score bucket
- ⬜ `/papers/[id]` detail page — summary + classification audit trail + theme chips + arxiv link
- ⬜ Theme trend charts on `/themes/[slug]`
- ⬜ Per-author tracking pages
- ⬜ Mobile reading UX pass

### Coverage

- ⬜ Add `cs.RO`, `cs.CR`, `stat.ML` to the crawl
- ⬜ Tunable `DAILY_LIMIT` per category

### Distribution

- ⬜ Daily LinkedIn / Twitter cross-post (manual → automated)
- ⬜ Public Langfuse dashboard link on `/about`

### Operational maturity

- ⬜ Synthetic monitoring — `arxivdigest health` every 6h
- ⬜ Runbooks for: Supabase pause, eval regression, prompt rollback, cost spike
- ⬜ Backup verification script — monthly restore drill
- ⬜ Disaster recovery doc per dependency

---

## V2 — Personalisation + reach &nbsp; *(3-6 months, traction-gated)*

Only pursue if V1 metrics confirm appetite (100+ stars, 50+ DAU).

### Subscriptions

- ⬜ **Email digest** via Resend / Loops / Postmark
- ⬜ Custom themes — user picks 3 themes, gets filtered digest (needs auth)
- ⬜ Saved papers / reading list

### Discoverability

- ⬜ Public read-only API at `/api/v1/papers`
- ⬜ Newsletter cross-post automation (Substack)
- ⬜ Audio digest — TTS over the top-3 papers + podcast feed
- ⬜ Discord / Slack notifier webhook

### Quality V2

- ⬜ Cross-encoder re-ranking — bge-reranker over top-50 retrieved
- ⬜ Paper relationships graph — kNN over embeddings; "similar to X" sidebar
- ⬜ Citation alert — notify subscriber when paper X is cited
- ⬜ Multi-model leaderboard — Claude vs Gemini vs Groq classify
- ⬜ Active-learning loop — user feedback signals re-rank weights

---

## V3 — Production-grade ops &nbsp; *(only when scale / reliability demands)*

- ⬜ Self-hosted LLM fallback — vLLM on Runpod with cost cap
- ⬜ Multi-region Batch / failover — Frankfurt + Mumbai
- ⬜ Automated backup verification + DR runbook
- ⬜ Cost telemetry dashboard on `/about`
- ⏸ Premium tier / sponsorship — only after Apache-2.0 core is stable + 1k+ stars

---

## Cross-cutting backlog &nbsp; *(any phase)*

- ⬜ **Per-paper "why this score" explainer** &nbsp;← high portfolio value
- ⬜ LLM cache layer (instructor-compat)
- ⬜ Embedding-similarity dedup within a 7-day window
- ⬜ CSP headers + gitleaks + trivy in CI + Renovate (V1+ noted in `security.mdx`)
- ⬜ "Good first issue" labels + profile pin

---

## Contributing to the roadmap

Got an idea? Open an issue with the tag `roadmap`. PRs that move ⬜ → ✅
are welcome — please reference the line above in your description so
reviewers know which slot is closing.

See [CONTRIBUTING.md](./CONTRIBUTING.md) for the workflow and the
attribution requirement (Apache 2.0 + NOTICE).
