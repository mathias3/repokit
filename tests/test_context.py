import json
from pathlib import Path

from typer.testing import CliRunner

from repokit.cli import EXIT_INVALID_INPUT, EXIT_NOT_FOUND, EXIT_OK, app
from repokit.scaffold import ScaffoldOptions, scaffold_project

runner = CliRunner()


def _parse_json_output(output: str) -> dict:
    lines = [line for line in output.splitlines() if line.strip()]
    return json.loads(lines[-1])


def test_context_inventory_json(tmp_path: Path):
    scaffold_project(
        ScaffoldOptions(
            project_name="Source Repo",
            repo_type="agent",
            destination_root=tmp_path,
        )
    )

    result = runner.invoke(app, ["context", "inventory", "--scope", str(tmp_path), "--format", "json"])

    assert result.exit_code == EXIT_OK
    payload = _parse_json_output(result.stdout)
    assert payload["command"] == "context inventory"
    assert len(payload["data"]["repositories"]) == 1
    repo = payload["data"]["repositories"][0]
    assert "AGENTS.md" in repo["present"]
    assert "PROJECT_RULES.md" in repo["present"]


def test_context_inventory_no_repositories(tmp_path: Path):
    result = runner.invoke(app, ["context", "inventory", "--scope", str(tmp_path), "--format", "json"])

    assert result.exit_code == EXIT_NOT_FOUND
    payload = _parse_json_output(result.stdout)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "no_repositories"


def test_context_transfer_copy(tmp_path: Path):
    source = scaffold_project(
        ScaffoldOptions(
            project_name="Source Repo",
            repo_type="agent",
            destination_root=tmp_path,
        )
    )
    destination = scaffold_project(
        ScaffoldOptions(
            project_name="Destination Repo",
            repo_type="agent",
            destination_root=tmp_path,
        )
    )

    (source / "PROJECT_RULES.md").write_text("# PROJECT_RULES\n\n- Use safe migration steps.\n", encoding="utf-8")

    result = runner.invoke(
        app,
        [
            "context",
            "transfer",
            "--from",
            str(source),
            "--to",
            str(destination),
            "--mode",
            "copy",
            "--file",
            "PROJECT_RULES.md",
            "--format",
            "json",
        ],
    )

    assert result.exit_code == EXIT_OK
    payload = _parse_json_output(result.stdout)
    assert payload["data"]["copied"] == ["PROJECT_RULES.md"]
    assert "Use safe migration steps." in (destination / "PROJECT_RULES.md").read_text(encoding="utf-8")
    assert (source / "PROJECT_RULES.md").exists()


def test_context_transfer_invalid_source(tmp_path: Path):
    destination = scaffold_project(
        ScaffoldOptions(
            project_name="Destination Repo",
            repo_type="agent",
            destination_root=tmp_path,
        )
    )

    result = runner.invoke(
        app,
        [
            "context",
            "transfer",
            "--from",
            str(tmp_path / "missing"),
            "--to",
            str(destination),
            "--format",
            "json",
        ],
    )

    assert result.exit_code == EXIT_INVALID_INPUT
    payload = _parse_json_output(result.stdout)
    assert payload["error"]["code"] == "context_error"


def test_context_compress_archives_middle_lines(tmp_path: Path):
    repo = scaffold_project(
        ScaffoldOptions(
            project_name="Compress Repo",
            repo_type="agent",
            destination_root=tmp_path,
        )
    )

    lines = ["# LEARNINGS", ""] + [f"- item {idx}" for idx in range(1, 231)]
    (repo / "LEARNINGS.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    result = runner.invoke(
        app,
        [
            "context",
            "compress",
            str(repo),
            "--file",
            "LEARNINGS.md",
            "--threshold",
            "200",
            "--keep-tail",
            "30",
            "--header-lines",
            "8",
            "--format",
            "json",
        ],
    )

    assert result.exit_code == EXIT_OK
    payload = _parse_json_output(result.stdout)
    assert payload["data"]["archived"] is True
    assert payload["data"]["original_lines"] > payload["data"]["final_lines"]

    archive_dir = repo / "memory" / "archive"
    archives = list(archive_dir.glob("LEARNINGS-*.md"))
    assert archives


def test_context_compress_below_threshold_no_archive(tmp_path: Path):
    repo = scaffold_project(
        ScaffoldOptions(
            project_name="Small Repo",
            repo_type="agent",
            destination_root=tmp_path,
        )
    )

    result = runner.invoke(
        app,
        ["context", "compress", str(repo), "--threshold", "1000", "--format", "json"],
    )

    assert result.exit_code == EXIT_OK
    payload = _parse_json_output(result.stdout)
    assert payload["data"]["archived"] is False
