# Architecture Decision Records (ADRs)

> Lightweight documentation of significant technical decisions, why they were made, and what alternatives were considered.

## Why ADRs

Reading code tells you **what** the system does. ADRs tell you **why** it's that way and what was rejected. Six months from now (or to a new contributor), this saves hours of "why didn't we just..." conversations.

## Format

We use a lightweight variant of the [Michael Nygard format](https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions.html):

- **Status** — Proposed / Accepted / Superseded by ADR-NNNN / Deprecated
- **Context** — What's the situation that calls for a decision?
- **Decision** — What did we choose?
- **Alternatives** — What else did we consider, and why not?
- **Consequences** — What follows from this decision? (good + bad)

## Index

| # | Title | Status |
|---|---|---|
| [0001](./0001-pure-batch-architecture.md) | Pure Python batch agent, no FastAPI | Accepted |
| [0002](./0002-supabase-over-cloudflare-d1.md) | Supabase Postgres over Cloudflare D1 | Accepted |
| [0003](./0003-uv-over-poetry.md) | `uv` over Poetry for Python dependency management | Accepted |
| [0004](./0004-hexagonal-architecture.md) | Hexagonal (ports + adapters) architecture for the agent | Accepted |
| [0005](./0005-vercel-over-cloudflare-pages.md) | Vercel over Cloudflare Pages for the Next.js site | Accepted |

## When to write an ADR

Write one when the decision:

- Locks in a constraint that affects multiple components
- Picks between non-obvious alternatives
- Will be questioned later ("why didn't we just use X?")
- Affects how new contributors should think about the system

Skip ADRs for:
- Decisions reversible in < 1 day (e.g. variable naming)
- Standard practices that aren't controversial (e.g. "we use `pytest`")
- Decisions that affect a single file

## Template

```markdown
# ADR-NNNN — Short Title

**Status:** Proposed | Accepted | Superseded by ADR-NNNN | Deprecated
**Date:** YYYY-MM-DD
**Decider:** Imtiaj

## Context

What's the situation? What forces are at play?

## Decision

What did we choose, in one sentence?

Then expand on what the decision means concretely.

## Alternatives considered

- **Option A** — Why not?
- **Option B** — Why not?

## Consequences

Positive:
- ...

Negative / accepted trade-offs:
- ...

## References

- Related: ADR-NNNN
- Inspired by: <link>
```
