from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

import yaml
from jinja2 import Environment, FileSystemLoader, StrictUndefined

from .config import DEFAULT_TOOLS, REPO_TYPES, templates_root


@dataclass(frozen=True)
class ScaffoldOptions:
    project_name: str
    repo_type: str
    destination_root: Path
    db_type: str = "redshift"
    tools: tuple[str, ...] = DEFAULT_TOOLS
    author: str = ""
    force: bool = False


class ScaffoldError(RuntimeError):
    pass


def _slugify(value: str) -> str:
    return "-".join(value.strip().lower().replace("_", " ").split())


def _iter_template_files(base: Path) -> Iterable[Path]:
    if not base.exists():
        return []
    return sorted(path for path in base.rglob("*.j2") if path.is_file())


def scaffold_project(options: ScaffoldOptions) -> Path:
    if options.repo_type not in REPO_TYPES:
        raise ScaffoldError(f"Unsupported repo type: {options.repo_type}")

    project_slug = _slugify(options.project_name)
    target_dir = options.destination_root / project_slug

    if target_dir.exists() and not options.force:
        raise ScaffoldError(f"Target path already exists: {target_dir}")

    target_dir.mkdir(parents=True, exist_ok=True)

    env = Environment(
        loader=FileSystemLoader(str(templates_root())),
        undefined=StrictUndefined,
        autoescape=False,
        trim_blocks=True,
        lstrip_blocks=True,
    )

    context = {
        "project_name": options.project_name,
        "project_slug": project_slug,
        "repo_type": options.repo_type,
        "db_type": options.db_type,
        "author": options.author or "unknown",
        "date": datetime.now(timezone.utc).date().isoformat(),
        "tools": list(options.tools),
    }

    for scope in ("_shared", options.repo_type):
        source_root = templates_root() / scope
        for template_path in _iter_template_files(source_root):
            relative_from_scope = template_path.relative_to(source_root)
            destination_relative = Path(str(relative_from_scope)[:-3])
            destination_file = target_dir / destination_relative
            destination_file.parent.mkdir(parents=True, exist_ok=True)

            template_name = str(template_path.relative_to(templates_root()))
            rendered = env.get_template(template_name).render(**context)
            destination_file.write_text(rendered + ("\n" if not rendered.endswith("\n") else ""), encoding="utf-8")

    metadata = {
        "name": options.project_name,
        "slug": project_slug,
        "type": options.repo_type,
        "db_type": options.db_type,
        "tools": list(options.tools),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    (target_dir / ".repokit.yml").write_text(yaml.safe_dump(metadata, sort_keys=False), encoding="utf-8")

    for directory in ("epics", "temp", "notebooks"):
        (target_dir / directory).mkdir(exist_ok=True)

    return target_dir
