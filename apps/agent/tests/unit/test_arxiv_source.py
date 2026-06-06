"""ArxivSource retry + graceful-degradation behavior, verified without network.

Covers 429 (rate limit) AND 5xx (server unavailable / gateway errors) — both
are arxiv-side transients we recover from. Non-transient responses (4xx that
isn't 429) propagate as ``HTTPStatusError`` so they surface in Sentry.
"""

from __future__ import annotations

from collections.abc import Callable

import httpx
import pytest

from arxivdigest.adapters.arxiv.source import (
    _MAX_ATTEMPTS,
    ARXIV_API_URL,
    ArxivRateLimitedError,
    ArxivSource,
    ArxivUnavailableError,
)

_EMPTY_ATOM_FEED = (
    '<?xml version="1.0" encoding="UTF-8"?>'
    '<feed xmlns="http://www.w3.org/2005/Atom"></feed>'
)


Handler = Callable[[httpx.Request], httpx.Response]


def _client_with_handler(handler: Handler) -> httpx.AsyncClient:
    """Wrap a handler in an httpx AsyncClient with a MockTransport."""
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


@pytest.mark.asyncio
async def test_fetch_recent_returns_empty_on_persistent_429(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A sustained arxiv 429 must not fail the run — return [] and log."""
    monkeypatch.setattr("arxivdigest.adapters.arxiv.source.asyncio.sleep", _noop_sleep)
    calls = 0

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(429, text="rate-limited")

    async with _client_with_handler(handler) as client:
        source = ArxivSource(client)
        papers = await source.fetch_recent(["cs.AI"], limit=10)

    assert papers == []
    assert calls == _MAX_ATTEMPTS  # bounded retry budget, not infinite


@pytest.mark.asyncio
async def test_fetch_recent_returns_empty_on_persistent_503(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """503 is the canonical 'arxiv is down right now' — bulkhead it like 429.

    Regression test for 2026-06-06 incident: a local run died on a 503
    that escaped the retry loop and surfaced as run.failed.
    """
    monkeypatch.setattr("arxivdigest.adapters.arxiv.source.asyncio.sleep", _noop_sleep)
    calls = 0

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(503, text="service unavailable")

    async with _client_with_handler(handler) as client:
        source = ArxivSource(client)
        papers = await source.fetch_recent(["cs.AI"], limit=10)

    assert papers == []
    assert calls == _MAX_ATTEMPTS


@pytest.mark.asyncio
async def test_fetch_recent_recovers_after_transient_429(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A 429 followed by a 200 must succeed — empty feed → empty paper list."""
    monkeypatch.setattr("arxivdigest.adapters.arxiv.source.asyncio.sleep", _noop_sleep)
    statuses: list[int] = [429, 429, 200]
    calls = 0

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        status = statuses[calls]
        calls += 1
        body = _EMPTY_ATOM_FEED if status == 200 else "rate-limited"
        return httpx.Response(status, text=body)

    async with _client_with_handler(handler) as client:
        source = ArxivSource(client)
        papers = await source.fetch_recent(["cs.AI"], limit=10)

    assert papers == []
    assert calls == 3  # 2 retries then success


@pytest.mark.asyncio
@pytest.mark.parametrize("transient_status", [500, 502, 503, 504])
async def test_fetch_recent_recovers_after_transient_5xx(
    monkeypatch: pytest.MonkeyPatch, transient_status: int
) -> None:
    """5xx followed by 200 must succeed — covers 500/502/503/504."""
    monkeypatch.setattr("arxivdigest.adapters.arxiv.source.asyncio.sleep", _noop_sleep)
    statuses: list[int] = [transient_status, 200]
    calls = 0

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        status = statuses[calls]
        calls += 1
        body = _EMPTY_ATOM_FEED if status == 200 else "unavailable"
        return httpx.Response(status, text=body)

    async with _client_with_handler(handler) as client:
        source = ArxivSource(client)
        papers = await source.fetch_recent(["cs.AI"], limit=10)

    assert papers == []
    assert calls == 2


@pytest.mark.asyncio
async def test_get_with_retry_raises_typed_error_on_exhaustion(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Internal helper raises ArxivUnavailableError, not httpx.HTTPStatusError."""
    monkeypatch.setattr("arxivdigest.adapters.arxiv.source.asyncio.sleep", _noop_sleep)

    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(429)

    async with _client_with_handler(handler) as client:
        source = ArxivSource(client, base_url=ARXIV_API_URL)
        with pytest.raises(ArxivUnavailableError):
            await source._get_with_retry({})


@pytest.mark.asyncio
async def test_backwards_compat_alias_still_works() -> None:
    """ArxivRateLimitedError is preserved as an alias for ArxivUnavailableError.

    External code that imported the original name (downstream adapters,
    notebooks, etc.) keeps working without an import-renaming churn.
    """
    assert ArxivRateLimitedError is ArxivUnavailableError


@pytest.mark.asyncio
async def test_get_with_retry_propagates_non_transient_4xx(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A 404 (or any non-429 4xx) is not transient — must propagate to Sentry."""
    monkeypatch.setattr("arxivdigest.adapters.arxiv.source.asyncio.sleep", _noop_sleep)

    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, text="not found")

    async with _client_with_handler(handler) as client:
        source = ArxivSource(client)
        with pytest.raises(httpx.HTTPStatusError):
            await source._get_with_retry({})


@pytest.mark.asyncio
async def test_retry_honors_retry_after_header(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When arxiv sends Retry-After, the helper waits that long (capped)."""
    waits: list[float] = []

    async def capture_sleep(seconds: float) -> None:
        waits.append(seconds)

    monkeypatch.setattr("arxivdigest.adapters.arxiv.source.asyncio.sleep", capture_sleep)
    statuses = [(429, "7"), (200, None)]
    calls = 0

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        status, retry_after = statuses[calls]
        calls += 1
        headers = {"Retry-After": retry_after} if retry_after else {}
        body = _EMPTY_ATOM_FEED if status == 200 else "rate-limited"
        return httpx.Response(status, text=body, headers=headers)

    async with _client_with_handler(handler) as client:
        source = ArxivSource(client)
        await source.fetch_recent(["cs.AI"], limit=10)

    assert waits == [7.0]  # honoured exactly the Retry-After value


async def _noop_sleep(_seconds: float) -> None:
    """asyncio.sleep replacement so tests don't actually wait."""
    return None
