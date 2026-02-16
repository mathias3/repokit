from pathlib import Path

from repokit.scaffold import ScaffoldOptions, scaffold_project


def test_scaffold_creates_agent_repo(tmp_path: Path):
    target = scaffold_project(
        ScaffoldOptions(
            project_name="My Agent Repo",
            repo_type="agent",
            destination_root=tmp_path,
            db_type="redshift",
            author="tester",
        )
    )

    assert target.exists()
    assert (target / "AGENTS.md").exists()
    assert (target / "PRD.md").exists()
    assert (target / "DATA_CONTRACTS.md").exists()
    assert (target / "prompts" / "README.md").exists()
    assert (target / ".windsurf" / "rules" / "safety.md").exists()
    assert (target / ".repokit.yml").exists()


def test_scaffold_creates_ml_specific_files(tmp_path: Path):
    target = scaffold_project(
        ScaffoldOptions(
            project_name="ML Repo",
            repo_type="ml",
            destination_root=tmp_path,
            db_type="none",
        )
    )

    assert (target / "MODEL_CARD.md").exists()
    assert (target / "PIPELINE.md").exists()
    assert (target / "DATA_CONTRACTS.md").exists() is False
