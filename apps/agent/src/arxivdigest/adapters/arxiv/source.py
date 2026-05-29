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
_MAX_ATTEMPTS = 3
_DEFAULT_RETRY_WAIT = 3.0

_ATOM = "http://www.w3.org/2005/Atom"
_VERSION_SUFFIX = re.compile(r"v\d+$")


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
        """GET with bounded retry on 429, honoring the ``Retry-After`` header."""
        response: httpx.Response | None = None
        for attempt in range(1, _MAX_ATTEMPTS + 1):
            response = await self._client.get(self._base_url, params=params, headers=_HEADERS)
            if response.status_code != httpx.codes.TOO_MANY_REQUESTS:
                break
            wait = float(response.headers.get("Retry-After", _DEFAULT_RETRY_WAIT))
            log.warning("arxiv.rate_limited", attempt=attempt, wait=wait)
            if attempt < _MAX_ATTEMPTS:
                await asyncio.sleep(wait)
        assert response is not None  # noqa: S101 — loop runs at least once
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
            response = await self._get_with_retry(params)
            # Trusted HTTPS source (arxiv's own Atom API); not untrusted XML.
            root = ET.fromstring(response.text)  # noqa: S314

        papers = [
            paper
            for entry in root.findall(f"{{{_ATOM}}}entry")
            if (paper := _parse_entry(entry)) is not None
        ]
        log.info("arxiv.fetched", requested=limit, parsed=len(papers))
        return papers
