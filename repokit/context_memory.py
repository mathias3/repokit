from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path

import yaml

CONTEXT_FILES = (
    "AGENTS.md",
    "PROJECT_RULES.md",
    "LEARNINGS.md",
    "CHANGELOG.md",
)


class ContextMode(str, Enum):
    copy = "copy"
    move = "move"


class ContextError(RuntimeError):
    pass


@dataclass(frozen=True)
class RepoContextStatus:
    repo_path: Path
    repo_type: str
    files_present: tuple[str, ...]
    files_missing: tuple[str, ...]


@dataclass(frozen=True)
class TransferReport:
    source: Path
    destination: Path
    mode: str
    copied: tuple[str, ...]
    moved: tuple[str, ...]
    skipped: tuple[str, ...]


@dataclass(frozen=True)
class CompressionReport:
    repo_path: Path
    file_path: Path
    threshold: int
    original_lines: int
    final_lines: int
    archived: bool
    archive_path: Path | None


def _load_repo_type(repo_path: Path) -> str:
    marker = repo_path / ".repokit.yml"
    if not marker.exists():
        return "?"
    data = yaml.safe_load(marker.read_text(encoding="utf-8")) or {}
    return str(data.get("type", "?")).strip() or "?"


def _validate_repo(repo_path: Path) -> Path:
    root = repo_path.resolve()
    if not root.exists() or not root.is_dir():
        raise ContextError(f"Repository path does not exist: {root}")
    marker = root / ".repokit.yml"
    if not marker.exists():
        raise ContextError(f"Missing .repokit.yml in repository: {root}")
    return root


def _context_file_set(files: tuple[str, ...] | None) -> tuple[str, ...]:
    if files is None:
        return CONTEXT_FILES

    normalized = tuple(sorted({item.strip() for item in files if item.strip()}))
    if not normalized:
        raise ContextError("At least one --file value must be provided when overriding defaults.")
    for item in normalized:
        if Path(item).is_absolute() or ".." in Path(item).parts:
            raise ContextError(f"Invalid context file path: {item}")
    return normalized


def inventory_context(scope: Path) -> tuple[RepoContextStatus, ...]:
    root = scope.resolve()
    if not root.exists() or not root.is_dir():
        raise ContextError(f"Scope path does not exist: {root}")

    rows: list[RepoContextStatus] = []
    for marker in root.rglob(".repokit.yml"):
        repo_path = marker.parent
        present = [name for name in CONTEXT_FILES if (repo_path / name).exists()]
        missing = [name for name in CONTEXT_FILES if not (repo_path / name).exists()]
        rows.append(
            RepoContextStatus(
                repo_path=repo_path,
                repo_type=_load_repo_type(repo_path),
                files_present=tuple(present),
                files_missing=tuple(missing),
            )
        )

    rows.sort(key=lambda item: str(item.repo_path))
    return tuple(rows)


def transfer_context(
    source_repo: Path,
    destination_repo: Path,
    mode: ContextMode,
    files: tuple[str, ...] | None = None,
) -> TransferReport:
    source = _validate_repo(source_repo)
    destination = _validate_repo(destination_repo)
    if source == destination:
        raise ContextError("Source and destination repositories must be different.")

    selected = _context_file_set(files)

    copied: list[str] = []
    moved: list[str] = []
    skipped: list[str] = []

    for relative in selected:
        src_path = source / relative
        dst_path = destination / relative

        if not src_path.exists():
            skipped.append(relative)
            continue

        dst_path.parent.mkdir(parents=True, exist_ok=True)
        content = src_path.read_text(encoding="utf-8")
        dst_path.write_text(content, encoding="utf-8")

        if mode == ContextMode.copy:
            copied.append(relative)
        else:
            src_path.unlink()
            moved.append(relative)

    return TransferReport(
        source=source,
        destination=destination,
        mode=mode.value,
        copied=tuple(copied),
        moved=tuple(moved),
        skipped=tuple(skipped),
    )


def compress_context_file(
    repo_path: Path,
    file_path: str,
    threshold: int = 200,
    keep_tail_lines: int = 80,
    header_lines: int = 12,
) -> CompressionReport:
    root = _validate_repo(repo_path)

    if threshold <= 0:
        raise ContextError("--threshold must be greater than 0.")
    if keep_tail_lines <= 0:
        raise ContextError("--keep-tail must be greater than 0.")
    if header_lines <= 0:
        raise ContextError("--header-lines must be greater than 0.")

    relative = file_path.strip()
    if not relative:
        raise ContextError("--file cannot be empty.")
    if Path(relative).is_absolute() or ".." in Path(relative).parts:
        raise ContextError(f"Invalid context file path: {relative}")

    target = root / relative
    if not target.exists() or not target.is_file():
        raise ContextError(f"Context file not found: {target}")

    lines = target.read_text(encoding="utf-8").splitlines()
    original_lines = len(lines)
    if original_lines <= threshold:
        return CompressionReport(
            repo_path=root,
            file_path=target,
            threshold=threshold,
            original_lines=original_lines,
            final_lines=original_lines,
            archived=False,
            archive_path=None,
        )

    head_count = min(header_lines, original_lines)
    tail_count = min(keep_tail_lines, max(0, original_lines - head_count))

    head = lines[:head_count]
    middle_end = original_lines - tail_count
    middle = lines[head_count:middle_end]
    tail = lines[middle_end:]

    now = datetime.now(timezone.utc)
    archive_dir = root / "memory" / "archive"
    archive_dir.mkdir(parents=True, exist_ok=True)
    archive_path = archive_dir / f"{Path(relative).stem}-{now.strftime('%Y%m%d-%H%M%S')}.md"

    archive_content = "\n".join(middle).rstrip() + "\n"
    archive_path.write_text(archive_content, encoding="utf-8")

    compression_note = [
        "",
        "## Compression Note",
        f"- Compressed on {now.date().isoformat()}.",
        f"- Archived {len(middle)} lines to `{archive_path.relative_to(root)}`.",
        "- Promote repeated rules from archived notes into PROJECT_RULES.md or AGENTS.md.",
        "",
    ]

    compressed_lines = head + compression_note + tail
    target.write_text("\n".join(compressed_lines).rstrip() + "\n", encoding="utf-8")

    return CompressionReport(
        repo_path=root,
        file_path=target,
        threshold=threshold,
        original_lines=original_lines,
        final_lines=len(compressed_lines),
        archived=True,
        archive_path=archive_path,
    )
