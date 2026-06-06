# Planning + Roadmap

## Phase map

```
V0 — Working pipeline + public site                   (3-4 weeks)  ← closing now
V1 — Polish + community pull                          (~1-2 months)
V2 — Personalisation + reach                          (3-6 months, traction-gated)
V3 — Production-grade ops                             (only when scale/reliability demands)
```

Public companion: [ROADMAP.md](../ROADMAP.md) — single-page version, lives at repo root, kept in sync.

## V0 — Working pipeline + public site

**Objective:** end-to-end agentic pipeline shipping a daily public digest; full observability + eval gate.

**Done means:**
- Agent runs daily for 14 consecutive days unattended
- Site is live at a real URL (custom domain or github.io)
- Eval F1 ≥ 0.85 on a 50-paper ground-truth set
- Architecture diagram + README pitch are interview-ready
- Public `/status` page shows last 30 days of runs

### Week 1 — Foundations + happy-path agent

Goal: by end of week, a hand-triggered agent run produces a structured paper digest.

- [ ] **Repo scaffolding** — Turborepo monorepo, `apps/web` + `apps/agent` + `packages/db`
- [ ] **Tooling setup** — `uv`, `ruff`, `mypy`, `pre-commit`, `pytest`, `pyproject.toml` finalized
- [ ] **Settings layer** — Pydantic `BaseSettings` with `SecretStr` for all keys; `.env.example` checked in
- [ ] **Sign up + configure** — Groq, Gemini, Voyage, Supabase, Langfuse, Sentry, Vercel, Cloudflare (domain)
- [ ] **Health command** — `agent health` validates all upstreams; this is the first thing built and tested
- [ ] **Domain models** — Pydantic models for `Paper`, `Theme`, `Run`, `Summary` in `core/models.py`
- [ ] **Ports** — `LLMClient`, `Embedder`, `Repository` protocols
- [ ] **Groq adapter** — `agent.adapters.llm.groq` with instructor integration
- [ ] **arxiv source adapter** — fetches yesterday's submissions for cs.AI/cs.LG/cs.CL
- [ ] **Supabase repository adapter** — `papers` table read/write via supabase-py
- [ ] **Minimal Drizzle schema + migration** — `papers`, `runs`, `themes`, `llm_audit`
- [ ] **One stage end-to-end** — crawl → summarize → write to DB. Test on 5 papers. Confirm appears in Supabase Studio.

**Exit criterion:** `uv run agent digest --limit 5 --dry-run` produces 5 structured paper entries in DB locally.

### Week 2 — Full pipeline + LangGraph orchestration

Goal: every stage built; LangGraph orchestrates; checkpointing works.

- [ ] **All adapters** — Gemini (failover), Voyage embedder, MultiLLM adapter with circuit breaker
- [ ] **All pipeline stages** — crawl, relevance, classify, embed, summarize, rank, publish
- [ ] **LangGraph state machine** — orchestrate stages; persist checkpoint after each
- [ ] **Bulkhead per paper** — one paper failing doesn't kill the run; DLQ wired
- [ ] **Rate-limit + retry** — `aiolimiter` per stage; `tenacity` exponential backoff
- [ ] **Idempotency keys** — `(arxiv_id, stage, prompt_ver)` checked before LLM call
- [ ] **Prompt versioning scaffold** — each prompt is `prompts/<stage>/v1.py`; recorded in DB per call
- [ ] **LLM audit logging** — every call writes to `llm_audit` table
- [ ] **Heartbeat task** — async task writes `runs.heartbeat_at` every 30s
- [ ] **Cost ceiling enforcement** — hard stop when projected tokens exceed budget
- [ ] **Structured logging** — `structlog` with `run_id`, `paper_id`, `stage` context propagated
- [ ] **Local Supabase via CLI** — `supabase start` for dev DB; identical schema

**Exit criterion:** `uv run agent digest` processes a real day's worth of papers (~40 kept from ~120 crawled) end-to-end in < 15min locally.

### Week 3 — Site, deployment, observability

Goal: public site live, daily cron firing, full observability stack working.

- [ ] **Next.js 15 + Fumadocs scaffold** — `apps/web` initialised; one route renders papers from DB
- [ ] **shadcn/ui + Tailwind** — components for paper card, theme filter, archive nav
- [ ] **Pages** — `/`, `/archive/[year]/[month]`, `/papers/[id]`, `/themes/[slug]`, `/status`, `/about`
- [ ] **ISR config** — revalidate intervals per page type
- [ ] **Vercel deployment** — connected to GH repo; auto-deploys on push to main
- [ ] **Domain configured** — DNS pointed; HTTPS via Vercel
- [ ] **GitHub Actions cron workflow** — `daily-digest.yml` running on schedule
- [ ] **Webhook to Vercel** — agent triggers site rebuild after publish
- [ ] **Langfuse integration** — all LLM calls traced; project shareable link tested
- [ ] **Sentry integration** — errors captured; first test alert verified
- [ ] **Status page** — reads `runs` table, renders 30-day grid
- [ ] **About page** — methodology, eval scores, cost ledger (always $0 — but the engineering shows)
- [ ] **First runbook** — `docs/runbooks/groq-down.md`

**Exit criterion:** cron fires at 06:00 UTC, agent runs, site updates by 06:15. Verified two consecutive days.

### Week 4 — Eval, polish, distribution

Goal: eval harness gates quality; project reads as portfolio-grade.

- [x] **Ground-truth set** — 95 papers hand-labeled (themes + summary keywords) via `arxivdigest label`
- [x] **Eval harness** — `arxivdigest eval` runs multi-label F1 (micro/macro/per-theme), schema validity, keyword coverage
- [x] **Eval CI gate** — daily-cron step (not per-PR — see [ADR-0008](../apps/web/content/docs/adr/0008-daily-cron-eval-gate.mdx)); fails workflow if any metric drops below `evals/baseline.json` floors
- [x] **Architecture diagram** — Mermaid in `/docs/architecture` (system overview, 6-stage pipeline, ER schema, daily sequence)
- [x] **README polish** — pitch + 6 shields.io badges (build, CI, micro_f1, schema, kw_cov, license)
- [x] **README badges** — daily-digest status, CI status, eval F1, schema, kw_cov, license
- [x] **ADRs written** — 8 ADRs surfaced as MDX at `/docs/adr` (pure-batch, Supabase, uv, hexagonal, Vercel, local-BGE, DB-as-checkpoint, daily-cron eval gate)
- [ ] **Architecture deep-dive blog post** — published on dev.to / Medium / Substack
- [ ] **Demo video** — 90-second Loom: cron firing → traces in Langfuse → site updating
- [ ] **GitHub Project board** — public roadmap visible from README
- [x] **License (Apache 2.0) + CONTRIBUTING.md** — LICENSE + NOTICE (attribution required) + CONTRIBUTING.md shipped. CODE_OF_CONDUCT explicitly skipped for now (solo project; revisit when external contributors arrive)
- [ ] **Profile pin** — repo pinned on personal GitHub profile

**Exit criterion (V0 done):** 14 consecutive days of green daily runs; eval F1 sustained ≥ 0.85; one published writeup; pinned on profile.

## V1 — Polish + community pull (~1-2 months after V0)

Goal: turn the working system into something a small community will use and stars. The public companion to this section is [ROADMAP.md](../ROADMAP.md) — keep them in sync when scoping changes.

### Quality / eval
- [ ] **Ground-truth expansion 95 → 200 papers** — current set is thin in `cs.RO` + `cs.CR` (4d)
- [ ] **Per-PR eval gate** — currently daily-only per [ADR-0008](../apps/web/content/docs/adr/0008-daily-cron-eval-gate.mdx); runs against a labelled subset for speed (2d)
- [ ] **Drift detector** — alert when per-theme F1 dips week-on-week even if absolute is above floor (2d)
- [ ] **Adversarial eval set** — 20 papers picked to stress classify (multi-domain, ambiguous, very-new themes) (2d)
- [ ] **Property-based tests** for ranking + classification logic via hypothesis (2d)
- [ ] **Shadow prompt experiment** — prompt v2 in parallel with v1 for 7 days; eval decides promotion (3d)

### Content / UX
- [x] **RSS feed at `/feed.xml`** — single biggest lever for organic readership. **SHIPPED 2026-06-06.** 50 most recent ranked papers; auto-discovered via `<link rel="alternate">`; CDATA-wrapped HTML descriptions with structured TL;DR (problem/approach/result/why_it_matters); `dc:creator` author lines + theme `<category>` tags; 1h ISR + 1y stale-while-revalidate.
- [ ] **Search over summaries** — pgvector already wired; semantic-search bar on `/papers` (3d)
- [ ] **Filter UI on `/papers`** — by theme, by date range, by impact-score bucket (2d)
- [ ] **`/papers/[id]` detail page** — full summary + classification audit trail + theme chips + arxiv link (1d)
- [ ] **Theme trend charts** — paper count per theme per week on `/themes/[slug]` (2d)
- [ ] **Per-author tracking** — if author appears 3+ times, dedicated page (2d)
- [ ] **Mobile reading UX pass** (1d)

### Coverage
- [ ] **Add `cs.RO`, `cs.CR`, `stat.ML` to crawl** — config-level; just bumps daily volume (0.5d)
- [ ] **Tunable `DAILY_LIMIT` per category** — today it's global (0.5d)

### Distribution
- [ ] **Daily LinkedIn / Twitter post** — manual at first; automate at V1.5
- [ ] **Public Langfuse dashboard link** from `/about` (0.5d)

### Operational maturity
- [ ] **Synthetic monitoring** — separate GH Action runs `arxivdigest health` every 6h (1d)
- [ ] **Runbooks for**: Supabase pause, eval regression, prompt rollback, cost spike (already started in `/docs/runbooks`) (2d)
- [ ] **Backup verification** — monthly script restores Supabase backup to a local DB (1d)
- [ ] **Disaster recovery doc** — what to do if Supabase / Vercel / GH each go down (1d)

### Success metrics for V1
- 100+ GitHub stars
- 50+ unique daily visitors organically
- One external mention (blog, newsletter, tweet)
- Eval F1 ≥ 0.90 sustained
- Two blog posts published

## V2 — Personalisation + reach (3-6 months)

**Only pursue if V1 metrics confirm appetite.**

### Subscriptions
- [ ] **Email digest** — Resend / Loops / Postmark; one-line-per-paper + click-through (4-5d)
- [ ] **Custom themes** — user picks 3 themes, gets filtered digest (needs auth: Supabase Auth) (1w)
- [ ] **Saved papers / reading list** — needs auth (3d after auth lands)

### Discoverability
- [ ] **Public read-only API** — `/api/v1/papers?theme=X&date=Y` (2d)
- [ ] **Newsletter cross-post automation** — auto-post daily digest to Substack (2d)
- [ ] **Audio digest** — TTS over the top-3 papers; podcast feed (3-4d)
- [ ] **Discord / Slack notifier** — webhook on digest publish (1d)

### Quality V2
- [ ] **Cross-encoder re-ranking** — small bge-reranker over the top-50 retrieved per query (3d)
- [ ] **Paper relationships graph** — embeddings → kNN → "papers similar to X" sidebar (2d)
- [ ] **Citation alert** — notify subscriber when paper X gets cited by anything in the crawl (1w)
- [ ] **Multi-model leaderboard** — "Claude vs Gemini vs Groq classify" comparison page (1-2w)
- [ ] **Active-learning loop** — user feedback signals re-rank weights (2-4w)

## V3 — Production-grade ops (when scale or reliability demands it)

- [ ] **Self-hosted LLM fallback** — vLLM on Runpod with cost-cap; triggered when Groq + Gemini both rate-limited (1w)
- [ ] **Multi-region Batch / failover** — Frankfurt + Mumbai cutover (3d)
- [ ] **Disaster-recovery runbook + automated backup** — Supabase PITR + S3 snapshot (2d)
- [ ] **Cost telemetry dashboard** — Langfuse per-stage cost; surface on `/about` (1d)
- [ ] **Premium tier / sponsorship** — only after Apache-2.0-licensed core is stable + 1k+ stars

## Cross-cutting backlog (do alongside any phase)

- [ ] **Per-paper "why this score" explainer** — LLM reasoning for impact score; high portfolio value (2d)
- [ ] **LLM cache layer** — instructor-compat; cuts re-runs to ~0 cost (2d)
- [ ] **Embedding-similarity dedup** — within a 7-day window (1d)
- [ ] **CSP headers + gitleaks + trivy in CI + Renovate** — already noted as V1+ items in `security.mdx` (2d total)
- [ ] **"Good first issue" labels + profile pin** — community on-ramp (0.5d)

## What I'd actually prioritise next

### If the goal is **portfolio impact** (current frame — job-switch context)

1. **RSS feed + custom domain** — earliest readership signal; one day of work for outsized return
2. **Per-paper "why this score" explainer** — pure AI-engineering story, screen-recordable for interviews
3. **Semantic search** — uses pgvector you already have; one good demo screen worth more than 10 blog posts
4. **Ground-truth expansion + per-PR eval gate** — the "this person takes evals seriously" signal hiring panels look for

~3 weeks of evening work; gives 3 strong demos + a clear "I treat eval as production infra" narrative.

### If the goal is **monetisation later**

1. Email digest first (subscriber list = the asset)
2. Then custom themes
3. Then API access (paid-tier candidate)

## Risk register

| Risk | Likelihood | Impact | Mitigation | Status |
|---|---|---|---|---|
| Solo bus factor | High | Medium | Apache 2.0 license; documented; ADRs; runbooks | Mitigated by V0 docs |
| Groq free tier tightened mid-V1 | Medium | High | Gemini failover proven in V0; Cerebras as 3rd | Mitigated |
| Supabase pause during gap | Low (daily cron) | Medium | Cron pings DB daily | Mitigated |
| Prompt regression breaks output | Medium | High | Eval CI gate blocks merges | Mitigated in V0 W4 |
| arxiv API changes / blocks scraping | Low | Critical | Use official API only; respect rate limits | Acceptable |
| Side-project time runs out | High | Medium | V0 is 3-4 weeks; clear stop point | Acceptable |
| Site grows beyond free tier | Low at V1; Medium at V2 | Low (clear migration path) | Cost ceiling alerts at 80% of any tier | Mitigated |

## Decision points

These need explicit go/no-go after V0:

- [ ] **Custom domain or `.github.io`?** — depends on V0 polish budget
- [ ] **Email digest in V1 or V2?** — depends on RSS engagement
- [ ] **Open shadow prompt experiments to public?** — Langfuse dashboard or keep private
- [ ] **Accept first PRs from community?** — set contribution guidelines beforehand
- [ ] **Apply to YC / write up as paper / pitch as product?** — only relevant at V2 traction

## Cadence + working style

- **Daily check** — 10min: did cron fire? Sentry errors? Eval drift?
- **Weekly review** — Sunday evening: review `runs` history, eval trend, open issues, pick week's priority
- **Monthly retro** — what worked, what's stuck, adjust V1/V2 sequencing
- **Blog post cadence** — 1 post per 2 weeks while in V1; whatever pace sustains in V2

## "Stop signals"

Reasons to pause / wind down ArxivDigest, listed honestly so they don't surprise:

- Job switch lands; new role consumes all evening time → pause maintenance, leave docs clear
- Eval F1 starts trending down faster than fixes can keep up → step back, redesign prompts
- Free tiers tighten across the board → publish cost analysis, ask if community wants to fund or fork
- Personal life shift → Apache 2.0 license means anyone can pick it up (with attribution)

## V0 weekly checklist (printable)

### Week 1
- [x] Repo + tooling + signups
- [x] Domain models + ports
- [x] First adapter (Groq) + first stage (summarize) working on 5 papers
- [x] Schema + migration in DB

### Week 2
- [x] All stages
- [x] LangGraph orchestration + checkpointing
- [x] Idempotency + DLQ + rate limits
- [x] Local end-to-end on ~40 papers

### Week 3
- [x] Next.js site + Vercel + cron
- [x] Langfuse + Sentry wired
- [x] Status page + about page
- [x] First production daily run

### Week 4
- [x] Eval harness + ground truth
- [x] CI gates + ADRs + diagrams (Mermaid in `/docs/architecture`)
- [ ] Blog post + demo video + profile pin
- [ ] 14-day consecutive green runs (rolls into V1)
