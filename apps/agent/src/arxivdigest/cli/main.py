import typer

from arxivdigest.adapters.observability.logging import configure_logging
from arxivdigest.cli.commands import hello
from arxivdigest.config import get_settings

app = typer.Typer(
    name="arxivdigest",
    help="Autonomous daily arxiv digest agent.",
    no_args_is_help=True,
)


@app.callback()
def _root() -> None:
    """Initialise settings, logging, and (eventually) observability."""
    settings = get_settings()
    configure_logging(app_env=settings.app_env, log_level=settings.log_level)


app.command(name="hello")(hello.hello)
