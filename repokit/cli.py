from __future__ import annotations

from pathlib import Path

import typer
import yaml
from rich.console import Console
from rich.table import Table

from . import __version__
from .config import LAYER_RULES, REPO_TYPES
from .scaffold import ScaffoldError, ScaffoldOptions, scaffold_project
from .search import search_markdown

app = typer.Typer(help="Scaffold and search context-first repositories.")
console = Console()


@app.command("new")
def new_repo(
    name: str = typer.Argument(..., help="Project name or slug."),
    repo_type: str = typer.Option(..., "--type", help=f"One of: {', '.join(REPO_TYPES)}"),
    destination: Path = typer.Option(Path("."), "--destination", "-d", help="Destination root path."),
    db_type: str = typer.Option("redshift", "--db", help="Database flavor: redshift/postgres/none"),
    author: str = typer.Option("", "--author", help="Author name used in templates."),
    force: bool = typer.Option(False, "--force", help="Allow writing into existing target directory."),
):
    """Create a repository scaffold from templates."""
    options = ScaffoldOptions(
        project_name=name,
        repo_type=repo_type,
        destination_root=destination.resolve(),
        db_type=db_type,
        author=author,
        force=force,
    )
    try:
        target = scaffold_project(options)
    except ScaffoldError as error:
        console.print(f"[red]Error:[/red] {error}")
        raise typer.Exit(code=1) from error

    console.print(f"[green]Created:[/green] {target}")


@app.command("search")
def search_repo(
    query: str = typer.Argument(..., help="Text query to find in markdown files."),
    scope: Path = typer.Option(Path("."), "--scope", help="Directory to search within."),
    limit: int = typer.Option(10, "--limit", "-l", help="Max hits."),
):
    """Search markdown files with lightweight relevance scoring."""
    hits = search_markdown(query=query, scope=scope.resolve(), limit=limit)
    if not hits:
        console.print("[yellow]No matches found.[/yellow]")
        raise typer.Exit(code=0)

    table = Table(title=f"Search results for: {query}")
    table.add_column("Score", justify="right")
    table.add_column("File")
    table.add_column("Line", justify="right")
    table.add_column("Snippet")

    for hit in hits:
        table.add_row(f"{hit.score:.2f}", str(hit.path), str(hit.line), hit.snippet)

    console.print(table)


@app.command("list")
def list_repos(
    scope: Path = typer.Option(Path("."), "--scope", help="Directory to inspect."),
):
    """List repositories scaffolded by repokit."""
    table = Table(title="Repokit repositories")
    table.add_column("Path")
    table.add_column("Type")
    table.add_column("Created")

    found = 0
    for marker in scope.resolve().rglob(".repokit.yml"):
        data = yaml.safe_load(marker.read_text(encoding="utf-8")) or {}
        table.add_row(str(marker.parent), str(data.get("type", "?")), str(data.get("created_at", "?")))
        found += 1

    if not found:
        console.print("[yellow]No repokit repositories found.[/yellow]")
        raise typer.Exit(code=0)

    console.print(table)


@app.command("info")
def repo_info(
    repo_path: Path = typer.Argument(..., help="Path to a repository."),
):
    """Show document layers and completion status."""
    root = repo_path.resolve()
    table = Table(title=f"Repository info: {root}")
    table.add_column("Layer")
    table.add_column("Target")
    table.add_column("Status")

    for layer, targets in LAYER_RULES.items():
        for target in targets:
            path = root / target
            if path.is_dir():
                status = "present"
            elif path.exists():
                content = path.read_text(encoding="utf-8", errors="ignore")
                status = "filled" if content.strip() else "empty"
            else:
                status = "missing"
            table.add_row(layer, target, status)

    console.print(table)


@app.command("version")
def version() -> None:
    """Print version."""
    console.print(__version__)


if __name__ == "__main__":
    app()
