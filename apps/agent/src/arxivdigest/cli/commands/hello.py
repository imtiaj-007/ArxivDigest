import structlog

from arxivdigest.adapters.observability.tracing import trace_span

log = structlog.get_logger()


def hello(name: str = "world") -> None:
    """Smoke-test command. Logs a structured hello message and emits a trace span."""
    with trace_span("hello", name=name) as span:
        log.info("hello", target=name, app="arxivdigest")
        if span is not None:
            span.update(output={"message": f"hello {name}"})
