#!/usr/bin/env bash
set -euo pipefail

REPO_PATH="${1:?Provide repo path}"
OUT_DIR="${2:-./out/scaffold-check}"

mkdir -p "$OUT_DIR"

echo "[1/2] Collecting layer status..."
repokit info "$REPO_PATH" --format json > "$OUT_DIR/info.json"

echo "[2/2] Checking scaffold drift..."
repokit sync "$REPO_PATH" --format json > "$OUT_DIR/sync.json"

echo "Done. Artifacts:"
echo "- $OUT_DIR/info.json"
echo "- $OUT_DIR/sync.json"
