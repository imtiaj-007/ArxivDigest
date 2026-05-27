# ADR-0004 — Hexagonal (Ports + Adapters) Architecture for the Agent

**Status:** Accepted
**Date:** 2026-05-26
**Decider:** Imtiaj

## Context

The agent integrates with many external services (Groq, Gemini, Voyage, Supabase, arxiv API, Langfuse, Sentry) and runs pipeline logic over them. The naive approach — call SDKs directly from pipeline functions — works for V0 but causes problems as the system grows:

- Hard to test pipeline logic without real network calls
- Vendor swaps (e.g. "switch from Groq to OpenAI for one experiment") require touching many files
- Difficult to add cross-cutting behavior (caching, retries, metrics) without code duplication
- Mixing business logic with infrastructure concerns makes both harder to reason about

Hexagonal architecture (Alistair Cockburn, also called "ports + adapters") separates these concerns explicitly. It's a slightly heavier upfront pattern, but pays off for any system intended to outlive its initial implementation.

## Decision

**Adopt hexagonal architecture for the agent.**

Three layers, with strict direction-of-dependency:

```
   ┌──────────────────────────────────────┐
   │   adapters/  (depends on ports)      │   ← Groq, Gemini, Supabase, arxiv
   └──────────────┬───────────────────────┘
                  │
                  ▼
   ┌──────────────────────────────────────┐
   │   ports/  (Protocol interfaces)      │   ← LLMClient, Embedder, Repository
   └──────────────┬───────────────────────┘
                  │
                  ▼
   ┌──────────────────────────────────────┐
   │   core/  (pure domain logic)         │   ← ranking, classification, prompts
   │   (no I/O, no network, no DB)        │
   └──────────────────────────────────────┘

   pipeline/  ← orchestrates over ports (depends down through the stack)
```

**Direction of dependency:** outer layers may depend on inner; inner must NOT depend on outer. `core/` knows nothing about HTTP clients or DB sessions.

## Alternatives considered

### A. Flat module structure (everything in one place)

Standard Python script style: `agent/main.py` calls `groq.client.complete(...)` directly.

**Rejected because:**
- Pipeline functions become hard to unit-test (need to mock SDK internals)
- Adding cross-cutting concerns (caching, retries, audit logging) means touching every call site
- Vendor swap is a search-and-replace exercise; high risk of subtle bugs

### B. Service classes without explicit ports

OOP-style: `LLMService` class with `groq_client` as constructor arg. Pipeline uses `self.llm_service.complete()`.

**Strengths:** mostly good; dependency injection works.

**Rejected because:**
- No formal interface contract — easy to accidentally couple to specific implementation details (e.g. assume Groq-specific error types)
- Doesn't naturally support multiple implementations (e.g. `MultiLLMAdapter` for failover)
- Doesn't make the "outer depends on inner" direction explicit

### C. Domain-driven design (full DDD with aggregates, entities, repositories)

**Rejected because:**
- Massively over-engineered for a daily batch pipeline
- DDD shines for transactional business systems; we're a read-mostly content generator
- Vocabulary mismatch (no "domain experts" except me)

## Implementation

### `ports/` — Protocol interfaces

```python
# ports/llm.py
from typing import Protocol
from pydantic import BaseModel

class LLMResponse(BaseModel):
    text: str
    prompt_tokens: int
    completion_tokens: int
    model: str
    provider: str
    cost_usd_estimate: float
    cached: bool = False

class LLMClient(Protocol):
    async def complete(
        self,
        system: str,
        user: str,
        *,
        stage: str,
        prompt_version: str,
        max_tokens: int = 1024,
    ) -> LLMResponse: ...
    
    async def complete_structured[T: BaseModel](
        self,
        response_model: type[T],
        system: str,
        user: str,
        *,
        stage: str,
        prompt_version: str,
        max_retries: int = 3,
    ) -> T: ...
```

### `adapters/` — concrete implementations

```python
# adapters/llm/groq.py
class GroqAdapter:
    """Implements LLMClient port via Groq API."""
    
    def __init__(self, api_key: SecretStr, model: str) -> None:
        self._client = groq.AsyncGroq(api_key=api_key.get_secret_value())
        self._model = model
    
    async def complete(self, system, user, *, stage, prompt_version, max_tokens=1024) -> LLMResponse:
        # implementation
        ...

# adapters/llm/multi.py
class MultiLLMAdapter:
    """Implements LLMClient port with failover across multiple providers."""
    
    def __init__(self, primary: LLMClient, fallback: LLMClient) -> None:
        self._primary = primary
        self._fallback = fallback
    
    async def complete(self, *args, **kwargs) -> LLMResponse:
        try:
            return await self._primary.complete(*args, **kwargs)
        except (RateLimitError, ProviderDownError):
            return await self._fallback.complete(*args, **kwargs)

# adapters/llm/instrumented.py
class InstrumentedLLM:
    """Adds Langfuse tracing to any LLMClient."""
    
    def __init__(self, inner: LLMClient, langfuse: Langfuse) -> None:
        ...
```

### `core/` — pure logic

```python
# core/ranking.py
def score_novelty(similarities: list[float]) -> float:
    """Pure function: similarities to recent papers → novelty score 0-1."""
    if not similarities:
        return 1.0
    return 1.0 - max(similarities)
```

No I/O. No imports from `adapters/`. No imports from `pipeline/`. Easy to unit-test.

### `pipeline/` — orchestration

```python
# pipeline/stages/summarize.py
async def summarize_paper(
    paper: Paper,
    llm: LLMClient,                   # ← port, not Groq directly
    repo: Repository,                  # ← port
) -> Summary:
    summary = await llm.complete_structured(
        response_model=Summary,
        system=prompts.summarize.SYSTEM,
        user=prompts.summarize.render(paper),
        stage="summarize",
        prompt_version=prompts.summarize.VERSION,
    )
    await repo.save_summary(paper.id, summary)
    return summary
```

### Composition root

```python
# agent/main.py (or cli.py)
def build_orchestrator(settings: Settings) -> Orchestrator:
    """Single place where adapters are wired to ports."""
    
    groq_llm = GroqAdapter(settings.groq_api_key, model="llama-3.3-70b")
    gemini_llm = GeminiAdapter(settings.gemini_api_key)
    multi_llm = MultiLLMAdapter(primary=groq_llm, fallback=gemini_llm)
    instrumented_llm = InstrumentedLLM(multi_llm, settings.langfuse_client)
    
    embedder = VoyageEmbedder(settings.voyage_api_key)
    repo = SupabaseRepository(settings.supabase_url, settings.supabase_service_key)
    source = ArxivSource()
    
    return Orchestrator(llm=instrumented_llm, embedder=embedder, repo=repo, source=source)
```

## Consequences

### Positive

- **Pipeline logic is easily testable** — pass mock adapters that implement the ports
- **Vendor swap is one line** — change a single import + binding in the composition root
- **Cross-cutting concerns compose cleanly** — `InstrumentedLLM` wraps any `LLMClient`; same pattern for caching, retries, metrics
- **Future FastAPI layer is non-breaking** — add a new "driver" (HTTP) that calls the same pipeline functions
- **Reads as senior** — interviewers see the structure and recognise it; opens better conversations
- **"How would you swap Groq for Anthropic?"** — answer: write `AnthropicAdapter` implementing `LLMClient`, change one line in composition root. Test demonstrates this works.

### Negative / accepted trade-offs

- **More files, more directories** — V0 has ~20 files where a flat structure might have 5. Cost is small for the discipline it enforces.
- **Some boilerplate** — each new external service requires defining a port + adapter, even if there's only one implementation
- **Slight indirection** — reading code requires understanding "this is calling through a port"; minor cognitive overhead
- **Easy to over-apply** — must resist temptation to put everything behind a port; `core/` should be small (~30% of code), `adapters/` larger

### When to revisit

- If `core/` ends up empty (everything is adapter glue) → architecture isn't paying off; revisit
- If we ship V1+ and adapters never change → the abstraction may be unnecessary; can flatten safely

## References

- [Original "Hexagonal Architecture" by Alistair Cockburn](https://alistair.cockburn.us/hexagonal-architecture/)
- [Ports and Adapters in Python (Robert Cooper / Bob Gregory)](https://www.cosmicpython.com/)
- Related: [ADR-0001 (batch architecture)](./0001-pure-batch-architecture.md) — hexagonal makes future HTTP layer non-breaking
- [ARCHITECTURE.md](../ARCHITECTURE.md#architecture-pattern--hexagonal-ports--adapters)
- [TESTING.md](../TESTING.md) — how this architecture enables testing
