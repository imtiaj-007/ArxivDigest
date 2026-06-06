# Contributing to ArxivDigest

Thanks for the interest. ArxivDigest is a personal portfolio project that
also happens to be open source — drive-by patches, bug reports, and
forks are all welcome.

## License + attribution

ArxivDigest is [Apache License 2.0](./LICENSE). Two things follow from that:

1. **Inbound = outbound.** By opening a pull request you agree that your
   contribution is licensed under the same terms.
2. **Attribution stays with the code.** The repo ships a [NOTICE](./NOTICE)
   file; if you fork, copy substantial parts, or build a derivative work,
   you must retain that notice and credit the original project at
   `https://github.com/imtiaj-007/ArxivDigest`. Acceptable forms:
   - Link in your README or top-level documentation
   - A line in an "Acknowledgements" / "Built upon" section
   - Retention of the original copyright headers where present

   Removing the NOTICE, stripping attribution from documentation, or
   presenting derivative work as wholly original are violations of the
   License terms and not authorized.

## What's in scope

- Bug fixes (especially in the agent pipeline, eval harness, CI workflows)
- Documentation improvements (typos, clarifications, ADR follow-ups)
- New ADRs proposing significant architectural changes — discuss in an
  issue first
- Small UX improvements to the docs site (`apps/web`)

## What's out of scope (for now)

- Net-new features in the agent without prior discussion
- Wholesale rewrites of existing modules
- Renaming, restructuring, or "modernizing" working code without a
  concrete bug or quality issue
- Vendor / SDK / framework swaps (LangGraph → X, Groq → Y, etc.) —
  these are ADR-territory; open an issue

## Workflow

1. **Fork the repo** and clone your fork locally.
2. **Branch off `main`.** Naming convention: `fix/<short>`,
   `feat/<short>`, `docs/<short>`, `ops/<short>`.
3. **Make the change.** Run the local checks (see below) before pushing.
4. **Open a PR against `main`.** Reference the issue if one exists.
   PR description should answer: what changed, why, what was tested.

## Local checks

This repo is a Turborepo + pnpm + uv monorepo. Each app has its own
toolchain.

### `apps/agent` (Python)

```sh
cd apps/agent
uv sync
uv run pytest tests/unit/ -q       # unit tests
uv run ruff check src tests        # lint
uv run mypy src tests              # type check (strict)
```

Integration tests need a real Postgres; set `TEST_DATABASE_URL` and run
`uv run pytest tests/integration/ -q`.

### `apps/web` (Next.js)

```sh
cd apps/web
pnpm install
pnpm build         # production build (catches type errors)
pnpm dev           # local dev server on :3000
```

### Pre-commit

```sh
uv tool install pre-commit
pre-commit install
```

Hooks run `ruff` + `mypy` on staged Python files.

## Code style

- **Python:** ruff-formatted, mypy-strict, structured logging via
  `structlog`. No bare `except`. Async first.
- **TypeScript:** strict mode, no `any`, prefer named exports. UI text
  in en-US, sentence-case (not Title Case) for headings.
- **Comments:** explain *why*, not *what*. The well-named identifier
  documents the what.
- **Tests:** unit tests in `tests/unit/`, integration in
  `tests/integration/`. Mock at adapter boundaries, not domain code.

## Reporting bugs

Open an issue with:

- What you did
- What you expected
- What actually happened (logs, screenshots if visual)
- Environment (OS, Node version, Python version)

If it's a security issue, **don't open a public issue** — email the
maintainer instead (see profile).

## Asking questions

Open a GitHub Discussion or comment on a relevant issue / ADR. For
"how does X work" questions, check the [docs site](https://arxiv-digest-preview.vercel.app/docs)
first — most architectural decisions are spelled out in
[ADRs](https://arxiv-digest-preview.vercel.app/docs/adr).
