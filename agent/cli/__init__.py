"""AutoHost CLI - Pure agentic interface.

Two ways to use:
- `autohost` - Terminal agent (interactive)
- `autohost serve` - Web UI
"""

import warnings

import typer

from agent.cli.console import Icons, console
from agent.config import settings
from agent.logging import configure_logging
from agent.version import __version__

# Suppress Python deprecation warnings to keep CLI output clean
# These come from third-party libraries and clutter the user experience
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=PendingDeprecationWarning)
warnings.filterwarnings("ignore", category=FutureWarning)

# Configure structured logging with Rich handler for console-aware output
# This integrates properly with Rich's Live display and prevents
# log messages from corrupting the CLI spinner
configure_logging(rich_console=console, json_output=settings.json_logs)

app = typer.Typer(
    name="autohost",
    help=f"{Icons.ROBOT} Your local AI agent",
    add_completion=False,
    pretty_exceptions_show_locals=False,
    no_args_is_help=False,
)


def version_callback(value: bool):
    if value:
        console.print(f"[bold cyan]AutoHost[/bold cyan] v{__version__}")
        raise typer.Exit()


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    version: bool = typer.Option(
        None, "--version", "-V", callback=version_callback, is_eager=True
    ),
    model: str = typer.Option(None, "--model", "-m", help="Model to use"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show detailed output"),
):
    """🤖 AutoHost - Your local AI agent.

    Just run `autohost` and start typing.
    The agent handles questions AND tasks automatically.

    Examples:
        autohost                   # Start agent
        autohost serve             # Start web UI
    """
    # Skip if subcommand (like serve)
    if ctx.invoked_subcommand is not None:
        return

    if verbose:
        configure_logging(
            verbose=True, rich_console=console, json_output=settings.json_logs
        )

    from agent.cli.agent_loop import run_agent

    run_agent(model)


@app.command()
def serve(
    host: str = typer.Option(settings.server_host, "--host", "-h"),
    port: int = typer.Option(settings.server_port, "--port", "-p"),
):
    """Start the web UI."""
    import webbrowser

    import uvicorn

    url = f"http://{host}:{port}"
    console.print(f"\n  {Icons.ROBOT} [bold]AutoHost[/bold] → {url}\n")
    webbrowser.open(url)
    uvicorn.run(
        "agent.orchestrator.server:app",
        host=host,
        port=port,
        reload=True,
        log_level="warning",
    )


@app.command()
def analyze(path: str = typer.Argument(..., help="Path to the repository to analyze")):
    """Analyze a codebase to understand its architecture."""
    from agent.tools.codebase_analyzer import analyze_codebase
    from rich.panel import Panel
    from rich.markdown import Markdown

    console.print(f"\n  {Icons.ROBOT} [bold]Analyzing codebase at:[/bold] {path}\n")

    with console.status("[cyan]Analyzing files, detecting frameworks, generating architecture map...", spinner="dots12"):
        summary = analyze_codebase(path)

    if summary.startswith("Error"):
        console.print(f"[bold red]{summary}[/bold red]")
    else:
        console.print(Panel(summary, title="Analysis Complete", border_style="green"))
        console.print("\n[dim]Generated architecture.md and repo_map.json in the target directory.[/dim]")

def cli():
    app()
