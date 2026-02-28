from __future__ import annotations

import json
from enum import Enum
from pathlib import Path
from typing import Callable

import typer
import yaml
from rich.console import Console
from rich.table import Table

from . import __version__
from .config import LAYER_RULES, REPO_TYPES
from .scaffold import ScaffoldError, ScaffoldOptions, scaffold_project
from .search import search_markdown
from .sync import SyncError, analyze_sync

app = typer.Typer(help="Scaffold and search context-first repositories.")
console = Console()

EXIT_OK = 0
EXIT_ERROR = 1
EXIT_INVALID_INPUT = 2
EXIT_NOT_FOUND = 3


class OutputFormat(str, Enum):
    table = "table"
    json = "json"
    md = "md"


def _json_print(payload: dict) -> None:
    typer.echo(json.dumps(payload, ensure_ascii=True, sort_keys=True))


def _print_key_value_table(title: str, rows: list[tuple[str, str]]) -> None:
    table = Table(title=title)
    table.add_column("Field")
    table.add_column("Value")
    for key, value in rows:
        table.add_row(key, value)
    console.print(table)


def _emit_success(
    command: str,
    output_format: OutputFormat,
    data: dict,
    md_renderer: Callable[[dict], str] | None = None,
    table_renderer: Callable[[dict], None] | None = None,
) -> None:
    if output_format == OutputFormat.json:
        _json_print(
            {
                "ok": True,
                "command": command,
                "exit_code": EXIT_OK,
                "data": data,
            }
        )
        return

    if output_format == OutputFormat.md and md_renderer is not None:
        console.print(md_renderer(data))
        return

    if output_format == OutputFormat.table and table_renderer is not None:
        table_renderer(data)
        return

    # Fallback for simple commands without dedicated renderer.
    if output_format == OutputFormat.md:
        lines = [f"# {command}", ""]
        lines.extend(f"- **{key}**: {value}" for key, value in data.items())
        console.print("\n".join(lines))
    else:
        _print_key_value_table(
            title=command,
            rows=[(str(key), str(value)) for key, value in data.items()],
        )


def _emit_error(
    command: str,
    output_format: OutputFormat,
    exit_code: int,
    code: str,
    message: str,
) -> None:
    if output_format == OutputFormat.json:
        _json_print(
            {
                "ok": False,
                "command": command,
                "exit_code": exit_code,
                "error": {
                    "code": code,
                    "message": message,
                },
            }
        )
    elif output_format == OutputFormat.md:
        console.print(f"# {command}\n\n- **status**: error\n- **code**: {code}\n- **message**: {message}")
    else:
        console.print(f"[red]Error ({code}):[/red] {message}")

    raise typer.Exit(code=exit_code)


@app.command("new")
def new_repo(
    name: str = typer.Argument(..., help="Project name or slug."),
    repo_type: str = typer.Option(..., "--type", help=f"One of: {', '.join(REPO_TYPES)}"),
    destination: Path = typer.Option(Path("."), "--destination", "-d", help="Destination root path."),
    db_type: str = typer.Option("redshift", "--db", help="Database flavor: redshift/postgres/none"),
    author: str = typer.Option("", "--author", help="Author name used in templates."),
    force: bool = typer.Option(False, "--force", help="Allow writing into existing target directory."),
    output_format: OutputFormat = typer.Option(OutputFormat.table, "--format", help="Output format."),
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
        _emit_error(
            command="new",
            output_format=output_format,
            exit_code=EXIT_INVALID_INPUT,
            code="scaffold_error",
            message=str(error),
        )
        raise

    data = {"path": str(target), "repo_type": repo_type, "db_type": db_type}
    _emit_success(command="new", output_format=output_format, data=data)


@app.command("search")
def search_repo(
    query: str = typer.Argument(..., help="Text query to find in markdown files."),
    scope: Path = typer.Option(Path("."), "--scope", help="Directory to search within."),
    limit: int = typer.Option(10, "--limit", "-l", help="Max hits."),
    output_format: OutputFormat = typer.Option(OutputFormat.table, "--format", help="Output format."),
):
    """Search markdown files with lightweight relevance scoring."""
    hits = search_markdown(query=query, scope=scope.resolve(), limit=limit)
    if not hits:
        _emit_error(
            command="search",
            output_format=output_format,
            exit_code=EXIT_NOT_FOUND,
            code="no_matches",
            message="No matches found.",
        )
        raise

    data = {
        "query": query,
        "scope": str(scope.resolve()),
        "limit": limit,
        "hits": [
            {
                "path": str(hit.path),
                "score": round(hit.score, 8),
                "line": hit.line,
                "snippet": hit.snippet,
            }
            for hit in hits
        ],
    }

    def render_md(payload: dict) -> str:
        lines = [f"# Search results: `{payload['query']}`", ""]
        for hit in payload["hits"]:
            lines.append(
                f"- `{hit['path']}:{hit['line']}` | score={hit['score']:.4f} | {hit['snippet']}"
            )
        return "\n".join(lines)

    def render_table(payload: dict) -> None:
        table = Table(title=f"Search results for: {payload['query']}")
        table.add_column("Score", justify="right")
        table.add_column("File")
        table.add_column("Line", justify="right")
        table.add_column("Snippet")
        for hit in payload["hits"]:
            table.add_row(f"{hit['score']:.2f}", hit["path"], str(hit["line"]), hit["snippet"])
        console.print(table)

    _emit_success(
        command="search",
        output_format=output_format,
        data=data,
        md_renderer=render_md,
        table_renderer=render_table,
    )


@app.command("list")
def list_repos(
    scope: Path = typer.Option(Path("."), "--scope", help="Directory to inspect."),
    output_format: OutputFormat = typer.Option(OutputFormat.table, "--format", help="Output format."),
):
    """List repositories scaffolded by repokit."""
    rows = []
    for marker in scope.resolve().rglob(".repokit.yml"):
        data = yaml.safe_load(marker.read_text(encoding="utf-8")) or {}
        rows.append(
            {
                "path": str(marker.parent),
                "type": str(data.get("type", "?")),
                "created_at": str(data.get("created_at", "?")),
            }
        )

    if not rows:
        _emit_error(
            command="list",
            output_format=output_format,
            exit_code=EXIT_NOT_FOUND,
            code="no_repositories",
            message="No repokit repositories found.",
        )
        raise

    rows.sort(key=lambda item: item["path"])
    data = {"scope": str(scope.resolve()), "repositories": rows}

    def render_md(payload: dict) -> str:
        lines = [f"# Repositories in `{payload['scope']}`", ""]
        for item in payload["repositories"]:
            lines.append(f"- `{item['path']}` ({item['type']}, created {item['created_at']})")
        return "\n".join(lines)

    def render_table(payload: dict) -> None:
        table = Table(title="Repokit repositories")
        table.add_column("Path")
        table.add_column("Type")
        table.add_column("Created")
        for item in payload["repositories"]:
            table.add_row(item["path"], item["type"], item["created_at"])
        console.print(table)

    _emit_success(command="list", output_format=output_format, data=data, md_renderer=render_md, table_renderer=render_table)


@app.command("info")
def repo_info(
    repo_path: Path = typer.Argument(..., help="Path to a repository."),
    output_format: OutputFormat = typer.Option(OutputFormat.table, "--format", help="Output format."),
):
    """Show document layers and completion status."""
    root = repo_path.resolve()
    if not root.exists() or not root.is_dir():
        _emit_error(
            command="info",
            output_format=output_format,
            exit_code=EXIT_INVALID_INPUT,
            code="invalid_repository_path",
            message=f"Repository path does not exist: {root}",
        )
        raise

    layers = []
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
            layers.append({"layer": layer, "target": target, "status": status})

    data = {"repo_path": str(root), "layers": layers}

    def render_md(payload: dict) -> str:
        lines = [f"# Repository info: `{payload['repo_path']}`", ""]
        for item in payload["layers"]:
            lines.append(f"- `{item['layer']}` | `{item['target']}` | `{item['status']}`")
        return "\n".join(lines)

    def render_table(payload: dict) -> None:
        table = Table(title=f"Repository info: {payload['repo_path']}")
        table.add_column("Layer")
        table.add_column("Target")
        table.add_column("Status")
        for item in payload["layers"]:
            table.add_row(item["layer"], item["target"], item["status"])
        console.print(table)

    _emit_success(command="info", output_format=output_format, data=data, md_renderer=render_md, table_renderer=render_table)


@app.command("sync")
def sync_repo(
    repo_path: Path = typer.Argument(..., help="Path to a repository."),
    repo_type: str = typer.Option("", "--type", help=f"Override repo type ({', '.join(REPO_TYPES)})"),
    output_format: OutputFormat = typer.Option(OutputFormat.table, "--format", help="Output format."),
):
    """Check documentation drift against repokit templates."""
    try:
        report = analyze_sync(repo_path.resolve(), repo_type=repo_type or None)
    except SyncError as error:
        _emit_error(
            command="sync",
            output_format=output_format,
            exit_code=EXIT_INVALID_INPUT,
            code="sync_error",
            message=str(error),
        )
        raise

    data = {
        "repo_path": str(repo_path.resolve()),
        "repo_type": report.repo_type,
        "missing": list(report.missing),
        "unexpected": list(report.unexpected),
    }

    def render_md(payload: dict) -> str:
        lines = [f"# Sync report: `{payload['repo_path']}`", ""]
        lines.append(f"- **repo_type**: `{payload['repo_type']}`")
        lines.append(f"- **missing_count**: {len(payload['missing'])}")
        lines.append(f"- **unexpected_count**: {len(payload['unexpected'])}")
        if payload["missing"]:
            lines.append("\n## Missing")
            lines.extend(f"- `{item}`" for item in payload["missing"])
        if payload["unexpected"]:
            lines.append("\n## Unexpected")
            lines.extend(f"- `{item}`" for item in payload["unexpected"])
        return "\n".join(lines)

    def render_table(payload: dict) -> None:
        console.print(f"[bold]Repo type:[/bold] {payload['repo_type']}")
        if payload["missing"]:
            console.print("[yellow]Missing expected files:[/yellow]")
            for item in payload["missing"]:
                console.print(f"- {item}")
        else:
            console.print("[green]No missing expected files.[/green]")
        if payload["unexpected"]:
            console.print("[yellow]Unexpected scaffold files:[/yellow]")
            for item in payload["unexpected"]:
                console.print(f"- {item}")
        else:
            console.print("[green]No unexpected scaffold files.[/green]")

    _emit_success(command="sync", output_format=output_format, data=data, md_renderer=render_md, table_renderer=render_table)


@app.command("version")
def version(
    output_format: OutputFormat = typer.Option(OutputFormat.table, "--format", help="Output format."),
) -> None:
    """Print version."""
    _emit_success(command="version", output_format=output_format, data={"version": __version__})


if __name__ == "__main__":
    app()
