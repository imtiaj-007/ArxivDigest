import structlog

from arxivdigest.adapters.observability.tracing import trace_span

log = structlog.get_logger()


def hello(name: str = "world", crash: bool = False) -> None:
    """Smoke-test command. Logs a structured hello message and emits a trace span.

    Pass ``--crash`` to deliberately raise an exception (used once to verify Sentry receives it).
    """
    with trace_span("hello", name=name) as span:
        log.info("hello", target=name, app="arxivdigest")
        if span is not None:
            span.update(output={"message": f"hello {name}"})
        if crash:
            raise RuntimeError(f"intentional crash from hello (target={name})")
