#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
task_python="${TUNEBENCH_PYTHON:-.venv/bin/python}"
"$task_python" -m pytest -q
"$task_python" -m ruff check .
"$task_python" -m ruff format --check .
task_output="$(mktemp -d "${TMPDIR:-/tmp}/tunebench-check.XXXXXXXX")"
trap 'rm -rf "$task_output"' EXIT
"$task_python" -m tunebench demo --output "$task_output/demo"
"$task_python" -m tunebench generate --full --output "$task_output/data" > "$task_output/generate.json"
"$task_python" -m tunebench audit --data-dir "$task_output/data" > "$task_output/audit.json"
"$task_python" -m tunebench export-training --data-dir "$task_output/data" --output "$task_output/training"
echo "PASS: tests, lint, format, controlled scoring, 1250-candidate audit, training export."
