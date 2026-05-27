# Prompt Design + Versioning

## Why prompts are the highest-leverage code

In production AI systems, a single prompt change can swing output quality more than any architectural change. Prompts are **code that ships to production** and must be treated as such:

- Versioned
- Reviewed
- Eval-gated
- Rollback-able
- Attributable (every output knows which prompt produced it)

This doc covers how ArxivDigest handles all of the above.

## Prompts are code, not config

Every prompt lives in `apps/agent/src/agent/core/prompts/` as a Python module:

```
core/prompts/
├── __init__.py
├── relevance/
│   ├── __init__.py        ← exports current active version
│   ├── v1.py
│   ├── v2.py
│   └── v3.py              ← current
├── classify/
│   ├── __init__.py
│   ├── v1.py
│   └── v2.py
├── summarize/
│   ├── __init__.py
│   ├── v1.py
│   ├── v2.py
│   ├── v3.py
│   └── v4.py
└── rank/
    ├── __init__.py
    ├── v1.py
    └── v2.py
```

### Why modules, not text files

- **Python f-strings + functions** = real templating, type-checked, refactorable
- **Imports** = composable (e.g. shared `tone_guidelines.py`)
- **Git diff readable** — reviewer sees prompt changes in plain text
- **mypy** catches missing variables in interpolations
- **No external prompt-template DSL** to learn

### Module shape

```python
# core/prompts/summarize/v3.py
"""Summarization prompt v3 — active since 2026-05-12.

Changes from v2:
- Added explicit "why_it_matters" framing
- Shortened from 1200 to 800 tokens average
- Stronger structure requirement

Rolled back to v2 once (2026-04-15) due to eval regression in keyword coverage;
fixed in v3 by adding examples.
"""
from agent.core.models import Paper

VERSION = "summarize/v3"

SYSTEM = """You are a research-paper summarizer for working AI/ML engineers.
Your job is to produce structured TL;DRs that help readers decide if they
should read the full paper.

Tone: technical but accessible. No marketing language.
Length: ~150-300 tokens total.
"""

USER_TEMPLATE = """Paper title: {title}

Authors: {authors}

Abstract:
{abstract}

Produce a structured summary as JSON with these exact keys:

- problem: What problem is the paper addressing? (1-2 sentences)
- approach: What's the core method? (2-3 sentences)
- result: What did they achieve? (1-2 sentences with concrete numbers if available)
- why_it_matters: Why should an engineer building production AI care? (1-2 sentences)

Be specific. Avoid filler like "this paper proposes" or "extensive experiments show".
"""

def render(paper: Paper) -> dict[str, str]:
    return {
        "system": SYSTEM,
        "user": USER_TEMPLATE.format(
            title=paper.title,
            authors=", ".join(a.name for a in paper.authors),
            abstract=paper.abstract,
        ),
    }
```

### Active version selection

```python
# core/prompts/summarize/__init__.py
from agent.core.prompts.summarize import v3 as _active

VERSION = _active.VERSION
render = _active.render
```

To switch active version, change the `import` line. One-character diff in PR; reviewer sees exactly what changed.

## Pydantic-typed outputs (instructor lib)

Every LLM call has a Pydantic output model. `instructor` automatically retries on schema validation failure with reformulated prompt.

```python
# core/models.py
from pydantic import BaseModel, Field

class Summary(BaseModel):
    problem: str = Field(min_length=20, max_length=400)
    approach: str = Field(min_length=20, max_length=600)
    result: str = Field(min_length=20, max_length=400)
    why_it_matters: str = Field(min_length=20, max_length=400)
```

```python
# pipeline/stages/summarize.py
import instructor
from agent.core.prompts.summarize import render as render_prompt
from agent.core.models import Summary

async def summarize_paper(paper: Paper, llm: LLMClient) -> Summary:
    messages = render_prompt(paper)
    summary = await llm.complete_structured(
        response_model=Summary,
        system=messages["system"],
        user=messages["user"],
        max_retries=3,  # instructor handles re-asking on validation fail
    )
    return summary
```

**What this gives you:**

- LLM output **must** match schema or it's retried
- Type-safe downstream code (`summary.approach` not `summary["approach"]`)
- Validation failure logged to `llm_audit` with `retry_count > 0`
- Forces prompt to be schema-precise (badly-worded prompts fail fast)

This is the single biggest "production-grade AI engineering" signal.

## Prompt versioning in the database

Every paper row tracks which prompt version generated each field:

```sql
papers (
  ...
  summary               jsonb,
  summary_prompt_ver    text,             -- "summarize/v3"
  summary_model         text,             -- "groq/llama-3.3-70b-versatile"
  
  themes                text[],
  classify_prompt_ver   text,
  classify_model        text,
  ...
);
```

**Why this matters:**

- **Backfill** — when prompt changes, find all `papers WHERE summary_prompt_ver != 'summarize/v3'`, re-process them
- **Compare** — "is v3 producing better summaries than v2 on the same papers?" → query and compare
- **Rollback** — keep old summaries available; regenerate from old prompt if needed
- **Attribution** — investigating a bad summary? Check which prompt version generated it

## Prompt design principles

### 1. Structure first, content second

LLMs are vastly better at filling in structured schemas than producing well-organized prose. Lean on this:

```python
# BAD
"Summarize this paper. Make sure to mention the problem, approach, and results."

# GOOD
"Produce JSON with keys: problem, approach, result, why_it_matters. ..."
```

### 2. Constrain length explicitly

LLMs default to verbose. Be specific:

```python
# BAD
"Write a short summary."

# GOOD
"problem: 1-2 sentences (max 80 words)"
```

### 3. Show, don't tell, for style

Few-shot examples beat style instructions:

```python
# BAD
"Use a technical but accessible tone."

# GOOD
"""Examples of the tone we want:

GOOD: "Introduces a 4-bit quantization scheme that recovers 99% of bf16 accuracy 
on Llama 3.3-70B while cutting inference memory 4×."

BAD: "This groundbreaking paper revolutionizes the field of quantization by 
proposing a novel approach that achieves unprecedented results."
"""
```

### 4. Negative examples for known failure modes

If you keep seeing the same bad pattern, include it as an anti-example:

```python
"""Do NOT use phrases like:
- "This paper proposes..."  → just say what it does
- "extensive experiments show..."  → give the numbers
- "achieves SOTA results..."  → name what it beats
"""
```

### 5. Fail loudly for uncertainty

The default LLM behavior is to hallucinate confident answers. Counter explicitly:

```python
"""If the abstract doesn't clearly state the result, set `result` to 
"Not specified in abstract" rather than guessing or paraphrasing the approach."""
```

This maps to one of [DTPL feedback themes](../docs/dtpl-internal-feedback-2026-05-26.md) we've heard in other contexts: "don't infer, flag ambiguity."

### 6. Cheap model for filter, expensive for reasoning

Two-tier prompt design saves cost without quality loss:

| Stage | Cost-tier | Model |
|---|---|---|
| Relevance filter | Cheap | Llama 3.1 8B Instant |
| Classify | Cheap | Llama 3.1 8B Instant |
| Summarize | Expensive | Llama 3.3 70B |
| Rank | Expensive | Llama 3.3 70B |

Cheap-tier prompts are simpler (binary classification, short outputs); they don't need the reasoning capacity of 70B.

## Shadow prompt rollout pattern

When promoting `v3 → v4`, the right pattern is **shadow rollout**:

```
Day 1-7:
  Production uses v3 (active)
  v4 runs in parallel (shadow), writes to papers_shadow table
  Eval harness compares v3 vs v4 outputs

Day 7 review:
  If v4 wins (eval metric improvement > some delta):
    Promote v4 to active
    Mark v3 inactive in prompt_versions table
    Backfill old papers with v4 if regeneration cost is reasonable
  Else:
    Discard v4; document why in ADR
```

### Implementation

`prompt_versions` table tracks which versions are active vs shadow:

```sql
prompt_versions (
  id              uuid pk,
  stage           text not null,
  version         text not null,
  prompt_text     text not null,
  shadow_of       text,                   -- null if active; else version it shadows
  created_at      timestamptz default now(),
  active_from     timestamptz,
  active_until    timestamptz,
  unique (stage, version)
);
```

Pipeline reads active + shadow per stage:

```python
async def summarize_with_shadow(paper, llm, repo):
    active_prompt = await repo.get_active_prompt("summarize")
    shadow_prompt = await repo.get_shadow_prompt("summarize")
    
    summary = await call_llm(paper, active_prompt, llm)
    await repo.save_paper_summary(paper.id, summary, active_prompt.version)
    
    if shadow_prompt:
        try:
            shadow_summary = await call_llm(paper, shadow_prompt, llm)
            await repo.save_shadow_summary(paper.id, shadow_summary, shadow_prompt.version)
        except Exception:
            # Shadow failures don't affect production
            log.warning("shadow_summary_failed", paper_id=paper.id)
    
    return summary
```

### Cost trade-off

Shadow rollout doubles LLM calls for affected stages during the trial. For ArxivDigest:

- 40 papers × 1 extra summarize call = 40 extra LLM calls/day
- Within free tier easily
- Spend a week's free-tier quota on a 7-day shadow → worth it for prompt confidence

## Theme taxonomy management

Themes are not free-form LLM output — they're picked from a **curated, versioned taxonomy**:

```python
# core/themes.py
THEMES = {
    "agents": "Agentic systems, tool use, multi-step reasoning",
    "retrieval": "RAG, embeddings, vector search, hybrid retrieval",
    "efficiency": "Quantization, distillation, pruning, inference speedups",
    "multimodal": "Vision-language, audio, video-text models",
    "alignment": "RLHF, constitutional AI, safety, jailbreak defenses",
    "evaluation": "Benchmarks, eval methodology, LLM-as-judge",
    "fine_tuning": "LoRA, instruction tuning, PEFT methods",
    "reasoning": "Chain-of-thought, planning, mathematical reasoning",
    "code": "Code generation, code understanding, programming benchmarks",
    "datasets": "New datasets, data curation, synthetic data",
    "architecture": "New model architectures, attention variants, MoE",
    "scaling": "Scaling laws, training dynamics, optimization",
    "robotics": "Embodied AI, robotic policies (where overlap with LLMs)",
    "interpretability": "Mech interp, probing, circuit analysis",
    "applications": "Domain-specific deployments (medical, legal, scientific)",
}
```

Themes evolve quarterly. When changing:
1. Document in `docs/adr/00NN-theme-taxonomy-vN.md`
2. Backfill old papers with new classifier if needed
3. Site themes-list updates from this source of truth

## Prompt review checklist (for self-review on PRs)

Before merging a prompt change, verify:

- [ ] Has a clear `VERSION` constant
- [ ] Docstring explains what changed vs previous version
- [ ] Pydantic output model matches expected schema
- [ ] Eval harness ran locally; F1 didn't regress
- [ ] At least 3 ground-truth papers eyeballed manually
- [ ] Anti-patterns from prior versions explicitly addressed
- [ ] Token budget estimated (don't blow cost ceiling)
- [ ] Active version pointer in `__init__.py` updated

## Anti-patterns to avoid

| Anti-pattern | Why bad |
|---|---|
| Edit prompt text inline in `pipeline/` code | No versioning; no rollback; not reviewable |
| Use string interpolation with untyped variables | Typos at runtime; no IDE help |
| Skip output validation | LLM eventually returns garbage; downstream crashes |
| Prompt that asks LLM to "be creative" | Non-determinism + low eval scores |
| Long prompts (> 2000 tokens) | Cost + latency + dilutes instruction |
| Mixing instruction + data without delimiters | Prompt injection risk; LLM confused |
| No examples in prompt | Worse output quality; LLM drift over time |
| Generating prompts dynamically from user input | Injection risk; not versioned |

## Future: prompt experimentation (V1)

Things to add when V0 is shipped:

- **A/B testing matrix** — multiple shadow prompts at once, evaluated against same ground truth
- **Automated regression alerting** — if any eval metric drops > 2σ from rolling mean, alert
- **Constitutional self-critique** — critic agent reviews summary, can request revision (multi-agent dialogue)
- **Public prompt-changelog page** on `/about` — visible audit of every prompt promotion + why
- **Prompt impact attribution** — tag every site-visitor-reported issue with `prompt_version` that generated it

## What this signals on a resume

| Practice | Senior signal |
|---|---|
| Prompts as versioned code | "I treat AI quality as a software concern" |
| Pydantic + instructor for outputs | "Type-safe LLM contracts" |
| Per-call prompt + model attribution in DB | "Reproducibility for AI" |
| Shadow rollout pattern | "I deploy prompts with the same rigor as code" |
| Eval-gated promotion | "I prevent AI regressions in CI" |
| Two-tier model design (cheap filter, expensive reason) | "Cost-aware AI engineering" |
| Anti-pattern documentation | "I learn from failure modes systematically" |

## Cross-references

- [ARCHITECTURE.md](./ARCHITECTURE.md) — where prompts run
- [TESTING.md](./TESTING.md) — how prompts get eval-gated
- [OBSERVABILITY.md](./OBSERVABILITY.md) — how prompt versions are traced
- [adr/](./adr/) — ADRs covering taxonomy changes, major prompt rewrites
