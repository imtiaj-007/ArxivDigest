"""ArxivSource retry + 429 graceful-degradation behavior, verified without network."""

from __future__ import annotations

from collections.abc import Callable

import httpx
import pytest

from arxivdigest.adapters.arxiv.source import (
    _MAX_ATTEMPTS,
    ARXIV_API_URL,
    ArxivRateLimitedError,
    ArxivSource,
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
async def test_get_with_retry_raises_typed_error_on_exhaustion(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Internal helper raises ArxivRateLimitedError, not httpx.HTTPStatusError."""
    monkeypatch.setattr("arxivdigest.adapters.arxiv.source.asyncio.sleep", _noop_sleep)

    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(429)

    async with _client_with_handler(handler) as client:
        source = ArxivSource(client, base_url=ARXIV_API_URL)
        with pytest.raises(ArxivRateLimitedError):
            await source._get_with_retry({})


@pytest.mark.asyncio
async def test_get_with_retry_propagates_non_429_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """5xx responses still bubble up as HTTPStatusError — only 429 is swallowed."""
    monkeypatch.setattr("arxivdigest.adapters.arxiv.source.asyncio.sleep", _noop_sleep)

    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, text="service unavailable")

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
