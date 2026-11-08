#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
# Keep caches writable in managed environments whose home directory is read-only.
export UV_CACHE_DIR="${UV_CACHE_DIR:-$PWD/.cache/uv}"
if command -v uv >/dev/null 2>&1; then
  uv venv --allow-existing .venv
  uv pip install --python .venv/bin/python --require-hashes -r requirements-dev.lock
  uv pip install --python .venv/bin/python --no-deps -e .
else
  python3 -m venv .venv
  .venv/bin/python -m pip install --require-hashes -r requirements-dev.lock
  .venv/bin/python -m pip install --no-deps -e .
fi
.venv/bin/python -m tunebench doctor
