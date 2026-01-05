#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BUILD_DIR="$ROOT/lambda_dist"
UV_BIN="${UV_BIN:-uv}"

if [ -x "$UV_BIN" ]; then
  UV_CMD="$UV_BIN"
elif command -v "$UV_BIN" >/dev/null 2>&1; then
  UV_CMD="$(command -v "$UV_BIN")"
elif [ -x "$HOME/.local/bin/uv" ]; then
  UV_CMD="$HOME/.local/bin/uv"
elif [ -x "$HOME/.cargo/bin/uv" ]; then
  UV_CMD="$HOME/.cargo/bin/uv"
else
  echo "uv is required. Install it with: curl -LsSf https://astral.sh/uv/install.sh | sh" >&2
  exit 1
fi

rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR"

"$UV_CMD" pip compile "$ROOT/pyproject.toml" -o "$BUILD_DIR/requirements.txt"

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
