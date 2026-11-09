"""Freeze and evaluate one portfolio dataset with a rules or local-model backend.

This runner scores decisions only. Simulated business-policy execution is tested
separately, because benchmark order identifiers need not exist in the demo store.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import random
import subprocess
import time
from collections import Counter
from collections.abc import Callable
from copy import deepcopy
from datetime import UTC, datetime
from importlib import metadata as package_metadata
from pathlib import Path
from typing import Any

from tunebench import __version__
from tunebench.contracts import load_tool_registry, validate_task
from tunebench.evaluator import evaluate
from tunebench.grounding import POLICY_VERSION
from tunebench.inference import build_messages
from tunebench.io import parse_json, read_jsonl, write_json, write_jsonl
from tunebench.structured import generation_schema

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROTOCOL_VERSION = "portfolio-decision-evaluation-v3"
LABELS = {
    "rules": "Deterministic rules baseline (not an LLM)",
    "model": "Local Qwen with validation and bounded repair",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(4 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _json_hash(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False).encode()
    ).hexdigest()


def _validate_tasks(tasks: list[dict[str, Any]]) -> None:
    if not tasks:
        raise ValueError("The evaluation dataset must not be empty")
    identifiers = [task.get("example_id") for task in tasks]
    if len(set(identifiers)) != len(identifiers):
        raise ValueError("Evaluation example IDs must be unique")
    registry = load_tool_registry()
    for task in tasks:
        errors = validate_task(task)
        if errors:
            raise ValueError(f"Invalid task {task.get('example_id')}: {'; '.join(errors)}")
        if task["tools"] != registry:
            raise ValueError("Assistant evaluation requires the canonical demo tool registry")


def _prediction(task: dict[str, Any], outcome: Any, **fields: Any) -> dict[str, Any]:
    return {"example_id": task["example_id"], "outcome": deepcopy(outcome), **fields}


def collect_cases(
    tasks: list[dict[str, Any]],
    responder: Callable[..., dict[str, Any]],
    *,
    backend: str,
    model_path: Path | None = None,
    max_repairs: int = 1,
    checkpoint: Callable[[dict[str, Any]], None] | None = None,
) -> dict[str, Any]:
    """Keep original attempts and accepted decisions, including every failed case.

    A responder test double can exercise accounting without loading a model.
    Checkpoint failures deliberately abort instead of silently losing evidence.
    """
    _validate_tasks(tasks)
    raw_predictions, final_predictions, cases = [], [], []
    for task in tasks:
        started = time.perf_counter()
        try:
            result = responder(
                task["prompt"],
                backend=backend,
                model_path=str(model_path) if model_path else None,
                max_repairs=max_repairs,
                execute_tools=False,
            )
            if not isinstance(result, dict):
                raise ValueError("Assistant response must be an object")
            if result.get("backend") != backend:
                raise ValueError("Assistant backend differs from the requested evaluation backend")
        except Exception as exc:
            result = {
                "backend": backend,
                "status": "error",
                "outcome": None,
                "accepted_outcome": None,
                "attempts": [],
                "validation_errors": [],
                "tool_result": None,
                "runtime_error": {"type": type(exc).__name__, "message": str(exc)},
                "elapsed_ms": (time.perf_counter() - started) * 1000,
            }
        attempts = result.get("attempts") or []
        first = attempts[0] if attempts else {}
        raw = _prediction(
            task,
            first.get("parsed_outcome"),
            raw_output=first.get("raw_output", ""),
            metadata={"stage": "first_attempt", "backend": backend},
        )
        # Blocked parsed proposals are retained in the case trace, not accepted
        # as product decisions. Do not substitute the last raw outcome here.
        accepted = result.get("accepted_outcome")
        if result.get("status") in {"blocked", "error"}:
            accepted = None
        final = _prediction(
            task,
            accepted,
            metadata={"stage": "accepted_final_decision", "backend": backend},
        )
        case = {
            "example_id": task["example_id"],
            "response": deepcopy(result),
            "raw_first_prediction": raw,
            "final_prediction": final,
        }
        raw_predictions.append(raw)
        final_predictions.append(final)
        cases.append(case)
        if checkpoint is not None:
            checkpoint(deepcopy(case))

    raw_report = evaluate(tasks, raw_predictions)
    final_report = evaluate(tasks, final_predictions)
    statuses = Counter(case["response"].get("status", "unknown") for case in cases)
    attempts_per_case = [len(case["response"].get("attempts") or []) for case in cases]
    return {
        "cases": cases,
        "raw_predictions": raw_predictions,
        "final_predictions": final_predictions,
        "raw_report": raw_report,
        "final_report": final_report,
        "pipeline": {
            "status_counts": dict(sorted(statuses.items())),
            "accepted_decisions": sum(
                record["outcome"] is not None for record in final_predictions
            ),
            "cases_with_repair": sum(count > 1 for count in attempts_per_case),
            "repair_attempts": sum(max(0, count - 1) for count in attempts_per_case),
            "generation_attempts": sum(attempts_per_case) if backend == "model" else 0,
            "runtime_error_cases": statuses.get("error", 0),
            "tool_execution_enabled": False,
            "tool_results_returned": sum(
                case["response"].get("tool_result") is not None for case in cases
            ),
            "execution_safety_evidence": (
                "Not measured here: decision-only evaluation disables tool execution. "
                "See guard and mock-tool integration tests for execution-policy checks."
            ),
        },
    }


def _sources() -> list[Path]:
    return sorted(
        {
            Path(__file__).resolve(),
            PROJECT_ROOT / "pyproject.toml",
            *PROJECT_ROOT.joinpath("src/tunebench").rglob("*.py"),
            *PROJECT_ROOT.joinpath("src/tunebench/resources").rglob("*.json"),
        }
    )


def _versions() -> dict[str, str | None]:
    versions: dict[str, str | None] = {"python": platform.python_version()}
    for name in (
        "tunebench",
        "jsonschema",
        "torch",
        "transformers",
        "accelerate",
        "lm-format-enforcer",
        "interegular",
    ):
        try:
            versions[name] = package_metadata.version(name)
        except package_metadata.PackageNotFoundError:
            versions[name] = None
    return versions


def _manifest_for(data: Path, tasks: list[dict[str, Any]]) -> tuple[Path | None, dict | None]:
    path = data.parent / "manifest.json"
    if not path.is_file():
        if any(task["split"] == "test" for task in tasks):
            raise ValueError("Held-out evaluation requires a frozen sibling manifest.json")
        return None, None
    manifest = parse_json(path.read_text(encoding="utf-8"))
    entry = next(
        (
            item
            for item in manifest.get("files", {}).values()
            if (path.parent / item.get("path", "")).resolve() == data.resolve()
        ),
        None,
    )
    if entry is None or entry.get("sha256") != sha256(data):
        raise ValueError("Dataset does not match its frozen manifest checksum")
    if entry.get("examples") != len(tasks) or entry.get("bytes") != data.stat().st_size:
        raise ValueError("Dataset count or size does not match its frozen manifest")
    return path, manifest


def _git(*args: str) -> str | None:
    try:
        return subprocess.check_output(
            ["git", "-C", str(PROJECT_ROOT), *args], text=True, stderr=subprocess.DEVNULL
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def run_evaluation(
    data: Path, outputdir: Path, *, backend: str, model_path: Path | None, max_repairs: int
) -> dict[str, Any]:
    """Create a fresh auditable run. No resume, overwrite, or automatic rerun."""
    if backend not in LABELS or max_repairs not in {0, 1}:
        raise ValueError("Choose rules/model and a bounded max_repairs of zero or one")
    data = data.expanduser().resolve()
    outputdir = outputdir.expanduser().resolve()
    tasks = read_jsonl(data)
    _validate_tasks(tasks)
    dataset_manifest_path, dataset_manifest = _manifest_for(data, tasks)
    if outputdir.exists() and (not outputdir.is_dir() or any(outputdir.iterdir())):
        raise ValueError("Choose a fresh output directory; existing run evidence is preserved")
    manifest = None
    if backend == "model":
        if model_path is None:
            raise ValueError("The model backend requires --model-path to a verified local snapshot")
        from tunebench.live_model import verify_local_snapshot

        model_path = model_path.expanduser().resolve()
        manifest = verify_local_snapshot(model_path)

    sources = _sources()
    source_hashes = {str(path.relative_to(PROJECT_ROOT)): sha256(path) for path in sources}
    # Rules never consume model messages. Retain exactly the model's first-turn
    # messages when using the live backend, including the current prompt version.
    messages = [build_messages(task, "strong-v3") for task in tasks] if backend == "model" else []
    outputdir.mkdir(parents=True, exist_ok=True)
    frozen_data = outputdir / "tasks.jsonl"
    frozen_data.write_bytes(data.read_bytes())
    if dataset_manifest_path:
        (outputdir / "dataset-manifest.json").write_bytes(dataset_manifest_path.read_bytes())
    write_json(outputdir / "first-attempt.messages.json", messages)
    protocol = {
        "protocol_version": PROTOCOL_VERSION,
        "status": "frozen_before_generation",
        "created_at_utc": datetime.now(UTC).isoformat(),
        "backend": backend,
        "backend_label": LABELS[backend],
        "examples": len(tasks),
        "example_ids_in_order": [task["example_id"] for task in tasks],
        "split_counts": dict(Counter(task["split"] for task in tasks)),
        "dataset_id": dataset_manifest.get("dataset_id") if dataset_manifest else None,
        "tasks_source_path": str(data),
        "tasks_sha256": sha256(frozen_data),
        "dataset_manifest_sha256": sha256(dataset_manifest_path) if dataset_manifest_path else None,
        "source_commit": _git("rev-parse", "HEAD"),
        "source_package_version": __version__,
        "source_worktree_dirty": bool(_git("status", "--porcelain")),
        "source_files_sha256": source_hashes,
        "prompt_style": "strong-v3" if backend == "model" else "rules-v3",
        "first_attempt_messages_sha256": _json_hash(messages),
        "structured_output": {
            "enabled": backend == "model",
            "library": "lm-format-enforcer" if backend == "model" else None,
            "schema_sha256": hashlib.sha256(
                json.dumps(generation_schema(), sort_keys=True).encode()
            ).hexdigest()
            if backend == "model"
            else None,
            "post_validation_required": True,
        },
        "execution_guard_policy": "evidence-grounding-v3",
        "non_execution_grounding_policy": "advisory_only_no_evidence_repair",
        "evidence_policy_version": POLICY_VERSION,
        "libraries": _versions(),
        "model_id": manifest["model_id"] if manifest else None,
        "resolved_model_revision": manifest["revision"] if manifest else None,
        "model_assets": manifest["files"] if manifest else None,
        "model_manifest_sha256": sha256(model_path / "download-manifest.json")
        if manifest
        else None,
        "device": "cpu" if manifest else None,
        "model_dtype": "float32" if manifest else None,
        "cpu_threads": 4 if manifest else None,
        "cpu_interop_threads": 1 if manifest else None,
        "seed": 42,
        "explicit_generation_overrides": (
            {"do_sample": False, "num_beams": 1, "max_new_tokens": 256, "repetition_penalty": 1.1}
            if manifest
            else None
        ),
        "inherited_generation_config": (
            parse_json((model_path / "generation_config.json").read_text()) if manifest else None
        ),
        "max_repairs": max_repairs,
        "retry_policy": (
            "At most one parse/schema or tool-call evidence repair; no output rewriting "
            "and no case reruns"
            if backend == "model"
            else "No generation or repair: deterministic rules baseline"
        ),
        "repair_policy": {
            "max_repairs": max_repairs if backend == "model" else 0,
            "triggers": ["parse_error", "schema_error", "tool_call_evidence_error"]
            if backend == "model"
            else [],
            "feedback": "Validation errors and evidence extracted only from the request",
            "grounding_failure": "bounded_repair_then_block"
            if backend == "model" and max_repairs
            else "block",
            "output_rewriting": False,
        },
        "execute_tools": False,
        "scoring": "Canonical exact decision, including all invalid/blocked/error cases",
        "holdout_policy": (
            "No prompt, policy, label, or model tuning after observing held-out outputs"
        ),
        "comparison_policy": "Rules are not LLM results; raw first output and guarded final differ",
    }
    protocol_path = outputdir / "protocol.json"
    write_json(protocol_path, protocol)
    protocol_hash = sha256(protocol_path)
    started = time.perf_counter()
    started_at = datetime.now(UTC).isoformat()
    journal = outputdir / "cases.partial.jsonl"
    journal.touch(exist_ok=False)
    captured: list[dict[str, Any]] = []

    def assert_frozen() -> None:
        if (
            sha256(frozen_data) != protocol["tasks_sha256"]
            or sha256(data) != protocol["tasks_sha256"]
        ):
            raise ValueError("Frozen evaluation data changed during the run")
        if sha256(protocol_path) != protocol_hash:
            raise ValueError("Frozen protocol changed during the run")
        if _sources() != sources:
            raise ValueError("Frozen source file list changed during the run")
        if any(
            sha256(path) != source_hashes[str(path.relative_to(PROJECT_ROOT))] for path in sources
        ):
            raise ValueError("Frozen source or policy changed during the run")
        if (
            dataset_manifest_path
            and sha256(dataset_manifest_path) != protocol["dataset_manifest_sha256"]
        ):
            raise ValueError("Frozen dataset manifest changed during the run")

    def checkpoint(case: dict[str, Any]) -> None:
        captured.append(case)
        with journal.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(case, ensure_ascii=False, allow_nan=False) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        print(
            f"{backend}: completed {len(captured)}/{len(tasks)} "
            f"in {time.perf_counter() - started:.1f}s ({case['response'].get('status')})",
            flush=True,
        )
        assert_frozen()
        if backend == "model" and case["response"].get("status") == "error":
            from tunebench.live_model import model_status

            if not model_status()["loaded"]:
                write_json(
                    outputdir / "run-status.json",
                    {
                        "status": "incomplete_backend_startup_failure",
                        "completed_cases": len(captured),
                        "expected_cases": len(tasks),
                        "quality_claims_validated": False,
                        "last_response": case["response"],
                    },
                )
                raise RuntimeError(
                    "Model session failed to become available; partial journal preserved, "
                    "no completed model-quality report produced"
                )

    # The protocol and exact first messages exist before any model initialization
    # or request. Local generation uses one cached session for every case/repair.
    random.seed(42)
    if backend == "model":
        import torch
        from transformers import set_seed

        torch.set_num_threads(4)
        try:
            torch.set_num_interop_threads(1)
        except RuntimeError:
            pass
        set_seed(42)
    from tunebench.assistant import respond

    assert_frozen()
    collected = collect_cases(
        tasks,
        respond,
        backend=backend,
        model_path=model_path,
        max_repairs=max_repairs,
        checkpoint=checkpoint,
    )
    assert_frozen()
    if collected["cases"] != captured or len(captured) != len(tasks):
        raise ValueError("Completed cases differ from the checkpoint journal")
    if collected["pipeline"]["tool_results_returned"]:
        raise ValueError("Decision-only evaluation unexpectedly returned executed tool results")
    runtime_metadata = None
    if backend == "model":
        from tunebench.live_model import model_status

        runtime_metadata = model_status()
    metadata = {
        "status": (
            "completed_with_runtime_errors"
            if collected["pipeline"]["runtime_error_cases"]
            else "completed"
        ),
        "backend": backend,
        "backend_label": LABELS[backend],
        "started_at_utc": started_at,
        "completed_at_utc": datetime.now(UTC).isoformat(),
        "elapsed_seconds": time.perf_counter() - started,
        "examples": len(tasks),
        "quality_claims_validated": not bool(collected["pipeline"]["runtime_error_cases"]),
        "protocol_sha256": protocol_hash,
        "tasks_sha256": protocol["tasks_sha256"],
        "model_runtime": runtime_metadata,
        "pipeline": collected["pipeline"],
    }
    for stage, key in (("raw-first", "raw"), ("final", "final")):
        write_jsonl(outputdir / f"{stage}.predictions.jsonl", collected[f"{key}_predictions"])
        report = collected[f"{key}_report"]
        report["gold_sha256"] = _json_hash(tasks)
        report["inference_metadata"] = {**metadata, "stage": stage}
        write_json(outputdir / f"{stage}.report.json", report)
    write_jsonl(outputdir / "cases.jsonl", captured)
    write_json(outputdir / "metadata.json", metadata)
    results = []
    stages = (("raw", "Qwen raw first attempt"), ("final", LABELS[backend]))
    for key, label in stages if backend == "model" else stages[1:]:
        report = collected[f"{key}_report"]
        results.append(
            {
                "label": label,
                "backend": backend,
                "examples": len(tasks),
                "strict_correct": report["task_success"]["correct"],
                "outcome_correct": report["outcome_accuracy"]["correct"],
                "valid_predictions": len(tasks) - report["invalid_predictions"],
            }
        )
    summary = {
        "title": "Frozen portfolio decision evaluation",
        "dataset_label": f"{protocol['dataset_id'] or data.name}: {len(tasks)} examples",
        "status": metadata["status"],
        "quality_claims_validated": metadata["quality_claims_validated"],
        "limitations": [
            "Small assistant-authored, assistant-reviewed fictional benchmark; no human review.",
            "Decision-only evaluation; simulated execution policy is checked separately.",
            "Raw first output and final guarded product decisions are separate results.",
            "No fine-tuning; rules baseline results are not LLM accuracy.",
            "Earlier smoke/development percentages use different data and are not comparable.",
        ],
        "results": results,
        "elapsed_seconds": metadata["elapsed_seconds"],
        "pipeline": collected["pipeline"],
        "protocol_sha256": protocol_hash,
    }
    write_json(outputdir / "summary.json", summary)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--outputdir", type=Path, required=True)
    parser.add_argument("--backend", choices=tuple(LABELS), required=True)
    parser.add_argument("--model-path", type=Path)
    parser.add_argument("--max-repairs", type=int, choices=(0, 1), default=1)
    args = parser.parse_args()
    summary = run_evaluation(
        args.data,
        args.outputdir,
        backend=args.backend,
        model_path=args.model_path,
        max_repairs=args.max_repairs,
    )
    print(json.dumps(summary, ensure_ascii=False, allow_nan=False), flush=True)


if __name__ == "__main__":
    main()
