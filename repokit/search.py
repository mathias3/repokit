from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from .config import SKIP_DIRS

WORD_RE = re.compile(r"[a-zA-Z0-9_\-]+")


@dataclass(frozen=True)
class SearchHit:
    path: Path
    score: float
    line: int
    snippet: str


def _tokenize(text: str) -> list[str]:
    return [token.lower() for token in WORD_RE.findall(text)]


def _iter_markdown_files(scope: Path):
    for path in scope.rglob("*.md"):
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if path.is_file():
            yield path


def _best_line_snippet(content: str, query_tokens: list[str]) -> tuple[int, str]:
    lines = content.splitlines()
    if not lines:
        return 1, ""

    best_idx = 0
    best_score = -1
    for idx, line in enumerate(lines):
        lowered = line.lower()
        score = sum(1 for token in query_tokens if token in lowered)
        if score > best_score:
            best_score = score
            best_idx = idx

    snippet = lines[best_idx].strip()
    return best_idx + 1, snippet[:200]


def search_markdown(query: str, scope: Path, limit: int = 10) -> list[SearchHit]:
    query_tokens = _tokenize(query)
    if not query_tokens:
        return []

    files = list(_iter_markdown_files(scope))
    if not files:
        return []

    docs = []
    for path in files:
        content = path.read_text(encoding="utf-8", errors="ignore")
        docs.append((path, content))

    query_counter = Counter(query_tokens)

    hits: list[SearchHit] = []
    for path, content in docs:
        token_counter = Counter(_tokenize(content))
        if not token_counter:
            continue

        overlap = sum(min(token_counter[token], count) for token, count in query_counter.items())
        if overlap <= 0:
            continue

        doc_norm = sum(token_counter.values())
        score = overlap / (1 + doc_norm ** 0.5)

        if score <= 0:
            continue
        line, snippet = _best_line_snippet(content, query_tokens)
        hits.append(SearchHit(path=path, score=float(score), line=line, snippet=snippet))

    hits.sort(key=lambda hit: hit.score, reverse=True)
    return hits[:limit]
