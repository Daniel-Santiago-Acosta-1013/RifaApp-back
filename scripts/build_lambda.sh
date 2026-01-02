#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BUILD_DIR="$ROOT/lambda_dist"

if ! command -v poetry >/dev/null 2>&1; then
  echo "Poetry is required. Install it with: curl -sSL https://install.python-poetry.org | python3 -" >&2
  exit 1
fi

rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR"

poetry export -f requirements.txt --without-hashes -o "$BUILD_DIR/requirements.txt"
python3 -m pip install --upgrade -r "$BUILD_DIR/requirements.txt" -t "$BUILD_DIR"

cp -R "$ROOT/app" "$BUILD_DIR/app"
