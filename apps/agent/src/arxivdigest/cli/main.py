import typer

from arxivdigest.cli.commands import hello

app = typer.Typer(
    name="arxivdigest",
    help="Autonomous daily arxiv digest agent.",
    no_args_is_help=True,
)


@app.callback()
def _root() -> None:
    """Force multi-command mode so subcommand names (e.g. `hello`) are required."""


app.command(name="hello")(hello.hello)
