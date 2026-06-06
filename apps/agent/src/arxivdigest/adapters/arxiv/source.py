"""arxiv paper source — raw Atom API over httpx, parsed with stdlib xml.etree.

The arxiv API (``export.arxiv.org/api/query``) returns an Atom feed; no SDK is
needed for a single read-only query. Implements the :class:`PaperSource` port.
"""

from __future__ import annotations

import asyncio
import re
from collections.abc import Sequence
from datetime import datetime
from xml.etree import ElementTree as ET

import httpx
import structlog

from arxivdigest.adapters.observability.tracing import trace_span
from arxivdigest.domain.models import RawPaper

log = structlog.get_logger(__name__)

ARXIV_API_URL = "https://export.arxiv.org/api/query"

# arxiv asks API clients to identify themselves and space out requests; an
# anonymous default User-Agent gets 429'd. See https://info.arxiv.org/help/api/
_USER_AGENT = "ArxivDigest/0.1 (+https://github.com/imtiaj-007/ArxivDigest)"
_HEADERS = {"User-Agent": _USER_AGENT}
# GH Actions runners share IPs across many jobs hitting arxiv; the bare 3-req
# retry budget exhausts inside ~6s on a sustained throttle. The 5-attempt
# exponential schedule (3 → 6 → 12 → 24 → 30) gives ~75s of total backoff.
_MAX_ATTEMPTS = 5
_DEFAULT_RETRY_WAIT = 3.0
_MAX_BACKOFF_WAIT = 30.0
# Honour Retry-After but cap so arxiv can't park the cron for an hour.
_RETRY_AFTER_CAP = 60.0


class ArxivUnavailableError(Exception):
    """Raised when arxiv keeps returning a transient status after the bounded
    retry budget. Covers 429 (rate limit) and 5xx (server unavailable / gateway
    errors). Caller treats this the same as "no new papers this run".
    """


# Back-compat alias: the original name only covered 429. Existing imports
# (tests, downstream code) still work; new code should prefer the broader name.
ArxivRateLimitedError = ArxivUnavailableError

_ATOM = "http://www.w3.org/2005/Atom"
_VERSION_SUFFIX = re.compile(r"v\d+$")


def _is_transient(status_code: int) -> bool:
    """429 + any 5xx — arxiv-side throttling or server unavailability.

    All of these recover on the next attempt or the next day's cron;
    treating them as fatal would noise up the Sentry feed for outages
    we can't fix anyway.
    """
    return status_code == httpx.codes.TOO_MANY_REQUESTS or 500 <= status_code < 600


def _clean(text: str | None) -> str:
    """Collapse arxiv's hard-wrapped whitespace into a single-spaced string."""
    return " ".join(text.split()) if text else ""


def _parse_entry(entry: ET.Element) -> RawPaper | None:
    """Map one Atom ``<entry>`` to a RawPaper, or None if it's missing essentials."""
    id_text = entry.findtext(f"{{{_ATOM}}}id")
    title = _clean(entry.findtext(f"{{{_ATOM}}}title"))
    abstract = _clean(entry.findtext(f"{{{_ATOM}}}summary"))
    published_text = entry.findtext(f"{{{_ATOM}}}published")
    if not (id_text and title and abstract and published_text):
        return None

    # id looks like "http://arxiv.org/abs/2401.01234v2" → "2401.01234"
    arxiv_id = _VERSION_SUFFIX.sub("", id_text.rsplit("/abs/", 1)[-1])

    authors = [
        _clean(name)
        for author in entry.findall(f"{{{_ATOM}}}author")
        if (name := author.findtext(f"{{{_ATOM}}}name"))
    ]
    categories = [
        term
        for category in entry.findall(f"{{{_ATOM}}}category")
        if (term := category.get("term"))
    ]
    pdf_url = next(
        (
            href
            for link in entry.findall(f"{{{_ATOM}}}link")
            if link.get("type") == "application/pdf" and (href := link.get("href"))
        ),
        None,
    )

    return RawPaper(
        arxiv_id=arxiv_id,
        title=title,
        abstract=abstract,
        authors=authors,
        categories=categories,
        published_at=datetime.fromisoformat(published_text),
        pdf_url=pdf_url,
    )


class ArxivSource:
    """Fetches recent submissions from the arxiv Atom API."""

    def __init__(self, client: httpx.AsyncClient, base_url: str = ARXIV_API_URL) -> None:
        self._client = client
        self._base_url = base_url

    async def _get_with_retry(self, params: dict[str, str | int]) -> httpx.Response:
        """GET with bounded retry on transient statuses (429 + all 5xx).

        Backoff is exponential (``_DEFAULT_RETRY_WAIT`` doubled per attempt,
        capped at ``_MAX_BACKOFF_WAIT``) when no ``Retry-After`` header is
        present. 429 may carry one (we honour up to ``_RETRY_AFTER_CAP``);
        5xx typically does not. Raises :class:`ArxivUnavailableError` if every
        attempt returns a transient status.
        """
        response: httpx.Response | None = None
        for attempt in range(1, _MAX_ATTEMPTS + 1):
            response = await self._client.get(self._base_url, params=params, headers=_HEADERS)
            if not _is_transient(response.status_code):
                break
            retry_after = response.headers.get("Retry-After")
            if retry_after is not None:
                wait = min(float(retry_after), _RETRY_AFTER_CAP)
            else:
                wait = min(_DEFAULT_RETRY_WAIT * (2 ** (attempt - 1)), _MAX_BACKOFF_WAIT)
            log.warning(
                "arxiv.transient_error",
                attempt=attempt,
                status=response.status_code,
                wait=wait,
                retry_after=retry_after,
            )
            if attempt < _MAX_ATTEMPTS:
                await asyncio.sleep(wait)
        assert response is not None  # noqa: S101 — loop runs at least once
        if _is_transient(response.status_code):
            raise ArxivUnavailableError(
                f"arxiv returned {response.status_code} on all {_MAX_ATTEMPTS} attempts",
            )
        response.raise_for_status()
        return response

    async def fetch_recent(
        self,
        categories: Sequence[str],
        limit: int,
    ) -> list[RawPaper]:
        query = " OR ".join(f"cat:{category}" for category in categories)
        params: dict[str, str | int] = {
            "search_query": query,
            "sortBy": "submittedDate",
            "sortOrder": "descending",
            "start": 0,
            "max_results": limit,
        }
        with trace_span("arxiv.fetch_recent", categories=list(categories), limit=limit):
            try:
                response = await self._get_with_retry(params)
            except ArxivUnavailableError as exc:
                # Bulkhead: a persistent 429 or 5xx is treated as "no new
                # papers this run" rather than a fatal error. Downstream
                # stages operate on rows where the relevant column IS NULL,
                # so the pipeline still drains any backlog from previous
                # runs and the cron stays green.
                log.warning(
                    "arxiv.unavailable_giving_up",
                    error=str(exc),
                    action="returning empty list; pipeline continues idempotently",
                )
                return []
            # Trusted HTTPS source (arxiv's own Atom API); not untrusted XML.
            root = ET.fromstring(response.text)  # noqa: S314

        papers = [
            paper
            for entry in root.findall(f"{{{_ATOM}}}entry")
            if (paper := _parse_entry(entry)) is not None
        ]
        # Surface the boundaries of the returned batch so cache/indexing drift is
        # visible on the first cron line, not after days of zero-new-paper runs.
        first = papers[0] if papers else None
        last = papers[-1] if papers else None
        log.info(
            "arxiv.fetched",
            requested=limit,
            parsed=len(papers),
            newest_id=first.arxiv_id if first else None,
            oldest_id=last.arxiv_id if last else None,
            oldest_published=last.published_at.date().isoformat() if last else None,
        )
        return papers
