"""Small frozen, paired CPU regression check; not a broad accuracy benchmark."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
import subprocess
import sys
from pathlib import Path


def digest(path):
    with Path(path).open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def sources(root):
    root = Path(root)
    return {
        str(p.relative_to(root)): digest(p)
        for p in sorted(
            [
                root / "pyproject.toml",
                *root.joinpath("src/tunebench").rglob("*.py"),
                *root.joinpath("src/tunebench/resources").rglob("*.json"),
            ]
        )
    }


def libraries():
    return {
        name: importlib.metadata.version(name)
        for name in ["tunebench", "llama-cpp-python", "jsonschema", "numpy"]
    }


def write(path, obj):
    Path(path).write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n")


def verify(protocol, output):
    assert libraries() == protocol["libraries"], "Runtime changed"
    assert digest(__file__) == protocol["runner_sha256"], "Runner changed"
    for name, root in protocol["roots"].items():
        assert sources(root) == protocol["sources"][name], "Source changed"
    assert digest(protocol["data"]) == protocol["data_sha256"], "Data changed"
    assert digest(output / "tasks.jsonl") == protocol["data_sha256"], "Retained data changed"


def worker(args):
    output = args.output.resolve()
    p = json.loads((output / "protocol.json").read_text())
    root = Path(p["roots"][args.worker])
    sys.path.insert(0, str(root / "src"))
    import tunebench
    from tunebench.assistant import respond
    from tunebench.contracts import validate_task
    from tunebench.evaluator import evaluate
    from tunebench.inference import parse_output

    assert Path(tunebench.__file__).resolve() == root / "src/tunebench/__init__.py"
    tasks = [json.loads(line) for line in (output / "tasks.jsonl").read_text().splitlines()]
    assert all(not validate_task(t) for t in tasks)
    directory = output / args.worker
    directory.mkdir()
    rows, first, final = [], [], []
    with (directory / "cases.jsonl").open("x") as journal:
        for t in tasks:
            verify(p, output)
            write(directory / "inflight.json", {"example_id": t["example_id"]})
            r = respond(t["prompt"], backend="model", model_path=p["model"], execute_tools=False)
            assert r["backend"] == "model" and r["tool_result"] is None
            for attempt in r["attempts"]:
                assert (
                    parse_output(t["example_id"], attempt["raw_output"])["outcome"]
                    == attempt["parsed_outcome"]
                )
            if r["accepted_outcome"] is not None:
                assert r["accepted_outcome"] == r["attempts"][-1]["parsed_outcome"]
            if args.worker == "candidate":
                for i, attempt in enumerate(r["attempts"]):
                    if attempt["schema_valid"] and attempt["parsed_outcome"]["type"] != "tool_call":
                        assert i == len(r["attempts"]) - 1, "Non-executing decision was retried"
                        assert not any(
                            v["primary_attempt"] == i + 1 for v in r["semantic_verifications"]
                        )
                        assert r["accepted_outcome"] == attempt["parsed_outcome"]
            row = {"example_id": t["example_id"], "response": r}
            journal.write(json.dumps(row, ensure_ascii=False) + "\n")
            journal.flush()
            os.fsync(journal.fileno())
            rows.append(row)
            first.append(
                {
                    "example_id": t["example_id"],
                    "outcome": r["attempts"][0]["parsed_outcome"] if r["attempts"] else None,
                }
            )
            final.append({"example_id": t["example_id"], "outcome": r["accepted_outcome"]})
            (directory / "inflight.json").unlink()
            print(f"{args.worker}: {len(rows)}/{len(tasks)} {r['status']}", flush=True)
    verify(p, output)
    for stage, predictions in [("raw-first", first), ("final", final)]:
        write(directory / (stage + ".report.json"), evaluate(tasks, predictions))
    write(
        directory / "summary.json",
        {
            "source_version": tunebench.__version__,
            "examples": len(rows),
            "primary_generations": sum(len(c["response"]["attempts"]) for c in rows),
            "review_generations": sum(len(c["response"]["semantic_verifications"]) for c in rows),
            "active_seconds": sum(c["response"]["elapsed_ms"] for c in rows) / 1000,
            "runtime_errors": sum(c["response"]["status"] == "error" for c in rows),
            "review_escalations": [
                c["example_id"]
                for c in rows
                if c["response"]["attempts"]
                and c["response"]["attempts"][0]["schema_valid"]
                and c["response"]["attempts"][0]["parsed_outcome"]["type"] != "tool_call"
                and (c["response"]["accepted_outcome"] or {}).get("type") == "tool_call"
            ],
            "journal_sha256": digest(directory / "cases.jsonl"),
        },
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--legacy-root", type=Path)
    parser.add_argument("--candidate-root", type=Path)
    parser.add_argument("--data", type=Path)
    parser.add_argument("--model", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--worker", choices=["legacy", "candidate"], help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.worker:
        return worker(args)
    if not all([args.legacy_root, args.candidate_root, args.data, args.model]):
        parser.error("Both frozen roots, data and verified local GGUF are required")
    args.output.mkdir(parents=True, exist_ok=False)
    roots = {
        "legacy": str(args.legacy_root.resolve()),
        "candidate": str(args.candidate_root.resolve()),
    }
    maps = {v: sources(root) for v, root in roots.items()}
    allowed = {
        "pyproject.toml",
        "src/tunebench/__init__.py",
        "src/tunebench/assistant.py",
        "src/tunebench/resources/configs/project.json",
    }
    assert maps["legacy"].keys() == maps["candidate"].keys()
    assert all(
        maps["legacy"][key] == maps["candidate"][key]
        for key in maps["legacy"]
        if key not in allowed
    )
    data = args.data.read_bytes()
    tasks = [json.loads(line) for line in data.decode().splitlines()]
    assert len(tasks) == 12 and len({t["example_id"] for t in tasks}) == 12
    (args.output / "tasks.jsonl").write_bytes(data)
    protocol = {
        "purpose": (
            "Targeted reliability regression; small assistant-authored set; "
            "not representative accuracy"
        ),
        "roots": roots,
        "sources": maps,
        "data": str(args.data.resolve()),
        "data_sha256": digest(args.data),
        "runner_sha256": digest(__file__),
        "model": str(args.model.resolve()),
        "model_sha256": digest(args.model),
        "libraries": libraries(),
        "execute_tools": False,
        "examples": 12,
        "order": ["candidate", "legacy"],
        "max_primary_generations": 2,
        "max_review_generations": 2,
        "max_tokens_per_generation": 256,
    }
    write(args.output / "protocol.json", protocol)
    for version in protocol["order"]:
        verify(protocol, args.output)
        subprocess.run(
            [
                sys.executable,
                "-u",
                str(Path(__file__).resolve()),
                "--worker",
                version,
                "--output",
                str(args.output.resolve()),
            ],
            check=True,
            env={**os.environ, "HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1"},
        )
    verify(protocol, args.output)
    assert digest(args.model) == protocol["model_sha256"]
    write(args.output / "completed.json", {"status": "complete", "examples_per_version": 12})


if __name__ == "__main__":
    main()
