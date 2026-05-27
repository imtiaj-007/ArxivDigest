"""Sentry error tracking — silent no-op when SENTRY_DSN is absent.

Sentry auto-captures uncaught exceptions once initialised; no decoration of
business logic is required. We deliberately set ``traces_sample_rate=0`` because
LLM tracing lives in Langfuse, not Sentry — Sentry stays focused on errors.
"""

from __future__ import annotations

import sentry_sdk
import structlog

from arxivdigest.config import Settings

log = structlog.get_logger(__name__)

_initialised = False


def init_sentry(settings: Settings) -> None:
    """Initialise Sentry if SENTRY_DSN is present; otherwise log and stay disabled."""
    global _initialised
    if _initialised:
        return  # idempotent

    if not settings.sentry_dsn:
        log.info("sentry.disabled", reason="SENTRY_DSN not set")
        return

    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        environment=settings.sentry_environment,
        traces_sample_rate=0.0,
        send_default_pii=False,
    )
    _initialised = True
    log.info("sentry.enabled", environment=settings.sentry_environment)
