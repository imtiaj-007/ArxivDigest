# ADR-0003 — `uv` over Poetry for Python dependency management

**Status:** Accepted
**Date:** 2026-05-26
**Decider:** Imtiaj

## Context

The Python agent needs a package manager. The historical leaders are pip, Poetry, and PDM. In 2024-25, Astral (the team behind `ruff`) released `uv` — a single Rust binary that replaces pip, venv, virtualenv, pyenv, poetry, and pip-tools. By mid-2026 it has become the de-facto modern choice in the AI/ML Python community (vLLM, Anthropic SDKs, Hugging Face Spaces, etc. all moved to `uv`).

## Decision

**Use `uv` for all Python dependency management.**

- `pyproject.toml` for declared deps
- `uv.lock` for locked versions (committed)
- `uv sync` for install
- `uv run <cmd>` for invocation in correct venv
- `uv tool install` for global CLI tools (ruff, mypy)

## Alternatives considered

### A. Poetry

**Strengths:**
- Mature, widely understood
- Strong lockfile semantics
- Built-in publishing workflow

**Rejected because:**
- **10-100× slower** than `uv` for installs and lock resolution — `uv sync` runs in ~1 second; Poetry can take 30-90s
- Lock file resolution sometimes hangs or produces inconsistent results across machines
- Slow CI (a 30s overhead per CI run × hundreds of runs/month adds up to a meaningful waste)
- The Python tooling community has clearly moved on; Poetry reads as 2022-era in 2026
- Resume signal: `uv` shows currency with the ecosystem

### B. pip + pip-tools + virtualenv

**Strengths:**
- Standard library + minimal extras
- Universally understood

**Rejected because:**
- Multiple tools to coordinate (pip-compile, pip-sync, virtualenv)
- No single source of truth for environments
- Manual venv activation in CI is annoying
- No `uv tool`-style global CLI install

### C. PDM

**Strengths:**
- PEP 582 support
- Faster than Poetry
- Cleaner CLI

**Rejected because:**
- Smaller community than `uv`
- No clear advantage over `uv` for our use case
- `uv` is winning the mindshare race; less risk of bit-rot

### D. conda / mamba

**Rejected because:**
- Heavy; designed for binary scientific packages we don't use
- Slower than `uv`
- Mixing pip and conda environments is fragile

## Consequences

### Positive

- **Fast CI** — `uv sync --frozen` takes ~2s. CI runs feel snappy.
- **Single tool** — no separate venv, pip-tools, pyenv. Everything in one binary.
- **Cross-platform identical** — same Rust binary on macOS / Linux / Windows; no "works on my machine" gaps.
- **`uv tool install`** — global CLI tools (ruff, mypy, pre-commit) cleanly isolated.
- **Resume signal** — using current tools = "stays current" indicator.

### Negative / accepted trade-offs

- **Newer tool, less mature** — `uv` is post-1.0 but has only ~18 months of production use. Lower than Poetry's track record.
  - **Mitigation:** Astral team is funded and active; if `uv` somehow disappeared, migration back to Poetry is straightforward (`pyproject.toml` format is compatible).
- **Smaller community** for troubleshooting (vs Poetry's huge Stack Overflow corpus)
  - **Mitigation:** active GitHub issues; problems get fixed fast
- **Less ecosystem integration** in some tools (some Docker images, some legacy tutorials)
  - **Mitigation:** `uv` works fine in standard Python Docker images

### When to revisit

- If Astral discontinues `uv` development → migrate to Poetry (low effort)
- If a project policy mandates Poetry (unlikely for personal project)
- If we need a Python feature `uv` doesn't yet support (none currently identified)

## Migration path back to Poetry (if ever needed)

```bash
# pyproject.toml is mostly compatible already
poetry init  # re-initialise from the existing pyproject.toml
poetry lock  # regenerate Poetry-format lock file
rm uv.lock
```

Effort: a few hours. Risk: low.

## References

- [`uv` documentation](https://docs.astral.sh/uv/)
- [STACK.md](../STACK.md)
- Astral team — same team that built `ruff` (now Python's default linter)
