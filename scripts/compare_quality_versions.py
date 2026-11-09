"""Compare frozen v0.4 and v0.5 systems on 40 new questions, with audited resume.

The parent imports only standard-library modules. Each sequential worker imports
TuneBench from its own source root, keeping archived and candidate code isolated.
"""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import importlib.metadata
import io
import json
import math
import os
import random
import subprocess
import sys
import tarfile
import time
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

VERSIONS = ("legacy", "candidate")
EXECUTION_ORDER = ("candidate", "legacy")
EXAMPLES = 40
LEGACY_COMMIT = "7498d78"
SCORING_CONTRACT_FILES = (
    "src/tunebench/contracts.py",
    "src/tunebench/evaluator.py",
    "src/tunebench/io.py",
    "src/tunebench/resources/schemas/task.schema.json",
    "src/tunebench/resources/schemas/prediction.schema.json",
    "src/tunebench/resources/configs/tool_registry.json",
    "src/tunebench/resources/configs/evaluation.json",
)
CANDIDATE_MODEL = {
    "model_id": "unsloth/Qwen3-4B-Instruct-2507-GGUF",
    "base_model_id": "Qwen/Qwen3-4B-Instruct-2507",
    "revision": "a06e946bb6b655725eafa393f4a9745d460374c9",
    "filename": "Qwen3-4B-Instruct-2507-Q4_K_M.gguf",
    "size": 2497281120,
    "sha256": "3605803b982cb64aead44f6c1b2ae36e3acdb41d8e46c8a94c6533bc4c67e597",
}
# fmt: off
SETTINGS = {"seed": 42, "cpu_threads": 4,
            "do_sample": False, "num_beams": 1, "max_new_tokens": 256,
            "repetition_penalty": 1.1, "max_repairs": 1, "execute_tools": False}
# fmt: on


def digest(path):
    value = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(4 * 1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def _unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def loads(text):
    def finite(value):
        number = float(value)
        if not math.isfinite(number):
            raise ValueError("Non-finite JSON number")
        return number

    return json.loads(text, object_pairs_hook=_unique, parse_float=finite, parse_constant=finite)


def json_equal(left, right):
    """Compare JSON values without treating booleans as monetary numbers."""
    if isinstance(left, bool) or isinstance(right, bool):
        return type(left) is type(right) and left == right
    if isinstance(left, dict) and isinstance(right, dict):
        return left.keys() == right.keys() and all(
            json_equal(left[key], right[key]) for key in left
        )
    if isinstance(left, list) and isinstance(right, list):
        return len(left) == len(right) and all(
            json_equal(a, b) for a, b in zip(left, right, strict=True)
        )
    return left == right


def write(path, value):
    temporary = Path(path).with_suffix(Path(path).suffix + f".{os.getpid()}.tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        handle.write(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    temporary.replace(path)


def journal_checkpoint(directory, journal, cases):
    """Record durable bytes; a crash between writes stops rather than reruns a case."""
    data = journal.read_bytes() if journal.exists() else b""
    checkpoint = {
        "completed_cases": len(cases),
        "journal_bytes": len(data),
        "journal_sha256": hashlib.sha256(data).hexdigest(),
    }
    write(directory / "journal-checkpoint.json", checkpoint)


def verify_checkpoint(directory, journal, cases):
    path = directory / "journal-checkpoint.json"
    if cases and not path.exists():
        raise ValueError("Prior journal has no durable checkpoint; do not rerun or rewrite")
    if path.exists():
        data = journal.read_bytes() if journal.exists() else b""
        expected = {
            "completed_cases": len(cases),
            "journal_bytes": len(data),
            "journal_sha256": hashlib.sha256(data).hexdigest(),
        }
        if loads(path.read_text()) != expected:
            raise ValueError("Prior journal differs from its durable checkpoint")
    pending = directory / "inflight.json"
    if pending.exists():
        raise ValueError(
            "A prior case started without a completed durable response. "
            "Its generation state is unknown; do not rerun it or claim a complete comparison."
        )


def versions():
    result = {"python": sys.version.split()[0]}
    names = "tunebench torch transformers accelerate jsonschema tokenizers numpy"
    for name in names.split() + [
        "lm-format-enforcer",
        "interegular",
        "llama-cpp-python",
        "pydantic",
        "pydantic_core",
    ]:
        try:
            result[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            result[name] = None
    return result


def source_hashes(root):
    root = Path(root)
    paths = [
        root / "pyproject.toml",
        *root.joinpath("src/tunebench").rglob("*.py"),
        *root.joinpath("src/tunebench/resources").rglob("*.json"),
    ]
    return {str(path.relative_to(root)): digest(path) for path in sorted(paths)}


def _legacy_archive_hashes(root):
    archive = subprocess.check_output(
        ["git", "-C", str(root), "archive", LEGACY_COMMIT, "src/tunebench", "pyproject.toml"]
    )
    with tarfile.open(fileobj=io.BytesIO(archive)) as handle:
        # fmt: off
        return {item.name: hashlib.sha256(handle.extractfile(item).read()).hexdigest()
                for item in handle.getmembers() if item.isfile() and (
                    item.name == "pyproject.toml" or item.name.endswith(".py") or
                    (item.name.startswith("src/tunebench/resources/") and
                     item.name.endswith(".json")))}
        # fmt: on


def model_spec(path, version):
    """Freeze locally verified assets without importing either inference runtime."""
    path = Path(path).expanduser().resolve()
    if version == "legacy":
        manifest_path = path / "download-manifest.json"
        manifest = loads(manifest_path.read_text())
        if (
            manifest.get("model_id") != "Qwen/Qwen2.5-1.5B-Instruct"
            or manifest.get("revision") != "989aa7980e4cf806f80c7fef2b1adb7bc71aa306"
        ):
            raise ValueError("Legacy model must be the pinned verified Qwen2.5 snapshot")
        files = [manifest_path]
        for name, item in manifest["files"].items():
            asset = path / name
            if Path(name).name != name or asset.resolve().parent != path:
                raise ValueError("Legacy asset must stay inside the snapshot")
            if asset.stat().st_size != item["size"]:
                raise ValueError("Legacy model asset size mismatch")
            if item["hash_algorithm"] == "sha256":
                actual = digest(asset)
            elif item["hash_algorithm"] == "git-blob-sha1":
                actual = hashlib.sha1(
                    f"blob {item['size']}\0".encode() + asset.read_bytes()
                ).hexdigest()
            else:
                raise ValueError("Unknown model verification algorithm")
            if actual != item["upstream_hash"]:
                raise ValueError("Legacy model upstream checksum mismatch")
            files.append(asset)
        result = {
            "path": str(path),
            "format": "safetensors",
            "dtype": "float32",
            "model_id": manifest["model_id"],
            "revision": manifest["revision"],
            "weights_sha256": manifest["files"]["model.safetensors"]["upstream_hash"],
            "download_manifest": manifest,
        }
    else:
        if path.name != CANDIDATE_MODEL["filename"] or not path.is_file():
            raise ValueError("Candidate requires its verified local GGUF file")
        if (
            path.stat().st_size != CANDIDATE_MODEL["size"]
            or digest(path) != CANDIDATE_MODEL["sha256"]
        ):
            raise ValueError("Candidate GGUF differs from pinned upstream size/SHA-256")
        files = [path]
        result = {
            "path": str(path),
            "format": "gguf",
            "dtype": "Q4_K_M",
            "model_id": CANDIDATE_MODEL["model_id"],
            "base_model_id": CANDIDATE_MODEL["base_model_id"],
            "revision": CANDIDATE_MODEL["revision"],
            "weights_sha256": CANDIDATE_MODEL["sha256"],
            "upstream_file": CANDIDATE_MODEL["filename"],
            "verification": "Pinned Hugging Face LFS SHA-256; third-party Unsloth conversion",
        }
    result["assets"] = {
        str(asset): {
            "bytes": asset.stat().st_size,
            "mtime_ns": asset.stat().st_mtime_ns,
            "sha256": digest(asset),
        }
        for asset in files
    }
    return result


def verify_models(protocol, full=False):
    for model in protocol["models"].values():
        for name, expected in model["assets"].items():
            path = Path(name)
            if (
                not path.is_file()
                or path.stat().st_size != expected["bytes"]
                or path.stat().st_mtime_ns != expected["mtime_ns"]
            ):
                raise ValueError("Frozen model asset size or modification time changed")
            if full and digest(path) != expected["sha256"]:
                raise ValueError("Frozen model asset checksum changed")


def verify(protocol, output, full_model=False):
    if digest(Path(__file__)) != protocol["runner_sha256"] or versions() != protocol["libraries"]:
        raise ValueError("Frozen runner or selected runtime libraries changed")
    for version in VERSIONS:
        if source_hashes(Path(protocol["roots"][version])) != protocol["sources"][version]:
            raise ValueError(f"Frozen {version} source changed")
    for path in (Path(protocol["data_source"]), output / "tasks.jsonl"):
        if digest(path) != protocol["tasks_sha256"]:
            raise ValueError("Frozen data changed")
    for path in (Path(protocol["manifest_source"]), output / "dataset-manifest.json"):
        if digest(path) != protocol["dataset_manifest_sha256"]:
            raise ValueError("Frozen dataset manifest changed")
    verify_models(protocol, full_model)


def freeze_or_verify(args):
    output = args.output.resolve()
    roots = {v: str(getattr(args, f"{v}_root").resolve()) for v in VERSIONS}
    paths = {v: str(getattr(args, f"{v}_model_path").resolve()) for v in VERSIONS}
    if args.resume:
        protocol = loads((output / "protocol.json").read_text())
        if str(args.data.resolve()) != protocol["data_source"]:
            raise ValueError("Resume data differs from the frozen protocol")
        if roots != protocol["roots"] or paths != {
            v: protocol["models"][v]["path"] for v in VERSIONS
        }:
            raise ValueError("Resume source roots or model paths changed")
        verify(protocol, output, full_model=True)
        return protocol
    if output.exists() and any(path.name != ".runner.lock" for path in output.iterdir()):
        raise ValueError("Choose fresh output or explicitly resume the existing frozen run")
    sources = {v: source_hashes(Path(root)) for v, root in roots.items()}
    if sources["legacy"] != _legacy_archive_hashes(Path(roots["candidate"])):
        raise ValueError("Legacy source is not the unchanged 7498d78 archive")
    for name in SCORING_CONTRACT_FILES:
        if sources["legacy"][name] != sources["candidate"][name]:
            raise ValueError("Both systems require the same canonical scoring contract")
    data = args.data.resolve()
    tasks = [loads(line) for line in data.read_text().splitlines() if line.strip()]
    if len(tasks) != EXAMPLES or len({task["example_id"] for task in tasks}) != EXAMPLES:
        raise ValueError("The fresh comparison requires all 40 unique held-out cases")
    if any(task.get("split") != "test" for task in tasks):
        raise ValueError("The comparison accepts the frozen test split only")
    manifest_path = data.parent / "manifest.json"
    dataset = loads(manifest_path.read_text())
    entry = next(
        (
            item
            for item in dataset["files"].values()
            if (data.parent / item["path"]).resolve() == data
        ),
        None,
    )
    if (
        not entry
        or entry["sha256"] != digest(data)
        or entry["examples"] != EXAMPLES
        or entry.get("bytes") != data.stat().st_size
    ):
        raise ValueError("Dataset does not match its frozen manifest")
    models = {v: model_spec(paths[v], v) for v in VERSIONS}
    output.mkdir(parents=True, exist_ok=True)
    (output / "tasks.jsonl").write_bytes(data.read_bytes())
    (output / "dataset-manifest.json").write_bytes(manifest_path.read_bytes())
    protocol = {
        "protocol_version": "quality-system-comparison-v1",
        "comparison_type": "system_version_comparison_not_model_or_prompt_ablation",
        "created_at_utc": datetime.now(UTC).isoformat(),
        "execution_order": list(EXECUTION_ORDER),
        "roots": roots,
        "sources": sources,
        "legacy_commit": LEGACY_COMMIT,
        "data_source": str(data),
        "dataset_id": dataset["dataset_id"],
        "manifest_source": str(manifest_path),
        "tasks_sha256": digest(data),
        "dataset_manifest_sha256": digest(manifest_path),
        "examples": EXAMPLES,
        "example_ids": [task["example_id"] for task in tasks],
        "models": models,
        "runner_sha256": digest(Path(__file__)),
        "libraries": versions(),
        "settings": SETTINGS,
        "runtime_differences": {
            "legacy": "Qwen2.5-1.5B float32 safetensors; Torch/Transformers + LMFE",
            "candidate": "Qwen3-4B-Instruct-2507 Q4_K_M GGUF; llama.cpp grammar",
            "interpretation": "Model, quantization, backend, prompt and guard change together",
        },
        "system_changes": [
            "model weights",
            "quantization",
            "inference runtime",
            "prompt",
            "structured decoding",
            "grounding",
            "repair feedback",
        ],
        "holdout_policy": "No tuning, relabeling, exclusions or reruns after generation",
        "scoring_limits": "Canonical decisions only; helpfulness and execution safety ungraded",
    }
    write(output / "protocol.json", protocol)
    return protocol


def _predictions(task, response):
    attempts = response.get("attempts") or []
    first = attempts[0] if attempts else {}
    accepted = response.get("accepted_outcome")
    if response["status"] in {"blocked", "error"}:
        accepted = None
    # fmt: off
    return ({"example_id": task["example_id"], "outcome": first.get("parsed_outcome"),
             "raw_output": first.get("raw_output", "")},
            {"example_id": task["example_id"], "outcome": accepted})
    # fmt: on


def read_journal(path, tasks, max_repairs=1):
    data = Path(path).read_bytes() if Path(path).exists() else b""
    if data and not data.endswith(b"\n"):
        raise ValueError("Truncated journal must not be repaired or rerun")
    lines = data.decode().splitlines()
    if len(lines) > len(tasks) or any(not line.strip() for line in lines):
        raise ValueError("Journal must be a complete contiguous prefix")
    cases = []
    for index, line in enumerate(lines):
        case, task = loads(line), tasks[index]
        response = case["response"]
        if case["example_id"] != task["example_id"] or response.get("input") != task["prompt"]:
            raise ValueError("Journal has duplicate, missing, reordered, or mismatched cases")
        if response.get("backend") != "model" or response.get("execute_tools") is not False:
            raise ValueError("Journal requires actual model decisions with execution disabled")
        if response.get("status") not in {
            "validated",
            "clarification",
            "no_tool",
            "blocked",
            "error",
        }:
            raise ValueError("Journal has an invalid decision-only status")
        if response.get("tool_result") is not None:
            raise ValueError("Decision-only comparison must not execute tools")
        attempts = response.get("attempts", [])
        if len(attempts) > 1 + max_repairs:
            raise ValueError("Journal exceeds bounded repairs")
        for number, attempt in enumerate(attempts, 1):
            if attempt["attempt"] != number or attempt["repair"] is not (number > 1):
                raise ValueError("Journal attempt sequence is invalid")
            try:
                parsed = loads(attempt["raw_output"])
                parsed = parsed if isinstance(parsed, dict) else None
            except (ValueError, TypeError):
                parsed = None
            if not json_equal(parsed, attempt["parsed_outcome"]):
                raise ValueError("Raw output and parsed attempt differ")
        if not json_equal(
            response.get("outcome"), attempts[-1]["parsed_outcome"] if attempts else None
        ):
            raise ValueError("Response outcome differs from its last parsed attempt")
        if (
            response["status"] in {"blocked", "error"}
            and response.get("accepted_outcome") is not None
        ):
            raise ValueError("Rejected decisions must not be accepted")
        if response["status"] in {"validated", "clarification", "no_tool"} and not isinstance(
            response.get("accepted_outcome"), dict
        ):
            raise ValueError("Accepted status requires an accepted model decision")
        if response.get("accepted_outcome") is not None and not json_equal(
            response["accepted_outcome"], response["outcome"]
        ):
            raise ValueError("Accepted decision differs from model output")
        raw, final = _predictions(task, response)
        if not json_equal(case["raw_first_prediction"], raw) or not json_equal(
            case["final_prediction"], final
        ):
            raise ValueError("Saved raw/final predictions are not canonical")
        elapsed = response["elapsed_ms"]
        if (
            isinstance(elapsed, bool)
            or not isinstance(elapsed, (float, int))
            or not math.isfinite(elapsed)
            or elapsed < 0
        ):
            raise ValueError("Invalid recorded case runtime")
        cases.append(case)
    return cases


def score_cases(tasks, cases, evaluate):
    if [c["example_id"] for c in cases] != [t["example_id"] for t in tasks]:
        raise ValueError("Every frozen case must be scored exactly once")
    counts = Counter(case["response"]["status"] for case in cases)
    # fmt: off
    return {"raw_report": evaluate(tasks, [case["raw_first_prediction"] for case in cases]),
            "final_report": evaluate(tasks, [case["final_prediction"] for case in cases]),
            "active_seconds": sum(case["response"]["elapsed_ms"] for case in cases) / 1000,
            "pipeline": {"status_counts": dict(counts), "runtime_errors": counts.get("error", 0),
                         "generation_attempts": sum(len(c["response"]["attempts"]) for c in cases),
                         "repair_attempts": sum(max(0, len(c["response"]["attempts"])-1)
                                                for c in cases), "execution_enabled": False,
                         "execution_safety": "Measured separately; no tools execute here"}}
    # fmt: on


def normalized_config(runtime):
    config = runtime["effective_generation_config"]
    return {
        key: config.get(key)
        for key in ("do_sample", "num_beams", "max_new_tokens", "repetition_penalty")
    }


def _runtime_shared(runtime, protocol, version):
    model, settings = protocol["models"][version], protocol["settings"]
    expected = {
        "model_id": model["model_id"],
        "resolved_model_revision": model["revision"],
        "weights_sha256": model["weights_sha256"],
        "device": "cpu",
        "dtype": model["dtype"],
        "seed": 42,
        "cpu_threads": 4,
    }
    if not runtime.get("loaded") or any(runtime.get(k) != v for k, v in expected.items()):
        raise ValueError("Actual model runtime differs from frozen model/settings")
    if not json_equal(
        normalized_config(runtime), {key: settings[key] for key in normalized_config(runtime)}
    ):
        raise ValueError("Actual normalized decoding settings differ from the frozen protocol")
    if version == "legacy" and runtime.get("cpu_interop_threads") != 1:
        raise ValueError("Legacy CPU inter-operation threads must equal one")
    if version == "candidate" and runtime.get("cpu_batch_threads") != 4:
        raise ValueError("Candidate CPU batch threads must equal four")
    if version == "candidate":
        # Check the arguments llama.cpp actually receives as well as aliases
        # retained for cross-runtime comparison. An alias must not hide a
        # different native token budget or a sampling setting.
        native = {
            "max_tokens": settings["max_new_tokens"],
            "temperature": 0.0,
            "top_p": 1.0,
            "top_k": 0,
            "min_p": 0.0,
            "repeat_penalty": settings["repetition_penalty"],
            "seed": settings["seed"],
            "stream": False,
        }
        if any(
            not json_equal(runtime["effective_generation_config"].get(k), v)
            for k, v in native.items()
        ):
            raise ValueError("Candidate native decoding settings differ from the frozen protocol")


def retained_runtime(current, cases):
    if current.get("loaded"):
        return current
    for case in reversed(cases):
        runtime = case["response"].get("model_metadata", {})
        if runtime.get("loaded"):
            return runtime
    raise ValueError("No retained loaded model runtime; quality readiness is unverified")


def worker(args):
    output = args.output.resolve()
    protocol = loads((output / "protocol.json").read_text())
    protocol_hash = digest(output / "protocol.json")
    root = Path(protocol["roots"][args.worker])
    sys.path.insert(0, str(root / "src"))
    import tunebench
    from tunebench.assistant import respond
    from tunebench.contracts import load_tool_registry, validate_task
    from tunebench.evaluator import evaluate

    if args.worker == "legacy":
        from tunebench.live_model import model_status
    else:
        from tunebench.gguf_model import model_status

    if Path(tunebench.__file__).resolve() != root / "src/tunebench/__init__.py":
        raise ValueError("Worker imported the wrong source package")
    tasks = [
        loads(line) for line in (output / "tasks.jsonl").read_text().splitlines() if line.strip()
    ]
    tools = load_tool_registry()
    for task in tasks:
        if validate_task(task):
            raise ValueError("Invalid frozen task contract")
        if task["tools"] != tools:
            raise ValueError("Frozen tasks must use the canonical support tool registry")
    directory = output / args.worker
    directory.mkdir(exist_ok=True)
    journal = directory / "cases.partial.jsonl"
    cases = read_journal(journal, tasks)
    verify_checkpoint(directory, journal, cases)
    if (directory / "metadata.json").exists():
        result = score_cases(tasks, cases, evaluate)
        saved_metadata = loads((directory / "metadata.json").read_text())
        if saved_metadata["protocol_sha256"] != protocol_hash:
            raise ValueError("Completed worker report belongs to another protocol")
        _runtime_shared(saved_metadata["model_runtime"], protocol, args.worker)
        if (
            not json_equal(saved_metadata["pipeline"], result["pipeline"])
            or saved_metadata["active_seconds"] != result["active_seconds"]
            or saved_metadata["quality_claims_validated"]
            is not (result["pipeline"]["runtime_errors"] == 0)
        ):
            raise ValueError("Saved completed metadata differs from journal recomputation")
        for stage, key in (("raw-first", "raw"), ("final", "final")):
            saved = loads((directory / f"{stage}.report.json").read_text())
            if not json_equal(saved.get("inference_metadata"), saved_metadata):
                raise ValueError("Saved report inference metadata differs from worker metadata")
            if not json_equal(
                result[f"{key}_report"],
                {k: v for k, v in saved.items() if k != "inference_metadata"},
            ):
                raise ValueError("Saved completed report differs from journal recomputation")
        print(
            f"{args.worker}: verified completed {len(tasks)}/{len(tasks)}; no generation",
            flush=True,
        )
        return
    prefix = journal.read_bytes() if journal.exists() else b""
    expected_bytes = prefix
    events_path = directory / "worker-events.json"
    events = loads(events_path.read_text()) if events_path.exists() else []
    # fmt: off
    event = {"started_at_utc": datetime.now(UTC).isoformat(), "pid": os.getpid(),
             "version": args.worker, "protocol_sha256": protocol_hash,
             "preserved_cases": len(cases), "prefix_bytes": len(prefix),
             "prefix_sha256": hashlib.sha256(prefix).hexdigest(), "status": "running"}
    # fmt: on
    events.append(event)
    write(events_path, events)
    started = time.perf_counter()
    try:
        random.seed(42)
        if args.worker == "legacy":
            import torch
            from transformers import set_seed

            torch.set_num_threads(4)
            torch.set_num_interop_threads(1)
            set_seed(42)
        # Candidate llama.cpp is seeded explicitly by its verified backend.

        for task in tasks[len(cases) :]:
            verify(protocol, output)
            if digest(output / "protocol.json") != protocol_hash:
                raise ValueError("Frozen protocol changed")
            if journal.exists() and journal.read_bytes() != expected_bytes:
                raise ValueError("Saved journal bytes changed")
            write(
                directory / "inflight.json",
                {"example_id": task["example_id"], "started_at_utc": datetime.now(UTC).isoformat()},
            )
            request_started = time.perf_counter()
            try:
                response = respond(
                    task["prompt"],
                    backend="model",
                    model_path=protocol["models"][args.worker]["path"],
                    max_repairs=1,
                    execute_tools=False,
                )
            except Exception as exc:
                # fmt: off
                response = {"input": task["prompt"], "backend": "model", "execute_tools": False,
                            "tool_result": None, "status": "error", "outcome": None,
                            "accepted_outcome": None, "attempts": [],
                            "elapsed_ms": (time.perf_counter() - request_started) * 1000,
                            "runtime_error": {"type": type(exc).__name__, "message": str(exc)}}
                # fmt: on
            raw, final = _predictions(task, response)
            case = {
                "example_id": task["example_id"],
                "response": response,
                "raw_first_prediction": raw,
                "final_prediction": final,
            }
            encoded = (json.dumps(case, ensure_ascii=False, allow_nan=False) + "\n").encode()
            with journal.open("ab") as handle:
                handle.write(encoded)
                handle.flush()
                os.fsync(handle.fileno())
            expected_bytes += encoded
            cases.append(case)
            read_journal(journal, tasks)
            journal_checkpoint(directory, journal, cases)
            (directory / "inflight.json").unlink()
            print(
                f"{args.worker}: {len(cases)}/{len(tasks)} ({response['status']}) "
                f"active worker {time.perf_counter() - started:.1f}s",
                flush=True,
            )
            if not model_status()["loaded"]:
                raise RuntimeError("Model startup failed; saved failed case will not be rerun")
        verify(protocol, output, full_model=True)
        if journal.read_bytes() != expected_bytes:
            raise ValueError("Saved journal bytes changed before finalization")
        runtime = retained_runtime(model_status(), cases)
        _runtime_shared(runtime, protocol, args.worker)
        result = score_cases(tasks, cases, evaluate)
        # fmt: off
        metadata = {"system_version": args.worker, "source_root": str(root),
                    "source_package_version": tunebench.__version__,
                    "installed_libraries": versions(),
                    "model_runtime": runtime, "protocol_sha256": protocol_hash,
                    "active_seconds": result["active_seconds"],
                    "timing_basis": "Sum of case elapsed_ms; idle interruptions excluded",
                    "quality_claims_validated": result["pipeline"]["runtime_errors"] == 0,
                    "pipeline": result["pipeline"], "worker_events": events}
        # fmt: on
        event.update(
            status="completed",
            completed_at_utc=datetime.now(UTC).isoformat(),
            preserved_prefix_verified=expected_bytes[: len(prefix)] == prefix,
            final_journal_sha256=digest(journal),
            completed_cases=len(cases),
        )
        write(events_path, events)
        for stage, key in (("raw-first", "raw"), ("final", "final")):
            report = result[f"{key}_report"]
            report["inference_metadata"] = metadata
            write(directory / f"{stage}.report.json", report)
        write(directory / "metadata.json", metadata)
    except BaseException as exc:
        event.update(
            status="interrupted_or_failed",
            stopped_at_utc=datetime.now(UTC).isoformat(),
            error_type=type(exc).__name__,
            error=str(exc),
            completed_cases=len(cases),
        )
        write(events_path, events)
        raise


def compare(output, protocol):
    # fmt: off
    reports = {v: {stage: loads((output / v / f"{stage}.report.json").read_text())
                   for stage in ("raw-first", "final")} for v in VERSIONS}
    # fmt: on
    runtimes = [reports[v]["final"]["inference_metadata"]["model_runtime"] for v in VERSIONS]
    protocol_hash = digest(output / "protocol.json")
    for version in VERSIONS:
        for stage in ("raw-first", "final"):
            if reports[version][stage]["inference_metadata"]["protocol_sha256"] != protocol_hash:
                raise ValueError("Worker reports refer to different frozen protocols")
    for version, runtime in zip(VERSIONS, runtimes, strict=True):
        _runtime_shared(runtime, protocol, version)
    if not json_equal(normalized_config(runtimes[0]), normalized_config(runtimes[1])):
        raise ValueError("Normalized shared generation configuration differs between versions")
    # fmt: off
    result = {"comparison_type": protocol["comparison_type"], "examples": protocol["examples"],
              "protocol_sha256": digest(output / "protocol.json"), "results": {},
              "limitations": ["Prompt, constraints and grounding changed; not a prompt ablation.",
                              "Different weights, quantization and runtimes; effects are combined.",
                              "Small assistant-authored holdout; no production reliability claim.",
                              "Execution disabled; execution safety checked separately."]}
    # fmt: on
    for stage in ("raw-first", "final"):
        old, new = (reports[v][stage] for v in VERSIONS)
        result["results"][stage] = {v: reports[v][stage]["task_success"] for v in VERSIONS}
        pairs = [
            (left["task_success"], right["task_success"], right["example_id"])
            for left, right in zip(old["per_example"], new["per_example"], strict=True)
        ]
        for label, values in (("improvements", (False, True)), ("regressions", (True, False))):
            result["results"][stage][label] = [key for a, b, key in pairs if (a, b) == values]
    result["quality_claims_validated"] = all(
        reports[v]["final"]["inference_metadata"]["quality_claims_validated"] for v in VERSIONS
    )
    for stage in ("raw-first", "final"):
        result["results"][stage]["schema_valid_decisions"] = {
            v: reports[v][stage]["total_examples"] - reports[v][stage]["invalid_predictions"]
            for v in VERSIONS
        }
    write(output / "comparison.json", result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in (
        "legacy-root",
        "candidate-root",
        "data",
        "legacy-model-path",
        "candidate-model-path",
        "output",
    ):
        parser.add_argument(f"--{name}", type=Path)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--worker", choices=VERSIONS, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.worker:
        return worker(args)
    if any(
        getattr(args, key) is None
        for key in (
            "legacy_root",
            "candidate_root",
            "data",
            "legacy_model_path",
            "candidate_model_path",
            "output",
        )
    ):
        parser.error("Both source roots, model paths, data and output are required")
    args.output.mkdir(parents=True, exist_ok=True)
    with (args.output / ".runner.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        protocol = freeze_or_verify(args)
        protocol_hash = digest(args.output / "protocol.json")
        for version in EXECUTION_ORDER:
            if digest(args.output / "protocol.json") != protocol_hash:
                raise ValueError("Frozen parent protocol changed before worker launch")
            # fmt: off
            env = {**os.environ, "OMP_NUM_THREADS": "4", "MKL_NUM_THREADS": "4",
                   "OPENBLAS_NUM_THREADS": "1", "TOKENIZERS_PARALLELISM": "false",
                   "HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1"}
            subprocess.run([sys.executable, "-u", str(Path(__file__).resolve()),
                            "--worker", version, "--output", str(args.output.resolve())],
                           env=env, check=True)
            # fmt: on
            if digest(args.output / "protocol.json") != protocol_hash:
                raise ValueError("Frozen parent protocol changed during a worker run")
            verify(protocol, args.output)
        print(json.dumps(compare(args.output, protocol), ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
