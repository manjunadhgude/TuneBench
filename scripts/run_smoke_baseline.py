"""Run and retain the first real-model check on the 20 reviewed smoke examples."""

import argparse
import hashlib
import json
import resource
import shutil
import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path

from tunebench.evaluator import evaluate
from tunebench.inference import run_inference
from tunebench.io import read_jsonl, write_json, write_jsonl


def verify_snapshot(snapshot: Path) -> dict:
    manifest = json.loads((snapshot / "download-manifest.json").read_text())
    for name, asset in manifest["files"].items():
        if Path(name).name != name:
            raise ValueError("Snapshot manifest must contain only filenames")
        path = snapshot / name
        if path.stat().st_size != asset["size"]:
            raise ValueError(f"Model asset size mismatch: {name}")
        if asset["hash_algorithm"] == "sha256":
            digest = hashlib.sha256()
        elif asset["hash_algorithm"] == "git-blob-sha1":
            digest = hashlib.sha1()
            digest.update(f"blob {asset['size']}\0".encode())
        else:
            raise ValueError(f"Unsupported hash algorithm for {name}")
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(4 * 1024 * 1024), b""):
                digest.update(chunk)
        if digest.hexdigest() != asset["upstream_hash"]:
            raise ValueError(f"Model asset content mismatch: {name}")
    if "model.safetensors" not in manifest["files"]:
        raise ValueError("Snapshot has no verified model weights")
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--tasks", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    tasks = read_jsonl(args.tasks)
    if len(tasks) != 20 or any(task["split"] != "smoke" for task in tasks):
        raise ValueError("This check requires exactly 20 smoke records; test data is refused")
    if args.output.exists() and any(args.output.iterdir()):
        raise ValueError("Choose a new output directory; existing results are preserved")
    print("Verifying the pinned model snapshot...", flush=True)
    manifest = verify_snapshot(args.snapshot)

    import torch
    from transformers import set_seed

    torch.set_num_threads(4)
    torch.set_num_interop_threads(1)
    set_seed(42)
    args.output.mkdir(parents=True, exist_ok=True)
    source_bytes = args.tasks.read_bytes()
    (args.output / "smoke.jsonl").write_bytes(source_bytes)
    started = datetime.now(UTC).isoformat()
    start = time.perf_counter()
    print("Running actual Qwen inference on 20 smoke examples, CPU float32...", flush=True)
    predictions, metadata = run_inference(
        tasks,
        model_id=str(args.snapshot),
        prompt_style="strong",
        max_new_tokens=256,
        device="cpu",
    )
    metadata.update(
        {
            "model_id": manifest["model_id"],
            "resolved_model_revision": manifest["revision"],
            "local_snapshot_directory": str(args.snapshot),
            "weights_sha256": manifest["files"]["model.safetensors"]["upstream_hash"],
            "artifact_verification": "Upstream weight SHA-256 and support-file Git blob hashes",
            "tasks_sha256": hashlib.sha256(source_bytes).hexdigest(),
            "source_commit": subprocess.check_output(
                ["git", "rev-parse", "HEAD"], text=True
            ).strip(),
            "started_at_utc": started,
            "completed_at_utc": datetime.now(UTC).isoformat(),
            "elapsed_seconds": time.perf_counter() - start,
            "cpu_peak_rss_bytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024,
            "cpu_threads": torch.get_num_threads(),
            "cpu_interop_threads": torch.get_num_interop_threads(),
            "model_dtype": "float32",
            "seed": 42,
            "model_fine_tuned": False,
            "engineering_smoke_only": True,
            "runner_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        }
    )
    predictions_path = args.output / "strong.predictions.jsonl"
    write_jsonl(predictions_path, predictions)
    write_json(str(predictions_path) + ".metadata.json", metadata)
    shutil.copyfile(
        args.snapshot / "download-manifest.json", args.output / "download-manifest.json"
    )
    report = evaluate(tasks, predictions)
    report["gold_sha256"] = hashlib.sha256(
        json.dumps(tasks, sort_keys=True, allow_nan=False).encode()
    ).hexdigest()
    report["inference_metadata"] = metadata
    write_json(args.output / "report.json", report)
    print(
        json.dumps(
            {
                "examples": report["total_examples"],
                "task_success": report["task_success"],
                "outcome_accuracy": report["outcome_accuracy"],
                "invalid_predictions": report["invalid_predictions"],
                "elapsed_seconds": metadata["elapsed_seconds"],
                "output": str(args.output),
            },
            indent=2,
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
