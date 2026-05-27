# ADR-0005 — Vercel over Cloudflare Pages for the Next.js site

**Status:** Accepted
**Date:** 2026-05-26
**Decider:** Imtiaj

## Context

The site is a Next.js 15 application (App Router) with mostly static content and a few SSR/ISR routes. It needs:

- Auto-deploy from a GitHub repo
- Free tier sufficient for a portfolio project
- Good Next.js feature support
- Edge CDN for global users
- Simple monorepo handling (deploy `apps/web` from a Turborepo)

Two strong contenders: Vercel and Cloudflare Pages. Both have generous free tiers, both auto-deploy from git, both have global CDNs.

## Decision

**Use Vercel Hobby tier.**

## Alternatives considered

### A. Cloudflare Pages

**Strengths:**
- Unlimited bandwidth (vs Vercel's 100GB/mo cap)
- Cheaper "next paid tier" than Vercel
- Same vendor if we use Cloudflare for DNS / Workers / R2
- Faster cold starts in some regions

**Rejected because:**
- **Lags Vercel in Next.js feature support** — particularly App Router features land on Vercel first
- **ISR support is limited** — Cloudflare's incremental static regeneration is workable but requires more config
- **Less mature monorepo detection** — Vercel auto-detects `apps/web` in a Turborepo cleanly; Cloudflare requires manual build config
- **OG image generation is harder** — Vercel has a first-class `@vercel/og` library; Cloudflare needs more work
- **Server actions + middleware** have parity gaps with Vercel

For a project that lives or dies by how the Next.js site presents (resume artifact), choosing the platform that ships Next.js features first matters.

### B. Netlify

**Strengths:**
- Long-standing platform
- Free tier is generous
- Good DX

**Rejected because:**
- Less Next.js-native than Vercel (Netlify retrofitted Next support; Vercel built Next.js)
- Free tier bandwidth (100GB/mo) is same as Vercel
- No clear advantage to justify divergence from the path-of-least-resistance

### C. Self-host on Fly.io / Railway / Render

**Rejected because:**
- More ops overhead
- Slower deploys
- No free tier as comfortable as Vercel for Next.js

### D. GitHub Pages (static only)

**Rejected because:**
- No SSR/ISR — can't render today's digest dynamically
- Limited to static; would need to write a static-export pipeline
- Worse DX than Vercel auto-deploy

## Consequences

### Positive

- **Best Next.js DX** — push to main, deploy in 1-2min, preview URL per PR
- **Auto-monorepo detection** — Vercel sees the Turborepo, picks `apps/web` automatically
- **Native ISR + Server Actions** — no config gymnastics
- **First-class OG image generation** via `@vercel/og`
- **Per-PR preview deploys** — every PR gets a unique URL for review
- **Generous free tier** — 100GB bandwidth, 100GB-hours of function execution

### Negative / accepted trade-offs

- **Vercel Hobby ToS technically says "non-commercial"** — for a portfolio project this is fine; Vercel doesn't enforce against clearly non-commercial use. If ArxivDigest ever monetises, upgrade to Pro ($20/mo).
- **100GB bandwidth cap** — current expectation is <5GB/mo; 20× headroom. If we cross 80GB, the migration to Cloudflare is straightforward (same Next.js code; different hosting config).
- **Vendor lock-in to Vercel-specific features** (e.g. `@vercel/og`, Server Components specifics) — mitigated by sticking to App Router primitives that work elsewhere

### When to revisit

- Bandwidth > 80GB/mo for 2 consecutive months → migrate to Cloudflare Pages (cheaper continued growth) or upgrade Vercel Pro
- Vercel sunsets Hobby tier or restricts non-commercial scope → migrate
- ArxivDigest becomes a real commercial product → upgrade to Pro ($20/mo) regardless
- Need true edge-rendered worldwide multi-region writes → neither helps; reconsider architecture

## Comparison summary

| Criterion | Vercel | Cloudflare Pages |
|---|---|---|
| Next.js feature parity | **Best** (Vercel built Next) | Lagging |
| Free tier bandwidth | 100GB/mo | Unlimited |
| Free tier function execution | 100GB-hr/mo | 100K req/day (Workers) |
| Monorepo auto-detection | Excellent | Manual config |
| Per-PR preview deploys | Native | Native |
| ISR support | First-class | Workable, more config |
| OG image generation | First-class (`@vercel/og`) | Manual |
| Server Actions | First-class | Limited support |
| Domain + DNS | Self-managed (Cloudflare Registrar works fine) | Native (if using CF DNS) |
| Migration cost if we leave | Low (Next.js portable) | Low |

## References

- [Vercel free tier limits](https://vercel.com/pricing)
- [Cloudflare Pages free tier limits](https://pages.cloudflare.com/)
- [STACK.md](../STACK.md)
