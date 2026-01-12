"""CLI for Keboola docs MCP server."""

from pathlib import Path
from typing import Optional

import typer

from .updater import update_docs_sync

app = typer.Typer(
    name="keboola-docs",
    help="Keboola API Documentation MCP Server CLI",
)


@app.command()
def update(
    api: Optional[str] = typer.Option(
        None,
        "--api",
        "-a",
        help="Filter by API name (e.g., 'storage' to update only Storage API)",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        "-n",
        help="Check for updates without writing files",
    ),
    sources_file: Optional[Path] = typer.Option(
        None,
        "--sources",
        "-s",
        help="Path to sources.yaml file",
    ),
) -> None:
    """Update API documentation from online sources."""
    action = "Checking" if dry_run else "Updating"
    typer.echo(f"{action} documentation...")

    results = update_docs_sync(sources_file, api, dry_run)

    # Print results
    updated_count = 0
    error_count = 0

    for result in results:
        if result.success:
            if result.updated:
                typer.echo(f"  [green]UPDATED[/green] {result.source.name}", color=True)
                updated_count += 1
            else:
                typer.echo(f"  [dim]OK[/dim] {result.source.name}", color=True)
        else:
            typer.echo(f"  [red]ERROR[/red] {result.source.name}: {result.error}", color=True)
            error_count += 1

    # Summary
    typer.echo("")
    if dry_run:
        typer.echo(f"Would update {updated_count} file(s)")
    else:
        typer.echo(f"Updated {updated_count} file(s)")

    if error_count > 0:
        typer.echo(f"[red]{error_count} error(s)[/red]", color=True)
        raise typer.Exit(1)


@app.command()
def list_sources(
    sources_file: Optional[Path] = typer.Option(
        None,
        "--sources",
        "-s",
        help="Path to sources.yaml file",
    ),
) -> None:
    """List all configured documentation sources."""
    from .config import load_sources

    sources = load_sources(sources_file)

    typer.echo("Configured documentation sources:\n")

    for source in sources:
        typer.echo(f"  [bold]{source.name}[/bold]", color=True)
        typer.echo(f"    Format: {source.format}")
        typer.echo(f"    URL: {source.url}")
        typer.echo(f"    Output: {source.output}")
        if source.description:
            typer.echo(f"    Description: {source.description}")
        typer.echo("")


@app.command()
def serve(
    host: str = typer.Option("localhost", "--host", "-h", help="Host to bind to"),
    port: int = typer.Option(8000, "--port", "-p", help="Port to bind to"),
) -> None:
    """Start the MCP server (for development/testing)."""
    typer.echo(f"Starting MCP server on {host}:{port}...")
    typer.echo("Use Ctrl+C to stop")

    # Import here to avoid circular imports
    from .server import run_server

    run_server()


if __name__ == "__main__":
    app()
