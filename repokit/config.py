from __future__ import annotations

from pathlib import Path

REPO_TYPES = ("agent", "ml", "data", "app", "automation")
DEFAULT_TOOLS = ("claude", "windsurf", "amp", "gemini")

LAYER_RULES = {
    "A_executive": ("AGENTS.md", "README.md"),
    "B_contracts": ("DATA_CONTRACTS.md", "MODEL_CARD.md", "PIPELINE.md", "prompts/README.md"),
    "C_planning": ("PRD.md", "CHANGELOG.md", "epics"),
    "D_scratch": ("temp", "notebooks"),
}

SKIP_DIRS = {".git", ".venv", "venv", "node_modules", "dist", "build", "__pycache__", ".mypy_cache", ".pytest_cache"}


def templates_root() -> Path:
    return Path(__file__).resolve().parent / "templates"
