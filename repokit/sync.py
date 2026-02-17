from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

from .config import REPO_TYPES, templates_root


@dataclass(frozen=True)
class SyncReport:
    repo_type: str
    missing: tuple[str, ...]
    unexpected: tuple[str, ...]


class SyncError(RuntimeError):
    pass


def _load_repo_type(repo_path: Path, repo_type: str | None) -> str:
    if repo_type:
        if repo_type not in REPO_TYPES:
            raise SyncError(f"Unsupported repo type: {repo_type}")
        return repo_type

    marker = repo_path / ".repokit.yml"
    if not marker.exists():
        raise SyncError("Missing .repokit.yml. Pass --type explicitly.")

    data = yaml.safe_load(marker.read_text(encoding="utf-8")) or {}
    detected = str(data.get("type", "")).strip()
    if detected not in REPO_TYPES:
        raise SyncError(f"Could not detect valid repo type from {marker}")
    return detected


def _expected_files(repo_type: str) -> set[str]:
    expected: set[str] = set()
    root = templates_root()

    for scope in ("_shared", repo_type):
        scope_root = root / scope
        if not scope_root.exists():
            continue

        for file_path in scope_root.rglob("*.j2"):
            relative = file_path.relative_to(scope_root)
            expected.add(str(Path(str(relative)[:-3])))

    return expected


def _canonical_files_union() -> set[str]:
    union: set[str] = set()
    for candidate in REPO_TYPES:
        union.update(_expected_files(candidate))
    return union


def analyze_sync(repo_path: Path, repo_type: str | None = None) -> SyncReport:
    root = repo_path.resolve()
    if not root.exists() or not root.is_dir():
        raise SyncError(f"Repository path does not exist: {root}")

    resolved_type = _load_repo_type(root, repo_type)
    expected = _expected_files(resolved_type)

    missing = sorted(path for path in expected if not (root / path).exists())

    # Unexpected means files that belong to some scaffold template but not to this repo type.
    all_canonical = _canonical_files_union()
    unexpected = sorted(path for path in (all_canonical - expected) if (root / path).exists())

    return SyncReport(
        repo_type=resolved_type,
        missing=tuple(missing),
        unexpected=tuple(unexpected),
    )
