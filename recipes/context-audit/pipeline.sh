#!/usr/bin/env bash
set -euo pipefail

SCOPE="${1:-.}"
OUT_DIR="${2:-./out/context-audit}"
QUERY="${3:-redshift safety}"

mkdir -p "$OUT_DIR"

echo "[1/2] Searching markdown context..."
repokit search "$QUERY" --scope "$SCOPE" --format json > "$OUT_DIR/search.json"

echo "[2/2] Listing repokit repositories..."
repokit list --scope "$SCOPE" --format json > "$OUT_DIR/repos.json"

echo "Done. Artifacts:"
echo "- $OUT_DIR/search.json"
echo "- $OUT_DIR/repos.json"
