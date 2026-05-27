import structlog

log = structlog.get_logger()


def hello(name: str = "world") -> None:
    """Smoke-test command. Logs a structured hello message."""
    log.info("hello", target=name, app="arxivdigest")
