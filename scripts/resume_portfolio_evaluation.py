"""Resume an interrupted frozen model evaluation without regenerating saved cases."""

from __future__ import annotations

import argparse
import fcntl
import importlib.util
import json
import math
import os
import random
import time
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from tunebench.contracts import validate_prediction
from tunebench.inference import build_messages, parse_output
from tunebench.io import parse_json, read_jsonl, write_json, write_jsonl

_SPEC = importlib.util.spec_from_file_location(
    "frozen_portfolio_evaluation", Path(__file__).with_name("evaluate_portfolio.py")
)
original = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(original)
PROJECT_ROOT = Path(__file__).resolve().parents[1]
COMPLETED_FILES = (
    "summary.json",
    "metadata.json",
    "cases.jsonl",
    "raw-first.report.json",
    "final.report.json",
    "raw-first.predictions.jsonl",
    "final.predictions.jsonl",
)


def _equal(left: Any, right: Any) -> bool:
    return original._json_hash(left) == original._json_hash(right)


def validate_journal(
    journal_bytes: bytes, tasks: list[dict[str, Any]], protocol: dict[str, Any]
) -> list[dict[str, Any]]:
    """Require complete newline records forming an exact, canonical task prefix."""
    if journal_bytes and not journal_bytes.endswith(b"\n"):
        raise ValueError("Journal has a truncated final record; refusing to repair or rerun it")
    lines = journal_bytes.decode("utf-8").splitlines()
    if any(not line.strip() for line in lines):
        raise ValueError("Journal must not contain blank records")
    if len(lines) > len(tasks):
        raise ValueError("Journal contains more cases than the frozen dataset")
    cases = []
    for index, line in enumerate(lines):
        case = parse_json(line)
        task = tasks[index]
        if not isinstance(case, dict) or case.get("example_id") != task["example_id"]:
            raise ValueError("Journal IDs must be a contiguous prefix without duplicates or gaps")
        response = case.get("response")
        if not isinstance(response, dict) or response.get("backend") != "model":
            raise ValueError("Journal response backend must be the actual model backend")
        if response.get("input", task["prompt"]) != task["prompt"]:
            raise ValueError("Journal response input differs from its frozen task")
        if response.get("tool_result") is not None or response.get("execute_tools", False):
            raise ValueError("Decision-only journal must not contain tool execution")
        elapsed = response.get("elapsed_ms")
        if isinstance(elapsed, bool) or not isinstance(elapsed, (int, float)):
            raise ValueError("Journal case elapsed_ms must be numeric")
        if not math.isfinite(elapsed) or elapsed < 0:
            raise ValueError("Journal case elapsed_ms must be finite and nonnegative")
        attempts = response.get("attempts")
        if not isinstance(attempts, list) or len(attempts) > 1 + protocol["max_repairs"]:
            raise ValueError("Journal attempts exceed the frozen repair bound")
        previous_valid = False
        for attempt_index, attempt in enumerate(attempts):
            if (
                not isinstance(attempt, dict)
                or attempt.get("attempt") != attempt_index + 1
                or attempt.get("repair") is not (attempt_index > 0)
                or not isinstance(attempt.get("raw_output"), str)
                or (attempt_index and previous_valid)
            ):
                raise ValueError("Journal attempt sequence violates the frozen repair policy")
            parsed = parse_output(task["example_id"], attempt["raw_output"])
            if not _equal(parsed["outcome"], attempt.get("parsed_outcome")):
                raise ValueError("Journal parsed outcome differs from its original raw output")
            previous_valid = parsed["outcome"] is not None and not validate_prediction(
                {"example_id": task["example_id"], "outcome": parsed["outcome"]}, task["tools"]
            )
            if attempt.get("schema_valid") is not previous_valid:
                raise ValueError("Journal schema validity differs from the canonical contract")
        status = response.get("status")
        if status not in {"validated", "clarification", "no_tool", "blocked", "error"}:
            raise ValueError("Journal has an unknown decision-only status")
        accepted = response.get("accepted_outcome")
        if status in {"blocked", "error"}:
            if accepted is not None:
                raise ValueError("Blocked/error response must not have an accepted decision")
        elif accepted is None or validate_prediction(
            {"example_id": task["example_id"], "outcome": accepted}, task["tools"]
        ):
            raise ValueError("Accepted decision is missing or violates the canonical contract")
        elif not _equal(accepted, response.get("outcome")):
            raise ValueError("Accepted outcome differs from the response decision")
        first = attempts[0] if attempts else {}
        expected_raw = original._prediction(
            task,
            first.get("parsed_outcome"),
            raw_output=first.get("raw_output", ""),
            metadata={"stage": "first_attempt", "backend": "model"},
        )
        expected_final = original._prediction(
            task, accepted, metadata={"stage": "accepted_final_decision", "backend": "model"}
        )
        if not _equal(case.get("raw_first_prediction"), expected_raw):
            raise ValueError("Journal raw prediction is not canonical for the saved first attempt")
        if not _equal(case.get("final_prediction"), expected_final):
            raise ValueError("Journal final prediction is not canonical for the accepted decision")
        cases.append(case)
    return cases


def _verify_frozen(run_dir: Path, model_path: Path, protocol: dict, *, verify_model: bool) -> None:
    expected_sources = protocol["source_files_sha256"]
    actual_sources = {
        str(path.relative_to(PROJECT_ROOT)): original.sha256(path) for path in original._sources()
    }
    if actual_sources != expected_sources:
        raise ValueError("Frozen source/policy hashes or source file list no longer match")
    data = Path(protocol["tasks_source_path"])
    for path in (data, run_dir / "tasks.jsonl"):
        if original.sha256(path) != protocol["tasks_sha256"]:
            raise ValueError("Frozen task data checksum no longer matches")
    for path in (data.parent / "manifest.json", run_dir / "dataset-manifest.json"):
        if original.sha256(path) != protocol["dataset_manifest_sha256"]:
            raise ValueError("Frozen dataset manifest checksum no longer matches")
    if original._versions() != protocol["libraries"]:
        raise ValueError("Runtime library versions differ from the frozen original run")
    if original.sha256(model_path / "download-manifest.json") != protocol["model_manifest_sha256"]:
        raise ValueError("Model manifest checksum differs from the frozen snapshot")
    if verify_model:
        from tunebench.live_model import verify_local_snapshot

        manifest = verify_local_snapshot(model_path)
        if (
            manifest["model_id"] != protocol["model_id"]
            or manifest["revision"] != protocol["resolved_model_revision"]
            or not _equal(manifest["files"], protocol["model_assets"])
        ):
            raise ValueError("Verified model assets differ from the original frozen model")
    inherited = parse_json((model_path / "generation_config.json").read_text())
    if not _equal(inherited, protocol["inherited_generation_config"]):
        raise ValueError("Inherited model generation configuration changed")


def load_existing(run_dir: Path, model_path: Path, verify_model: bool = True) -> dict[str, Any]:
    """Read and verify an interrupted run without writing files or generating text."""
    run_dir, model_path = run_dir.resolve(), model_path.resolve()
    if any((run_dir / name).exists() for name in COMPLETED_FILES):
        raise ValueError("Completed or partially finalized runs must not be resumed or overwritten")
    protocol_path = run_dir / "protocol.json"
    protocol = parse_json(protocol_path.read_text())
    if (
        protocol.get("protocol_version") != original.PROTOCOL_VERSION
        or protocol.get("status") != "frozen_before_generation"
        or protocol.get("backend") != "model"
        or protocol.get("execute_tools") is not False
        or protocol.get("seed") != 42
        or protocol.get("prompt_style") != "strong-v2"
        or protocol.get("max_repairs") not in {0, 1}
        or protocol.get("explicit_generation_overrides")
        != {"do_sample": False, "num_beams": 1, "max_new_tokens": 256, "repetition_penalty": 1.1}
    ):
        raise ValueError("Unsupported frozen protocol; no policy override is permitted")
    _verify_frozen(run_dir, model_path, protocol, verify_model=verify_model)
    tasks = read_jsonl(run_dir / "tasks.jsonl")
    original._validate_tasks(tasks)
    original._manifest_for(Path(protocol["tasks_source_path"]), tasks)
    if protocol["examples"] != len(tasks) or protocol["example_ids_in_order"] != [
        task["example_id"] for task in tasks
    ]:
        raise ValueError("Frozen task order/count differs from the protocol")
    messages = [build_messages(task, protocol["prompt_style"]) for task in tasks]
    saved_messages = parse_json((run_dir / "first-attempt.messages.json").read_text())
    if (
        not _equal(messages, saved_messages)
        or original._json_hash(messages) != protocol["first_attempt_messages_sha256"]
    ):
        raise ValueError("First-attempt messages differ from the frozen prompt")
    journal_bytes = (run_dir / "cases.partial.jsonl").read_bytes()
    cases = validate_journal(journal_bytes, tasks, protocol)
    if len(cases) >= len(tasks):
        raise ValueError("No positive remainder to resume; saved cases must not be regenerated")
    return {
        "protocol": protocol,
        "tasks": tasks,
        "cases": cases,
        "journal_bytes": journal_bytes,
        "protocol_hash": original.sha256(protocol_path),
    }


def finalize_run(
    run_dir: Path,
    protocol: dict,
    tasks: list[dict],
    cases: list[dict],
    runtime_metadata: dict,
    resume_events: list[dict],
    protocol_hash: str,
) -> dict:
    """Score all saved responses, with no model invocation and no case exclusion."""
    if any((run_dir / name).exists() for name in COMPLETED_FILES):
        raise ValueError("Refusing to overwrite existing completed evaluation evidence")
    if len(cases) != len(tasks) or [case["example_id"] for case in cases] != [
        task["example_id"] for task in tasks
    ]:
        raise ValueError("Finalization requires every frozen case exactly once and in order")
    saved = iter(cases)

    def saved_response(_message: str, **_kwargs: Any) -> dict:
        return deepcopy(next(saved)["response"])

    collected = original.collect_cases(
        tasks, saved_response, backend="model", max_repairs=protocol["max_repairs"]
    )
    if not _equal(collected["cases"], cases):
        raise ValueError("Saved case records differ from canonical original collection")
    if collected["pipeline"]["tool_results_returned"]:
        raise ValueError("Decision-only evaluation contains unexpected tool execution")
    elapsed = sum(case["response"]["elapsed_ms"] for case in cases) / 1000
    quality_ok = not collected["pipeline"]["runtime_error_cases"] and runtime_metadata.get("loaded")
    metadata = {
        "status": "completed" if quality_ok else "completed_with_runtime_errors",
        "backend": "model",
        "backend_label": original.LABELS["model"],
        "started_at_utc": protocol["created_at_utc"],
        "started_at_utc_source": (
            "Original protocol creation; original worker start was not retained"
        ),
        "completed_at_utc": datetime.now(UTC).isoformat(),
        "elapsed_seconds": elapsed,
        "elapsed_seconds_basis": (
            "Sum of per-response elapsed_ms; interruption and idle time excluded"
        ),
        "resumed": True,
        "resume_events": resume_events,
        "examples": len(tasks),
        "quality_claims_validated": bool(quality_ok),
        "protocol_sha256": protocol_hash,
        "tasks_sha256": protocol["tasks_sha256"],
        "model_runtime": runtime_metadata,
        "pipeline": collected["pipeline"],
        "finalization_replays_saved_responses_only": True,
    }
    results = []
    for stage, key, label in (
        ("raw-first", "raw", "Qwen raw first attempt"),
        ("final", "final", original.LABELS["model"]),
    ):
        write_jsonl(run_dir / f"{stage}.predictions.jsonl", collected[f"{key}_predictions"])
        report = collected[f"{key}_report"]
        report["gold_sha256"] = original._json_hash(tasks)
        report["inference_metadata"] = {**metadata, "stage": stage}
        write_json(run_dir / f"{stage}.report.json", report)
        results.append(
            {
                "label": label,
                "backend": "model",
                "examples": len(tasks),
                "strict_correct": report["task_success"]["correct"],
                "outcome_correct": report["outcome_accuracy"]["correct"],
                "valid_predictions": len(tasks) - report["invalid_predictions"],
            }
        )
    write_jsonl(run_dir / "cases.jsonl", cases)
    write_json(run_dir / "metadata.json", metadata)
    summary = {
        "title": "Frozen portfolio decision evaluation (resumed after interruption)",
        "dataset_label": f"{protocol['dataset_id']}: {len(tasks)} examples",
        "status": metadata["status"],
        "quality_claims_validated": bool(quality_ok),
        "resumed": True,
        "resume_events": resume_events,
        "limitations": [
            "Interrupted worker resumed; completed cases were preserved byte for byte.",
            "Elapsed seconds sum case runtimes and exclude interruption/idle time.",
            "Small assistant-authored and assistant-reviewed fictional dataset; no human review.",
            "Decision-only evaluation; execution guard checks are separate.",
            "Raw model output and guarded product decisions are separate metrics.",
            "Rules are not LLM accuracy; no fine-tuning was performed.",
        ],
        "results": results,
        "elapsed_seconds": elapsed,
        "pipeline": collected["pipeline"],
        "protocol_sha256": protocol_hash,
    }
    write_json(run_dir / "summary.json", summary)
    return summary


def resume_evaluation(run_dir: Path, model_path: Path) -> dict:
    """Lock the journal, preserve its prefix, then generate only unsaved decisions."""
    run_dir, model_path = run_dir.resolve(), model_path.resolve()
    with (run_dir / "cases.partial.jsonl").open("r+b") as journal:
        try:
            fcntl.flock(journal.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise ValueError("Another resume process holds the journal lock") from exc
        state = load_existing(run_dir, model_path)
        protocol, tasks, cases = state["protocol"], state["tasks"], state["cases"]
        prefix = state["journal_bytes"]
        expected_bytes = prefix
        script_hash = original.sha256(Path(__file__))
        event_path = run_dir / "resume-events.json"
        events = parse_json(event_path.read_text()) if event_path.exists() else []
        if not isinstance(events, list):
            raise ValueError("Resume events must be an append-only list")
        event = {
            "recorded_at_utc": datetime.now(UTC).isoformat(),
            "pid": os.getpid(),
            "parent_pid": os.getppid(),
            "previous_worker_pid": None,
            "resume_script": str(Path(__file__).relative_to(PROJECT_ROOT)),
            "resume_script_sha256": script_hash,
            "protocol_sha256": state["protocol_hash"],
            "preserved_cases": len(cases),
            "preserved_journal_bytes": len(prefix),
            "preserved_journal_sha256": original.hashlib.sha256(prefix).hexdigest(),
            "remaining_example_ids": [task["example_id"] for task in tasks[len(cases) :]],
            "reason": "Previous worker stopped during an environment/session interruption",
            "status": "running",
            "original_worker_start_and_stop_times": "not retained",
        }
        events.append(event)
        write_json(event_path, events)
        started = time.perf_counter()

        def assert_unchanged() -> None:
            if original.sha256(run_dir / "protocol.json") != state["protocol_hash"]:
                raise ValueError("Frozen protocol changed during resumed evaluation")
            if original.sha256(Path(__file__)) != script_hash:
                raise ValueError("Resume runner changed during evaluation")
            _verify_frozen(run_dir, model_path, protocol, verify_model=False)
            journal.seek(0)
            if journal.read() != expected_bytes:
                raise ValueError("Saved journal prefix or appended evidence changed")

        def checkpoint(case: dict) -> None:
            nonlocal expected_bytes
            assert_unchanged()
            encoded = (json.dumps(case, ensure_ascii=False, allow_nan=False) + "\n").encode()
            validate_journal(expected_bytes + encoded, tasks, protocol)
            journal.seek(0, os.SEEK_END)
            journal.write(encoded)
            journal.flush()
            os.fsync(journal.fileno())
            expected_bytes += encoded
            cases.append(case)
            print(
                f"resumed model: completed {len(cases)}/{len(tasks)}; "
                f"resume active wall time {time.perf_counter() - started:.1f}s "
                f"({case['response'].get('status')})",
                flush=True,
            )
            if case["response"].get("status") == "error":
                from tunebench.live_model import model_status

                if not model_status()["loaded"]:
                    raise RuntimeError(
                        "Model startup failed; checkpoint retained without case rerun"
                    )

        try:
            import torch
            from transformers import set_seed

            random.seed(protocol["seed"])
            torch.set_num_threads(protocol["cpu_threads"])
            torch.set_num_interop_threads(protocol["cpu_interop_threads"])
            set_seed(protocol["seed"])
            from tunebench.assistant import respond
            from tunebench.live_model import model_status

            assert_unchanged()
            original.collect_cases(
                tasks[len(cases) :],
                respond,
                backend="model",
                model_path=model_path,
                max_repairs=protocol["max_repairs"],
                checkpoint=checkpoint,
            )
            assert_unchanged()
            runtime = model_status()
            prior_runtime = next(
                (
                    case["response"].get("model_metadata")
                    for case in state["cases"]
                    if case["response"].get("model_metadata")
                ),
                None,
            )
            if prior_runtime is not None and not _equal(runtime, prior_runtime):
                raise ValueError("Resumed model runtime configuration differs from saved session")
            event.update(
                {
                    "status": "completed",
                    "completed_at_utc": datetime.now(UTC).isoformat(),
                    "resume_active_wall_seconds": time.perf_counter() - started,
                    "completed_cases": len(cases),
                    "final_journal_sha256": original.hashlib.sha256(expected_bytes).hexdigest(),
                    "preserved_prefix_verified": expected_bytes[: len(prefix)] == prefix,
                }
            )
            write_json(event_path, events)
            return finalize_run(
                run_dir, protocol, tasks, cases, runtime, events, state["protocol_hash"]
            )
        except BaseException as exc:
            event.update(
                {
                    "status": "interrupted_or_failed",
                    "stopped_at_utc": datetime.now(UTC).isoformat(),
                    "resume_active_wall_seconds": time.perf_counter() - started,
                    "completed_cases": len(cases),
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                }
            )
            write_json(event_path, events)
            raise


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--model-path", type=Path, required=True)
    parser.add_argument(
        "--check-only", action="store_true", help="Verify inputs without generation"
    )
    args = parser.parse_args()
    if args.check_only:
        state = load_existing(args.run_dir, args.model_path)
        print(
            json.dumps(
                {
                    "status": "verified_interrupted_run",
                    "preserved_cases": len(state["cases"]),
                    "remaining_cases": len(state["tasks"]) - len(state["cases"]),
                    "protocol_sha256": state["protocol_hash"],
                }
            )
        )
    else:
        print(json.dumps(resume_evaluation(args.run_dir, args.model_path), ensure_ascii=False))


if __name__ == "__main__":
    main()
