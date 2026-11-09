"""Capture actual local-model development decisions; never an unseen test score."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from collections import Counter
from pathlib import Path

from tunebench.assistant import respond
from tunebench.contracts import validate_task
from tunebench.evaluator import evaluate


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--data", type=Path, default=Path("datasets/portfolio-v1/development.jsonl")
    )
    parser.add_argument("--model-path", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()
    tasks = [json.loads(line) for line in args.data.read_text().splitlines() if line.strip()]
    if any(task["split"] not in {"train", "validation"} or validate_task(task) for task in tasks):
        raise ValueError("Use valid development records only; test/smoke records are rejected")
    if args.limit is not None:
        if args.limit < 1:
            raise ValueError("limit must be positive")
        tasks = tasks[: args.limit]
    args.output.mkdir(parents=True, exist_ok=True)
    if any(args.output.iterdir()):
        raise ValueError("Choose a fresh output directory to preserve prior development captures")
    sources = [*Path("src/tunebench").rglob("*.py"), Path("pyproject.toml"), Path(__file__)]
    write_json(
        args.output / "protocol.json",
        {
            "purpose": "Development model selection; not an unseen quality estimate",
            "examples": len(tasks),
            "data_sha256": hashlib.sha256(args.data.read_bytes()).hexdigest(),
            "source_sha256": {
                str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in sources
            },
            "model_path": str(args.model_path.resolve()),
            "max_repairs": 1,
            "execute_tools": False,
        },
    )
    raw, final, cases = [], [], []
    with (args.output / "cases.jsonl").open("x") as handle:
        for index, task in enumerate(tasks, 1):
            result = respond(
                task["prompt"],
                backend="model",
                model_path=str(args.model_path),
                execute_tools=False,
                max_repairs=1,
            )
            cases.append({"example_id": task["example_id"], "response": result})
            handle.write(json.dumps(cases[-1], ensure_ascii=False) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
            first = result["attempts"][0] if result["attempts"] else {}
            raw.append({"example_id": task["example_id"], "outcome": first.get("parsed_outcome")})
            final.append({"example_id": task["example_id"], "outcome": result["accepted_outcome"]})
            print(f"{index}/{len(tasks)}: {result['status']}", flush=True)
            if result["status"] == "error":
                raise RuntimeError(result["user_message"])
    raw_report, final_report = evaluate(tasks, raw), evaluate(tasks, final)
    write_json(args.output / "raw-first.report.json", raw_report)
    write_json(args.output / "final.report.json", final_report)
    summary = {
        "purpose": "Development only; no claim of unseen accuracy",
        "examples": len(tasks),
        "raw_strict": raw_report["task_success"],
        "final_strict": final_report["task_success"],
        "statuses": dict(Counter(case["response"]["status"] for case in cases)),
        "generations": sum(len(case["response"]["attempts"]) for case in cases),
        "active_seconds": sum(case["response"]["elapsed_ms"] for case in cases) / 1000,
    }
    write_json(args.output / "summary.json", summary)
    print(json.dumps(summary), flush=True)


if __name__ == "__main__":
    main()
