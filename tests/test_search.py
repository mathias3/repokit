from pathlib import Path

from repokit.search import search_markdown


def test_search_returns_relevant_hits(tmp_path: Path):
    (tmp_path / "AGENTS.md").write_text("Use read-only access for redshift queries", encoding="utf-8")
    (tmp_path / "README.md").write_text("General project overview", encoding="utf-8")

    hits = search_markdown("redshift read-only", scope=tmp_path, limit=5)

    assert hits
    assert hits[0].path.name == "AGENTS.md"
    assert hits[0].score > 0
