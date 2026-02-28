import json
from pathlib import Path

from typer.testing import CliRunner

from repokit.cli import EXIT_INVALID_INPUT, EXIT_NOT_FOUND, EXIT_OK, app
from repokit.scaffold import ScaffoldOptions, scaffold_project

runner = CliRunner()


def _parse_json_output(output: str) -> dict:
    lines = [line for line in output.splitlines() if line.strip()]
    return json.loads(lines[-1])


def test_search_json_output_schema(tmp_path: Path):
    (tmp_path / "AGENTS.md").write_text("Use read-only access for redshift queries", encoding="utf-8")

    result = runner.invoke(
        app,
        ["search", "redshift read-only", "--scope", str(tmp_path), "--format", "json"],
    )

    assert result.exit_code == EXIT_OK
    payload = _parse_json_output(result.stdout)
    assert payload["ok"] is True
    assert payload["command"] == "search"
    assert payload["exit_code"] == EXIT_OK
    assert "hits" in payload["data"]
    assert payload["data"]["hits"][0]["path"].endswith("AGENTS.md")


def test_search_no_matches_returns_not_found(tmp_path: Path):
    (tmp_path / "README.md").write_text("General project overview", encoding="utf-8")

    result = runner.invoke(
        app,
        ["search", "redshift", "--scope", str(tmp_path), "--format", "json"],
    )

    assert result.exit_code == EXIT_NOT_FOUND
    payload = _parse_json_output(result.stdout)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "no_matches"
    assert payload["exit_code"] == EXIT_NOT_FOUND


def test_list_json_output_schema(tmp_path: Path):
    scaffold_project(
        ScaffoldOptions(
            project_name="Agent Repo",
            repo_type="agent",
            destination_root=tmp_path,
        )
    )

    result = runner.invoke(app, ["list", "--scope", str(tmp_path), "--format", "json"])

    assert result.exit_code == EXIT_OK
    payload = _parse_json_output(result.stdout)
    assert payload["ok"] is True
    assert payload["command"] == "list"
    assert len(payload["data"]["repositories"]) == 1
    assert payload["data"]["repositories"][0]["type"] == "agent"


def test_info_invalid_path_returns_invalid_input(tmp_path: Path):
    missing_repo = tmp_path / "missing"
    result = runner.invoke(app, ["info", str(missing_repo), "--format", "json"])

    assert result.exit_code == EXIT_INVALID_INPUT
    payload = _parse_json_output(result.stdout)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "invalid_repository_path"
    assert payload["exit_code"] == EXIT_INVALID_INPUT

