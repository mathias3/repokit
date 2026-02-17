from pathlib import Path

from repokit.scaffold import ScaffoldOptions, scaffold_project
from repokit.sync import analyze_sync


def test_sync_detects_missing_expected_file(tmp_path: Path):
    repo = scaffold_project(
        ScaffoldOptions(
            project_name="Agent Repo",
            repo_type="agent",
            destination_root=tmp_path,
        )
    )

    (repo / "DATA_CONTRACTS.md").unlink()

    report = analyze_sync(repo)

    assert "DATA_CONTRACTS.md" in report.missing
    assert report.repo_type == "agent"


def test_sync_detects_unexpected_file_for_repo_type(tmp_path: Path):
    repo = scaffold_project(
        ScaffoldOptions(
            project_name="Agent Repo",
            repo_type="agent",
            destination_root=tmp_path,
        )
    )

    (repo / "MODEL_CARD.md").write_text("# MODEL_CARD\n", encoding="utf-8")

    report = analyze_sync(repo)

    assert "MODEL_CARD.md" in report.unexpected
