"""Commands for reproducible TuneBench experiments."""

import argparse
import hashlib
import importlib.metadata
import json
import platform
import shutil
import sys
from pathlib import Path

from tunebench.io import parse_json, read_jsonl, write_json, write_jsonl


def _fresh_directory(value: str) -> Path:
    directory = Path(value)
    if directory.exists() and any(directory.iterdir()):
        raise ValueError(f"Output directory is not empty: {directory}; choose a new directory")
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def _evaluate(gold, predictions):
    from tunebench.evaluator import evaluate

    report = evaluate(gold, predictions)
    report["gold_sha256"] = hashlib.sha256(
        json.dumps(gold, sort_keys=True, allow_nan=False).encode()
    ).hexdigest()
    return report


def _doctor():
    packages = {}
    for package in ("tunebench", "jsonschema", "torch", "transformers", "peft", "accelerate"):
        try:
            packages[package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            packages[package] = None
    return {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "packages": packages,
        "nvidia_smi_available": shutil.which("nvidia-smi") is not None,
        "note": "Package presence does not establish model availability or CUDA readiness.",
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="tunebench")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("doctor", help="Inspect tools without exposing environment variables")
    generate = commands.add_parser("generate", help="Generate synthetic candidate data")
    generate.add_argument("--output", required=True)
    generate.add_argument("--seed", type=int, default=42)
    generate.add_argument("--full", action="store_true", help="1250 candidates instead of 20 smoke")
    audit = commands.add_parser("audit", help="Validate records and cross-split leakage")
    audit.add_argument("--data-dir", required=True)
    evaluate = commands.add_parser("evaluate", help="Score prediction JSONL against gold")
    evaluate.add_argument("--gold", required=True)
    evaluate.add_argument("--predictions", required=True)
    evaluate.add_argument("--output", required=True)
    evaluate.add_argument(
        "--run-metadata", help="Inference metadata sidecar (auto-detected by default)"
    )
    compare = commands.add_parser("compare", help="Compare paired evaluation reports")
    compare.add_argument("--baseline", required=True)
    compare.add_argument("--candidate", required=True)
    compare.add_argument("--output", required=True)
    compare.add_argument("--seed", type=int, default=42)
    compare.add_argument(
        "--allow-unmatched", action="store_true", help="Intentional prompt ablation"
    )
    demo = commands.add_parser("demo", help="Test the pipeline with gold-derived fixtures, no LLM")
    demo.add_argument("--output", required=True)
    infer = commands.add_parser("infer", help="Run a real Transformers model (optional extras)")
    infer.add_argument("--tasks", required=True)
    infer.add_argument("--output", required=True)
    infer.add_argument("--model", default="Qwen/Qwen2.5-1.5B-Instruct")
    infer.add_argument(
        "--prompt-style", choices=["minimal", "strong", "strong-v2"], default="strong"
    )
    infer.add_argument("--device", default="cpu")
    infer.add_argument("--adapter")
    infer.add_argument("--max-new-tokens", type=int, default=256)
    infer.add_argument("--allow-test", action="store_true", help="Explicit final-test access")
    export = commands.add_parser("export-training", help="Export train/validation messages")
    export.add_argument("--data-dir", required=True)
    export.add_argument("--output", required=True)
    train = commands.add_parser("train", help="Run GPU LoRA fine-tuning (optional extras)")
    train.add_argument("--data-dir", required=True)
    train.add_argument("--output", required=True)
    train.add_argument("--model", default="Qwen/Qwen2.5-1.5B-Instruct")
    train.add_argument("--quantize", action="store_true", help="QLoRA; requires bitsandbytes")
    args = parser.parse_args(argv)
    try:
        result = _run(args)
    except (ValueError, OSError, ImportError, RuntimeError, KeyError) as exc:
        print(f"tunebench: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, allow_nan=False))
    return 0


def _run(args):
    if args.command == "doctor":
        return _doctor()
    if args.command == "generate":
        from tunebench.dataset import (
            GENERATOR_VERSION,
            audit_dataset,
            generate_dataset,
            generate_smoke,
        )

        splits = generate_dataset(args.seed) if args.full else {"smoke": generate_smoke(args.seed)}
        audit = audit_dataset(splits)
        directory = _fresh_directory(args.output)
        hashes = {}
        for split, records in splits.items():
            path = directory / f"{split}.jsonl"
            write_jsonl(path, records)
            hashes[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
        manifest = {
            "generator_version": GENERATOR_VERSION,
            "status": "synthetic_candidates_not_reviewed_not_frozen",
            "seed": args.seed,
            "files_sha256": hashes,
            "audit": audit,
        }
        write_json(directory / "manifest.json", manifest)
        return {"output": str(directory), "manifest": manifest}
    if args.command == "audit":
        from tunebench.dataset import audit_dataset

        directory = Path(args.data_dir)
        splits = {
            p.stem: read_jsonl(p)
            for p in sorted(directory.glob("*.jsonl"))
            if p.stem in {"smoke", "train", "validation", "test"}
        }
        if not splits:
            raise ValueError("No smoke/train/validation/test JSONL files found")
        manifest_path = directory / "manifest.json"
        if manifest_path.exists():
            manifest = parse_json(manifest_path.read_text())
            if not isinstance(manifest, dict) or not isinstance(manifest.get("files_sha256"), dict):
                raise ValueError("Manifest must be an object with a files_sha256 object")
            checksums = manifest["files_sha256"]
            if set(checksums) != {f"{name}.jsonl" for name in splits}:
                raise ValueError("Manifest filenames must match the dataset split files")
            for name, expected in checksums.items():
                if hashlib.sha256((directory / name).read_bytes()).hexdigest() != expected:
                    raise ValueError(f"Manifest checksum mismatch: {name}")
        return audit_dataset(splits)
    if args.command == "evaluate":
        report = _evaluate(read_jsonl(args.gold), read_jsonl(args.predictions))
        metadata_path = Path(args.run_metadata or args.predictions + ".metadata.json")
        if args.run_metadata or metadata_path.exists():
            metadata = parse_json(metadata_path.read_text())
            if not isinstance(metadata, dict):
                raise ValueError("Inference metadata must be a JSON object")
            expected_hash = metadata.get("tasks_sha256")
            if (
                expected_hash
                and expected_hash != hashlib.sha256(Path(args.gold).read_bytes()).hexdigest()
            ):
                raise ValueError("Inference metadata tasks checksum does not match the gold input")
            report["inference_metadata"] = metadata
        write_json(args.output, report)
        return {
            "examples": report["total_examples"],
            "output": args.output,
            "task_success": report["task_success"],
        }
    if args.command == "compare":
        from tunebench.comparison import compare_reports

        result = compare_reports(
            parse_json(Path(args.baseline).read_text()),
            parse_json(Path(args.candidate).read_text()),
            seed=args.seed,
            allow_unmatched=args.allow_unmatched,
        )
        write_json(args.output, result)
        return result
    if args.command == "demo":
        from tunebench.dataset import generate_smoke

        directory = _fresh_directory(args.output)
        tasks = generate_smoke()
        predictions = [
            {
                "example_id": t["example_id"],
                "outcome": {
                    **t["expected_outcome"],
                    **(
                        {"question": "Please provide the missing information."}
                        if t["expected_outcome"]["type"] == "clarification"
                        else {}
                    ),
                },
            }
            for t in tasks
        ]
        corrupted = [dict(p) for p in predictions]
        corrupted[0] = {"example_id": tasks[0]["example_id"], "outcome": None}
        corrupted.pop()
        write_jsonl(directory / "smoke.jsonl", tasks)
        write_jsonl(directory / "oracle-fixture.jsonl", predictions)
        write_jsonl(directory / "corrupted-fixture.jsonl", corrupted)
        oracle = _evaluate(tasks, predictions)
        flawed = _evaluate(tasks, corrupted)
        write_json(directory / "oracle-report.json", oracle)
        write_json(directory / "corrupted-report.json", flawed)
        if oracle["task_success"]["correct"] != 20 or flawed["task_success"]["correct"] != 18:
            raise ValueError("Pipeline fixture checks did not produce expected results")
        return {
            "fixture_only_not_model_results": True,
            "examples": 20,
            "oracle_correct": 20,
            "corrupted_correct": 18,
            "output": str(directory),
        }
    if args.command == "infer":
        from tunebench.inference import run_inference

        tasks = read_jsonl(args.tasks)
        if any(task["split"] == "test" for task in tasks) and not args.allow_test:
            raise ValueError("Use validation for tuning; final test access requires --allow-test")
        if Path(args.output).exists() or Path(args.output + ".metadata.json").exists():
            raise ValueError("Inference output already exists; choose a new path")
        predictions, metadata = run_inference(
            tasks,
            model_id=args.model,
            prompt_style=args.prompt_style,
            device=args.device,
            max_new_tokens=args.max_new_tokens,
            adapter=args.adapter,
        )
        metadata["tasks_sha256"] = hashlib.sha256(Path(args.tasks).read_bytes()).hexdigest()
        write_jsonl(args.output, predictions)
        write_json(args.output + ".metadata.json", metadata)
        return metadata
    if args.command in {"export-training", "train"}:
        from tunebench.training import export_training_data, train_lora

        directory = Path(args.data_dir)
        train = read_jsonl(directory / "train.jsonl")
        validation = read_jsonl(directory / "validation.jsonl")
        output = _fresh_directory(args.output)
        if args.command == "export-training":
            return export_training_data(train, validation, output)
        return train_lora(train, validation, output, model_id=args.model, quantize=args.quantize)
    raise ValueError(f"Unknown command: {args.command}")
