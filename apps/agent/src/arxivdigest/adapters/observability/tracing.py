"""Langfuse tracing — silent no-op when keys are absent.

Use ``trace_span`` as a context manager around any operation that should appear
in the Langfuse UI; it yields a span when tracing is enabled, ``None`` otherwise.

Typical bootstrap order (handled by ``cli/main.py``)::

    init_tracing(settings)
    ... run commands ...
    shutdown_tracing()  # registered via atexit
"""

from __future__ import annotations

import atexit
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

import structlog
from langfuse import Langfuse, get_client

from arxivdigest.config import Settings

log = structlog.get_logger(__name__)

_client: Langfuse | None = None


def init_tracing(settings: Settings) -> None:
    """Initialise Langfuse if both keys are present; otherwise log and stay disabled."""
    global _client
    if _client is not None:
        return  # idempotent

    if not (settings.langfuse_public_key and settings.langfuse_secret_key):
        log.info("tracing.disabled", reason="LANGFUSE_PUBLIC_KEY / LANGFUSE_SECRET_KEY not set")
        return

    _client = Langfuse(
        public_key=settings.langfuse_public_key,
        secret_key=settings.langfuse_secret_key,
        host=settings.langfuse_host,
        environment=settings.app_env,
    )
    atexit.register(shutdown_tracing)
    log.info("tracing.enabled", host=settings.langfuse_host, env=settings.app_env)


def shutdown_tracing() -> None:
    """Flush pending spans + close client. Safe to call multiple times."""
    global _client
    if _client is None:
        return
    try:
        _client.flush()
    finally:
        _client = None


def _get_tracer() -> Langfuse | None:
    """Return the live Langfuse client, or None when tracing is disabled."""
    if _client is None:
        return None
    return get_client()


@contextmanager
def trace_span(span_name: str, **input_data: Any) -> Iterator[Any]:
    """Open a Langfuse span. Yields ``None`` when tracing is disabled (no overhead)."""
    tracer = _get_tracer()
    if tracer is None:
        yield None
        return
    with tracer.start_as_current_observation(
        name=span_name, input=input_data or None
    ) as span:
        yield span
