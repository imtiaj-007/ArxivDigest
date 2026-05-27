# Planning + Roadmap

## Phase map

```
V0 — Working pipeline + public site                   (3-4 weeks)
V1 — Quality + community polish                       (~2 months)
V2 — Traction-dependent expansion                     (open-ended)
```

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

- [ ] **Ground-truth set** — 50 papers manually labeled: relevance Y/N, themes assigned, "good summary" examples
- [ ] **Eval harness** — `agent eval` runs classification F1, summary BLEU/ROUGE, regression-checked against baseline
- [ ] **Eval CI gate** — PR check: F1 must not drop > 5% from baseline
- [ ] **Architecture diagram** — drawn in Excalidraw, embedded in README + ARCHITECTURE.md
- [ ] **README polish** — pitch in 30 seconds, badges, demo screenshot, link to live site
- [ ] **README badges** — build status, coverage %, Vercel deploy status, latest eval F1
- [ ] **ADRs written** — at least the first 4 (pure batch, hexagonal, Supabase, uv)
- [ ] **Architecture deep-dive blog post** — published on dev.to / Medium / Substack
- [ ] **Demo video** — 90-second Loom: cron firing → traces in Langfuse → site updating
- [ ] **GitHub Project board** — public roadmap visible from README
- [ ] **License (MIT) + CONTRIBUTING.md + CODE_OF_CONDUCT.md**
- [ ] **Profile pin** — repo pinned on personal GitHub profile

**Exit criterion (V0 done):** 14 consecutive days of green daily runs; eval F1 sustained ≥ 0.85; one published writeup; pinned on profile.

## V1 — Quality + community polish (~2 months after V0)

Goal: turn the working system into something a small community will use and stars.

### Theme: deeper engineering
- [ ] Extend ground-truth set to 200 papers across all 15 themes
- [ ] Property-based tests for ranking and classification logic
- [ ] Run a **shadow prompt experiment** end-to-end: prompt v2 runs in parallel with v1 for 7 days; eval determines promotion
- [ ] Add **confidence-based human-in-loop hook** — papers below threshold flagged in admin UI (a private Supabase Studio query is enough for V1)
- [ ] Eval drift alerting — chart F1 over time; alert if drift > 5%

### Theme: distribution
- [ ] RSS feed (free, easy, drives subscribers)
- [ ] Email digest via Resend free tier (3000 emails/mo)
- [ ] Daily LinkedIn / Twitter post (manual at first; automate at V1.5)
- [ ] Public Langfuse dashboard link from `/about`

### Theme: site improvements
- [ ] Semantic search (pgvector cosine over `paper_embeddings`)
- [ ] Theme trend charts (D3 or Recharts) — paper count per theme per week
- [ ] Per-author tracking (if author appears 3+ times, dedicated page)
- [ ] Mobile reading UX

### Theme: operational maturity
- [ ] Synthetic monitoring — separate GH Action runs `agent health` every 6h
- [ ] Runbooks for: Supabase pause, eval regression, prompt rollback, cost spike
- [ ] Backup verification — monthly script restores Supabase backup to local DB
- [ ] Disaster recovery doc — what to do if Supabase / Vercel / GH each go down

### Success metrics for V1
- 100+ GitHub stars
- 50+ unique daily visitors organically
- One external mention (blog, newsletter, tweet)
- Eval F1 ≥ 0.90 sustained
- Two blog posts published

## V2 — Traction-dependent expansion (open-ended)

**Only pursue if V1 metrics confirm appetite.**

Possible directions:

| Direction | When to do | Effort |
|---|---|---|
| Custom themes for users | After 200+ subscribers ask | 2-3 weeks |
| Multi-model leaderboard ("Claude vs Gemini classify") | When prompt v3+ stable | 1-2 weeks |
| Active-learning loop (user feedback → re-rank) | After organic traffic established | 2-4 weeks |
| Audio digest (podcast generation) | If text traction high | 2-3 weeks |
| API access for downstream tools | When external dev community asks | 2 weeks |
| Multi-domain (cs.RO, cs.CR, stat.ML) | If existing scope is saturated | 1 week per domain (small) |
| Self-hosted LLM (vLLM on Runpod) | If Groq becomes paid + cost > $50/mo | 1-2 weeks |
| Premium tier / sponsorship | Only after MIT-licensed core stable | indefinite |

## Risk register

| Risk | Likelihood | Impact | Mitigation | Status |
|---|---|---|---|---|
| Solo bus factor | High | Medium | MIT license; documented; ADRs; runbooks | Mitigated by V0 docs |
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
- Personal life shift → MIT license means anyone can pick it up

## V0 weekly checklist (printable)

### Week 1
- [ ] Repo + tooling + signups
- [ ] Domain models + ports
- [ ] First adapter (Groq) + first stage (summarize) working on 5 papers
- [ ] Schema + migration in DB

### Week 2
- [ ] All stages
- [ ] LangGraph orchestration + checkpointing
- [ ] Idempotency + DLQ + rate limits
- [ ] Local end-to-end on ~40 papers

### Week 3
- [ ] Next.js site + Vercel + cron
- [ ] Langfuse + Sentry wired
- [ ] Status page + about page
- [ ] First production daily run

### Week 4
- [ ] Eval harness + ground truth
- [ ] CI gates + ADRs + diagrams
- [ ] Blog post + demo video + profile pin
- [ ] 14-day consecutive green runs (rolls into V1)
