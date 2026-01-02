#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BUILD_DIR="$ROOT/lambda_dist"
POETRY_BIN="${POETRY_BIN:-poetry}"

if [ -x "$POETRY_BIN" ]; then
  POETRY_CMD="$POETRY_BIN"
elif command -v "$POETRY_BIN" >/dev/null 2>&1; then
  POETRY_CMD="$(command -v "$POETRY_BIN")"
else
  echo "Poetry is required. Install it with: curl -sSL https://install.python-poetry.org | python3 -" >&2
  exit 1
fi

rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR"

"$POETRY_CMD" export -f requirements.txt --without-hashes -o "$BUILD_DIR/requirements.txt"

PIP_PLATFORM="${LAMBDA_PLATFORM:-manylinux2014_x86_64}"
PIP_PYTHON_VERSION="${LAMBDA_PYTHON_VERSION:-311}"
PIP_IMPLEMENTATION="${LAMBDA_PIP_IMPLEMENTATION:-cp}"
PIP_ABI="${LAMBDA_PIP_ABI:-cp311}"

python3 -m pip install --upgrade \
  --platform "$PIP_PLATFORM" \
  --python-version "$PIP_PYTHON_VERSION" \
  --implementation "$PIP_IMPLEMENTATION" \
  --abi "$PIP_ABI" \
  --only-binary=:all: \
  -r "$BUILD_DIR/requirements.txt" \
  -t "$BUILD_DIR"

cp -R "$ROOT/app" "$BUILD_DIR/app"
