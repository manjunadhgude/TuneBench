"""Strict JSON input and atomic, UTF-8 output."""

import json
import os
import tempfile
from pathlib import Path
from typing import Any


def _unique_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def _nonfinite(value: str) -> None:
    raise ValueError(f"Non-finite JSON number: {value}")


def parse_json(text: str) -> Any:
    return json.loads(text, object_pairs_hook=_unique_keys, parse_constant=_nonfinite)


def read_jsonl(path: str | Path) -> list[dict[str, Any]]:
    records = []
    path = Path(path)
    with path.open(encoding="utf-8") as handle:
        for number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                record = parse_json(line)
            except ValueError as exc:
                raise ValueError(f"{path}:{number}: {exc}") from exc
            if not isinstance(record, dict):
                raise ValueError(f"{path}:{number}: JSONL records must be objects")
            records.append(record)
    return records


def _atomic_write(path: str | Path, text: str) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(text)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def write_json(path: str | Path, value: Any) -> None:
    _atomic_write(path, json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n")


def write_jsonl(path: str | Path, records: list[dict[str, Any]]) -> None:
    _atomic_write(
        path,
        "".join(json.dumps(r, ensure_ascii=False, allow_nan=False) + "\n" for r in records),
    )
