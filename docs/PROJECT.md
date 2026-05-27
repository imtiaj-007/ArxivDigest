# Project Overview

## What ArxivDigest is

A **daily autonomous AI agent** that processes new arxiv research submissions, structures them into a navigable archive, and publishes a curated digest. It runs unattended on free cloud tiers, with full LLM trace observability and an eval harness gating quality.

## Why it exists

### The problem

Anyone trying to keep up with AI/ML research faces three issues:

1. **Signal-to-noise** — arxiv `cs.AI / cs.LG / cs.CL` produce **100-150 new papers per weekday**. Most are incremental; a handful are genuinely impactful. Manual triage is impractical.
2. **No structured comparison** — existing summarizers (PapersWithCode, alphaXiv, Hugging Face daily papers) provide titles + abstracts but rarely structured comparison across novelty / approach / impact dimensions.
3. **No memory** — most digests are list-shaped, with no theme-level browsing, no historical anchoring ("this is a refinement of last month's X"), no per-author or per-theme trend lines.

### The opportunity

The combination of (a) free, fast inference (Groq Llama 3.3 70B), (b) cheap structured storage (Supabase Postgres + pgvector), and (c) free deployment (Vercel + GitHub Actions) means a single engineer can ship a production-grade daily digest that **didn't exist 18 months ago**.

This project demonstrates that capability as a portfolio piece.

## Goals

### Primary (V0 must achieve)

1. **Autonomous daily operation** — runs unattended at 06:00 UTC; no manual intervention required for normal operation
2. **Structured paper representation** — every processed paper has: title, authors, arxiv link, abstract, structured summary, theme assignment(s), novelty score, impact score, confidence, model + prompt version that generated each field
3. **Browsable public archive** — chronological, theme-based, and search-based access
4. **Quality gating** — eval harness on 50 hand-labeled papers; classification F1 ≥ 0.85 sustained, regression-gated in CI
5. **Full observability** — every LLM call traced (Langfuse), every error captured (Sentry), structured logs
6. **$0 monthly cost** — entirely on free tiers; domain (~₹1000/year) is the only paid item

### Secondary (V1+)

7. Email subscriber digest (Resend free tier)
8. Theme-level trend visualisations
9. Author tracking ("show me everything from this author this month")
10. Cross-paper citation chains
11. Public Langfuse dashboard link
12. Active learning loop for low-confidence outputs

### Tertiary (V2+, only if traction warrants)

13. User-supplied custom themes / RSS feeds
14. API access for downstream tools
15. Multi-model leaderboard ("how would Claude vs Gemini classify this paper?")
16. Companion blog / Substack distribution

## Non-goals

Things ArxivDigest will explicitly **not** do:

- ❌ Replace reading the actual papers — summaries are filters, not substitutes
- ❌ Make accept/reject decisions — only rank + classify; humans decide what to read
- ❌ Cover non-AI subjects (cs.RO, cs.CR, etc.) — focused scope by design
- ❌ Real-time streaming — daily is the right cadence; real-time adds operational burden without proportionate value
- ❌ Become a SaaS product — portfolio + open-source artifact only; if it grows, that's bonus
- ❌ Compete with PapersWithCode / Hugging Face papers — different positioning (deeper structure, fewer papers)

## Success criteria

### V0 (3-4 weeks of evening work)

- [ ] Agent runs daily for 14 consecutive days without manual intervention
- [ ] Eval harness reports classification F1 ≥ 0.85 on the ground-truth set
- [ ] Site loads in < 1s globally (Vercel edge)
- [ ] Architecture diagram + README pitch get **interview-quality polish**
- [ ] One technical blog post / writeup published

### V1 (post-V0, ~2 months)

- [ ] 100+ GitHub stars
- [ ] 50+ unique daily visitors organically
- [ ] Eval harness extended to 200 papers across 15 themes
- [ ] Prompt v2 shipped via shadow rollout pattern (V1 vs V2 ran in parallel for 7 days; V2 promoted on better eval)

### V2 (only if V1 traction confirms appetite)

- [ ] 500+ stars
- [ ] Email digest active with 100+ subscribers
- [ ] Cited in a research community newsletter or blog post
- [ ] Becomes the default "how do I keep up with arxiv?" recommendation in at least one community

## Target audience

1. **Primary — me** (the author): genuinely useful as a daily research digest; eating own dog food validates quality
2. **Secondary — AI/ML engineers and researchers** in industry: small community, but high engagement potential; will star, fork, share if useful
3. **Tertiary — recruiters / hiring managers** for AI/ML roles: portfolio review audience; this audience cares about engineering signal more than utility
4. **Quaternary — students entering AI/ML**: structured introduction to current research themes

## Constraints

| Constraint | Value | Driver |
|---|---|---|
| Total monthly cost | $0 (excluding optional domain) | Personal project budget |
| Engineer effort | ~3-4 weeks for V0, then ~2-4 hrs/week for maintenance | Side project alongside day job |
| Operating regions | Global (CDN-served site, agent runs in US-East GH Actions) | No regulatory requirement |
| Languages | English content only initially | Scope discipline |
| Code license | MIT | Permissive open source |
| Data license | Respects arxiv ToS — links to original paper, summaries are derivative work | Compliance |
| Compute environment | GitHub Actions runner (Ubuntu, 4 CPU, 16GB RAM, ~30 min budget per run) | Free tier |

## Risks + mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Groq free tier rate-limit tightened | Medium | High | Gemini failover + Cerebras backup; cost-capped paid tier ready |
| Supabase free project paused after dormancy | Low (daily cron pings it) | Medium | Heartbeat run every 6h triggers DB |
| GH Actions free tier reduced | Low | Medium | Move cron to Cloudflare Workers Cron (also free) |
| arxiv API changes / blocks scrapers | Low | Critical | Use official arxiv API (rate-respecting); maintain User-Agent identification |
| Prompt regression breaks output quality | Medium | High | Eval CI gate; rollback via prompt versioning |
| Hosting costs grow if it becomes popular | Low (free tiers generous) | Medium | Cost ceiling enforced in code; alert at 80% of any free tier |
| Single-engineer bus factor | High | Medium | Open source, MIT-licensed, documented for handoff |

## Out of scope for V0 (deferred)

These are valuable but explicitly deferred — see [PLANNING.md](./PLANNING.md) for sequencing:

- Email subscriber list + delivery infrastructure
- Multi-model A/B testing
- User accounts + personalised digests
- Citation graph visualisation
- Mobile-optimised reading experience (beyond responsive web)
- Translation to non-English languages
- Audio digest (podcast generation)

## Reference

- [ARCHITECTURE.md](./ARCHITECTURE.md) — how it's built
- [PLANNING.md](./PLANNING.md) — when it's built
- [STACK.md](./STACK.md) — what it's built with
- [adr/](./adr/) — why specific decisions were made
