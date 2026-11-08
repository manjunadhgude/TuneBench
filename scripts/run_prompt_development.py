"""Freeze and run a paired CPU comparison of legacy and revised prompts on development data."""

import argparse
import hashlib
import json
import resource
import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path

from run_smoke_baseline import verify_snapshot

from tunebench.comparison import assert_prompt_comparison_conditions, compare_reports
from tunebench.contracts import validate_task
from tunebench.evaluator import evaluate
from tunebench.inference import build_messages, run_inference
from tunebench.io import read_jsonl, write_json, write_jsonl


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--tasks", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    tasks = read_jsonl(args.tasks)
    if not tasks or any(task.get("split") != "validation" for task in tasks):
        raise ValueError("This development run accepts validation records only")
    if len({task["example_id"] for task in tasks}) != len(tasks):
        raise ValueError("Development example IDs must be unique")
    for task in tasks:
        errors = validate_task(task)
        if errors:
            raise ValueError(f"Invalid development task: {errors}")
    if args.output.exists() and any(args.output.iterdir()):
        raise ValueError("Choose a new output directory; existing runs are preserved")
    manifest = verify_snapshot(args.snapshot)
    project_root = Path(__file__).resolve().parents[1]
    sources = [
        Path(__file__),
        project_root / "src/tunebench/inference.py",
        project_root / "src/tunebench/contracts.py",
        project_root / "src/tunebench/evaluator.py",
        project_root / "src/tunebench/comparison.py",
    ]
    source_hashes = {str(path.relative_to(project_root)): sha256(path) for path in sources}
    styles = ("strong", "strong-v2")
    args.output.mkdir(parents=True, exist_ok=True)
    frozen_tasks = args.output / "development.jsonl"
    frozen_tasks.write_bytes(args.tasks.read_bytes())
    tasks_hash = sha256(frozen_tasks)
    prompt_hashes = {}
    for style in styles:
        systems = [build_messages(task, style)[0] for task in tasks]
        prompt_hashes[style] = hashlib.sha256(
            json.dumps(systems, sort_keys=True, allow_nan=False).encode()
        ).hexdigest()
        write_json(args.output / f"{style}.system-messages.json", systems)
    protocol = {
        "status": "frozen_before_generation",
        "created_at_utc": datetime.now(UTC).isoformat(),
        "styles_in_order": styles,
        "examples": len(tasks),
        "tasks_sha256": tasks_hash,
        "source_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
        "source_files_sha256": source_hashes,
        "system_messages_sha256": prompt_hashes,
        "model_id": manifest["model_id"],
        "revision": manifest["revision"],
        "model_assets": manifest["files"],
        "device": "cpu",
        "model_dtype": "float32",
        "cpu_threads": 4,
        "cpu_interop_threads": 1,
        "seed": 42,
        "explicit_generation_overrides": {
            "do_sample": False,
            "num_beams": 1,
            "max_new_tokens": 256,
        },
        "inherited_generation_config": json.loads(
            (args.snapshot / "generation_config.json").read_text()
        ),
        "retry_policy": "none",
        "purpose": "paired_development_prompt_ablation_not_final_test",
        "notes": [
            "Do not compare percentages directly with the different 20-example smoke set.",
            "Only prompt changes are permitted; no revisions after seeing run outputs.",
        ],
    }
    write_json(args.output / "protocol.json", protocol)

    import torch
    from transformers import set_seed

    torch.set_num_threads(4)
    torch.set_num_interop_threads(1)
    reports = []
    for style in styles:
        if sha256(frozen_tasks) != tasks_hash or any(
            sha256(path) != source_hashes[str(path.relative_to(project_root))] for path in sources
        ):
            raise ValueError("Frozen inputs or source changed during the experiment")
        directory = args.output / style
        directory.mkdir()
        journal = directory / "predictions.partial.jsonl"
        captured = []
        started = datetime.now(UTC).isoformat()
        start = time.perf_counter()

        def on_prediction(record, *, captured=captured, journal=journal, style=style, start=start):
            captured.append(record)
            with journal.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(record, ensure_ascii=False, allow_nan=False) + "\n")
            print(
                f"{style}: completed {len(captured)}/{len(tasks)} "
                f"in {time.perf_counter() - start:.1f}s",
                flush=True,
            )

        set_seed(42)
        predictions, metadata = run_inference(
            tasks,
            model_id=str(args.snapshot),
            prompt_style=style,
            max_new_tokens=256,
            device="cpu",
            on_prediction=on_prediction,
        )
        if predictions != captured or len(predictions) != len(tasks):
            raise ValueError("The complete prediction list differs from the checkpoint journal")
        metadata.update(
            {
                "model_id": manifest["model_id"],
                "resolved_model_revision": manifest["revision"],
                "weights_sha256": manifest["files"]["model.safetensors"]["upstream_hash"],
                "support_file_hashes": {
                    name: asset["upstream_hash"]
                    for name, asset in manifest["files"].items()
                    if name != "model.safetensors"
                },
                "tasks_sha256": tasks_hash,
                "model_dtype": "float32",
                "cpu_threads": 4,
                "cpu_interop_threads": 1,
                "seed": 42,
                "started_at_utc": started,
                "completed_at_utc": datetime.now(UTC).isoformat(),
                "elapsed_seconds": time.perf_counter() - start,
                "process_peak_rss_bytes_so_far": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
                * 1024,
                "protocol_sha256": sha256(args.output / "protocol.json"),
            }
        )
        write_jsonl(directory / "predictions.jsonl", predictions)
        write_json(directory / "predictions.jsonl.metadata.json", metadata)
        report = evaluate(tasks, predictions)
        report["gold_sha256"] = hashlib.sha256(
            json.dumps(tasks, sort_keys=True, allow_nan=False).encode()
        ).hexdigest()
        report["inference_metadata"] = metadata
        write_json(directory / "report.json", report)
        reports.append(report)
    assert_prompt_comparison_conditions(
        reports[0]["inference_metadata"], reports[1]["inference_metadata"]
    )
    comparison = compare_reports(*reports, allow_unmatched=True)
    comparison["protocol_sha256"] = sha256(args.output / "protocol.json")
    comparison["non_prompt_conditions_verified_equal"] = True
    write_json(args.output / "comparison.json", comparison)
    print(
        json.dumps(
            {
                "baseline": reports[0]["task_success"],
                "revised": reports[1]["task_success"],
                "output": str(args.output),
            },
            indent=2,
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
