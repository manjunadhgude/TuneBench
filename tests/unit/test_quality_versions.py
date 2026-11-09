"""Synthetic accounting/isolation tests; no holdout data or model weights are read."""

import ast
import importlib.util
import json
import os
import subprocess
import sys
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace

import pytest

from tunebench.contracts import load_tool_registry
from tunebench.evaluator import evaluate

SCRIPT = Path(__file__).resolve().parents[2] / "scripts/compare_quality_versions.py"
SPEC = importlib.util.spec_from_file_location("quality_versions", SCRIPT)
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


def task(key="synthetic-1"):
    return {
        "example_id": key,
        "prompt": f"Synthetic request {key}",
        "schema_version": "3.0.0",
        "family_id": key,
        "scenario_id": key,
        "split": "test",
        "difficulty": "medium",
        "tools": load_tool_registry(),
        "expected_outcome": {"type": "no_tool", "reason_code": "no_action_requested"},
    }


def case(example, *, blocked=False, repair=False):
    outcome = example["expected_outcome"]
    attempts = [
        {
            "attempt": 1,
            "repair": False,
            "raw_output": json.dumps(outcome),
            "parsed_outcome": outcome,
            "schema_valid": True,
            "validation_errors": [],
        }
    ]
    if repair:
        attempts[0].update(raw_output="bad JSON", parsed_outcome=None, schema_valid=False)
        attempts.append(
            {
                **attempts[0],
                "attempt": 2,
                "repair": True,
                "raw_output": json.dumps(outcome),
                "parsed_outcome": outcome,
                "schema_valid": True,
            }
        )
    response = {
        "input": example["prompt"],
        "backend": "model",
        "execute_tools": False,
        "tool_result": None,
        "status": "blocked" if blocked else "no_tool",
        "outcome": outcome,
        "accepted_outcome": None if blocked else outcome,
        "attempts": attempts,
        "elapsed_ms": 1250,
    }
    raw, final = runner._predictions(example, response)
    return {
        "example_id": example["example_id"],
        "response": response,
        "raw_first_prediction": raw,
        "final_prediction": final,
    }


def journal(path, cases):
    path.write_text("".join(json.dumps(item) + "\n" for item in cases))


def test_parent_has_no_top_level_tunebench_import():
    tree = ast.parse(SCRIPT.read_text())
    imports = [node for node in tree.body if isinstance(node, (ast.Import, ast.ImportFrom))]
    assert all(not getattr(node, "module", "").startswith("tunebench") for node in imports)
    assert all(
        not alias.name.startswith("tunebench")
        for node in imports
        if isinstance(node, ast.Import)
        for alias in node.names
    )


def test_empty_and_valid_contiguous_prefix(tmp_path):
    examples = [task("one"), task("two")]
    path = tmp_path / "journal.jsonl"
    assert runner.read_journal(path, examples) == []
    prefix = [case(examples[0], repair=True)]
    journal(path, prefix)
    assert runner.read_journal(path, examples) == prefix


@pytest.mark.parametrize("mutation", ["duplicate", "gap", "truncated", "blank", "malformed"])
def test_invalid_journal_never_repaired_or_skipped(tmp_path, mutation):
    examples = [task("one"), task("two")]
    cases = [case(item) for item in examples]
    path = tmp_path / "journal.jsonl"
    if mutation == "duplicate":
        cases[1] = deepcopy(cases[0])
    elif mutation == "gap":
        cases = cases[1:]
    journal(path, cases)
    if mutation == "truncated":
        path.write_bytes(path.read_bytes()[:-1])
    elif mutation == "blank":
        path.write_text(path.read_text() + "\n")
    elif mutation == "malformed":
        path.write_text("{broken}\n")
    before = path.read_bytes()
    with pytest.raises(ValueError):
        runner.read_journal(path, examples)
    assert path.read_bytes() == before


@pytest.mark.parametrize("mutation", ["backend", "execute", "raw", "final", "last", "repairs"])
def test_tampered_response_or_decision_is_rejected(tmp_path, mutation):
    example = task()
    saved = case(example)
    response = saved["response"]
    if mutation == "backend":
        response["backend"] = "rules"
    elif mutation == "execute":
        response["tool_result"] = {"status": "success"}
    elif mutation == "raw":
        response["attempts"][0]["raw_output"] = "not JSON"
    elif mutation == "final":
        saved["final_prediction"]["outcome"] = None
    elif mutation == "last":
        response["outcome"] = {"type": "no_tool", "reason_code": "unsupported_request"}
    else:
        response["attempts"] *= 3
    path = tmp_path / "journal.jsonl"
    journal(path, [saved])
    with pytest.raises(ValueError):
        runner.read_journal(path, [example])


@pytest.mark.parametrize("stage", ["raw_parse", "accepted"])
def test_journal_never_equates_json_boolean_with_refund_amount_one(tmp_path, stage):
    example = task()
    example["expected_outcome"] = {
        "type": "tool_call",
        "tool_name": "propose_refund",
        "arguments": {"order_id": "SYNTHETIC", "reason": "damaged_item", "refund_amount": 1},
    }
    saved = case(example)
    saved["response"]["status"] = "validated"
    changed = deepcopy(example["expected_outcome"])
    changed["arguments"]["refund_amount"] = True
    if stage == "raw_parse":
        saved["response"]["attempts"][0]["raw_output"] = json.dumps(changed)
        message = "Raw output and parsed attempt differ"
    else:
        saved["response"]["accepted_outcome"] = changed
        saved["final_prediction"]["outcome"] = changed
        message = "Accepted decision differs"
    path = tmp_path / "journal.jsonl"
    journal(path, [saved])
    with pytest.raises(ValueError, match=message):
        runner.read_journal(path, [example])


def test_raw_final_denominators_repairs_and_active_timing():
    examples = [task("one"), task("two")]
    saved = [case(examples[0], repair=True), case(examples[1], blocked=True)]
    result = runner.score_cases(examples, saved, evaluate)
    assert result["raw_report"]["total_examples"] == 2
    assert result["final_report"]["total_examples"] == 2
    assert result["raw_report"]["task_success"]["correct"] == 1
    assert result["final_report"]["task_success"]["correct"] == 1
    assert result["final_report"]["invalid_predictions"] == 1
    assert result["pipeline"]["generation_attempts"] == 3
    assert result["pipeline"]["repair_attempts"] == 1
    assert result["active_seconds"] == 2.5
    with pytest.raises(ValueError):
        runner.score_cases(examples, saved[:1], evaluate)


def test_source_hashes_ignore_caches_and_detect_policy_change(tmp_path):
    (tmp_path / "pyproject.toml").write_text("version='synthetic'\n")
    source = tmp_path / "src/tunebench"
    source.mkdir(parents=True)
    (source / "assistant.py").write_text("policy = 1\n")
    baseline = runner.source_hashes(tmp_path)
    (source / "ignored.pyc").write_bytes(b"cache")
    assert runner.source_hashes(tmp_path) == baseline
    (source / "assistant.py").write_text("policy = 2\n")
    assert runner.source_hashes(tmp_path) != baseline


def test_legacy_asset_freeze_requires_pinned_upstream_identity_and_checksums(tmp_path):
    data = b"synthetic weights, no actual model"
    (tmp_path / "model.safetensors").write_bytes(data)
    manifest = {
        "model_id": "Qwen/Qwen2.5-1.5B-Instruct",
        "revision": "989aa7980e4cf806f80c7fef2b1adb7bc71aa306",
        "files": {
            "model.safetensors": {
                "size": len(data),
                "hash_algorithm": "sha256",
                "upstream_hash": runner.digest(tmp_path / "model.safetensors"),
            }
        },
    }
    runner.write(tmp_path / "download-manifest.json", manifest)
    frozen = runner.model_spec(tmp_path, "legacy")
    assert frozen["dtype"] == "float32"
    runner.verify_models({"models": {"legacy": frozen}}, full=True)
    manifest["revision"] = "unverified"
    runner.write(tmp_path / "download-manifest.json", manifest)
    with pytest.raises(ValueError, match="pinned verified"):
        runner.model_spec(tmp_path, "legacy")


def test_gguf_freeze_uses_upstream_file_hash_and_detects_later_mutation(tmp_path, monkeypatch):
    path = tmp_path / "synthetic.gguf"
    path.write_bytes(b"synthetic model data")
    expected = {
        **runner.CANDIDATE_MODEL,
        "filename": path.name,
        "size": path.stat().st_size,
        "sha256": runner.digest(path),
    }
    monkeypatch.setattr(runner, "CANDIDATE_MODEL", expected)
    frozen = runner.model_spec(path, "candidate")
    protocol = {"models": {"candidate": frozen}}
    runner.verify_models(protocol, full=True)
    original = path.stat()
    path.write_bytes(b"X" * original.st_size)
    # Even deliberately restored size/time cannot bypass the final full digest.
    os.utime(path, ns=(original.st_atime_ns, original.st_mtime_ns))
    runner.verify_models(protocol, full=False)
    with pytest.raises(ValueError, match="checksum changed"):
        runner.verify_models(protocol, full=True)
    with pytest.raises(ValueError, match="pinned upstream"):
        runner.model_spec(path, "candidate")


def test_normalized_configuration_allows_runtime_details_but_rejects_budget_change():
    runtime = {
        "loaded": True,
        "model_id": "synthetic",
        "resolved_model_revision": "test-revision",
        "weights_sha256": "a" * 64,
        "device": "cpu",
        "dtype": "Q4_K_M",
        "seed": 42,
        "cpu_threads": 4,
        "cpu_batch_threads": 4,
        "effective_generation_config": {
            **runner.SETTINGS,
            "temperature": 0.0,
            "max_tokens": 256,
            "top_p": 1.0,
            "top_k": 0,
            "min_p": 0.0,
            "repeat_penalty": 1.1,
            "stream": False,
        },
    }
    protocol = {
        "models": {
            "candidate": {
                "model_id": "synthetic",
                "revision": "test-revision",
                "weights_sha256": "a" * 64,
                "dtype": "Q4_K_M",
            }
        },
        "settings": runner.SETTINGS,
    }
    runner._runtime_shared(runtime, protocol, "candidate")
    runtime["effective_generation_config"]["max_tokens"] = 512
    with pytest.raises(ValueError, match="native decoding"):
        runner._runtime_shared(runtime, protocol, "candidate")
    runtime["effective_generation_config"]["max_tokens"] = 256
    runtime["effective_generation_config"]["max_new_tokens"] = 512
    with pytest.raises(ValueError, match="normalized decoding"):
        runner._runtime_shared(runtime, protocol, "candidate")


def test_backend_errors_remain_in_both_denominators():
    examples = [task("one"), task("two")]
    error = {
        "input": examples[1]["prompt"],
        "backend": "model",
        "execute_tools": False,
        "tool_result": None,
        "status": "error",
        "outcome": None,
        "accepted_outcome": None,
        "attempts": [],
        "elapsed_ms": 500,
    }
    raw, final = runner._predictions(examples[1], error)
    records = [
        case(examples[0]),
        {
            "example_id": examples[1]["example_id"],
            "response": error,
            "raw_first_prediction": raw,
            "final_prediction": final,
        },
    ]
    scores = runner.score_cases(examples, records, evaluate)
    assert scores["raw_report"]["task_success"] == {"correct": 1, "total": 2, "accuracy": 0.5}
    assert scores["final_report"]["task_success"] == {"correct": 1, "total": 2, "accuracy": 0.5}
    assert scores["pipeline"]["runtime_errors"] == 1
    assert scores["active_seconds"] == 1.75


def test_checkpoint_detects_changed_durable_prefix(tmp_path):
    example = task()
    path = tmp_path / "cases.partial.jsonl"
    saved = [case(example)]
    journal(path, saved)
    with pytest.raises(ValueError, match="no durable checkpoint"):
        runner.verify_checkpoint(tmp_path, path, saved)
    runner.journal_checkpoint(tmp_path, path, saved)
    runner.verify_checkpoint(tmp_path, path, saved)
    path.write_bytes(path.read_bytes().replace(b"1250", b"1251"))
    with pytest.raises(ValueError, match="differs from its durable checkpoint"):
        runner.verify_checkpoint(tmp_path, path, runner.read_journal(path, [example]))


def test_unknown_inflight_generation_never_silently_reruns(tmp_path):
    path = tmp_path / "cases.partial.jsonl"
    runner.journal_checkpoint(tmp_path, path, [])
    runner.write(tmp_path / "inflight.json", {"example_id": "synthetic-pending"})
    with pytest.raises(ValueError, match="generation state is unknown"):
        runner.verify_checkpoint(tmp_path, path, [])


def test_completed_prefix_with_final_backend_error_keeps_prior_runtime():
    runtime = {"loaded": True, "model_id": "synthetic-only"}
    cases = [
        {"response": {"model_metadata": runtime}},
        {"response": {"status": "error"}},
    ]
    assert runner.retained_runtime({"loaded": False}, cases) == runtime
    assert runner.retained_runtime(runtime, []) == runtime
    with pytest.raises(ValueError, match="quality readiness is unverified"):
        runner.retained_runtime({"loaded": False}, cases[1:])


@pytest.mark.parametrize("status", ["executed", "invented"])
def test_decision_only_journal_rejects_unknown_or_executed_status(tmp_path, status):
    example = task()
    saved = case(example)
    saved["response"]["status"] = status
    path = tmp_path / "cases.partial.jsonl"
    journal(path, [saved])
    with pytest.raises(ValueError, match="decision-only status"):
        runner.read_journal(path, [example])


def test_fresh_output_allows_only_parent_lock(tmp_path, monkeypatch):
    output = tmp_path / "output"
    output.mkdir()
    (output / ".runner.lock").touch()
    # Reach root inspection rather than rejecting the parent's own lock file.
    monkeypatch.setattr(
        runner,
        "source_hashes",
        lambda _root: (_ for _ in ()).throw(RuntimeError("roots inspected")),
    )
    args = SimpleNamespace(
        output=output,
        resume=False,
        legacy_root=tmp_path,
        candidate_root=tmp_path,
        legacy_model_path=tmp_path,
        candidate_model_path=tmp_path,
    )
    with pytest.raises(RuntimeError, match="roots inspected"):
        runner.freeze_or_verify(args)
    (output / "existing-report.json").write_text("{}")
    with pytest.raises(ValueError, match="fresh output"):
        runner.freeze_or_verify(args)


def test_workers_import_separate_roots_and_completed_resume_never_generates(tmp_path):
    output = tmp_path / "output"
    output.mkdir()
    examples = [task("one"), task("two")]
    journal(output / "tasks.jsonl", examples)
    (output / "dataset-manifest.json").write_text("{}")
    roots, models, runtimes = {}, {}, {}
    for version, package_version in (("legacy", "0.4-test"), ("candidate", "0.5-test")):
        model_path = tmp_path / f"{version}.synthetic"
        model_path.write_bytes(b"synthetic-test-only")
        model = {
            "path": str(model_path),
            "model_id": f"synthetic-{version}",
            "revision": "synthetic-revision",
            "dtype": "float32" if version == "legacy" else "Q4_K_M",
            "weights_sha256": runner.digest(model_path),
            "assets": {
                str(model_path): {
                    "bytes": model_path.stat().st_size,
                    "mtime_ns": model_path.stat().st_mtime_ns,
                    "sha256": runner.digest(model_path),
                }
            },
        }
        models[version] = model
        runtime = {
            "loaded": True,
            "model_id": model["model_id"],
            "resolved_model_revision": model["revision"],
            "weights_sha256": model["weights_sha256"],
            "device": "cpu",
            "dtype": model["dtype"],
            "seed": 42,
            "cpu_threads": 4,
            "cpu_interop_threads": 1,
            "cpu_batch_threads": 4,
            "effective_generation_config": {
                **runner.SETTINGS,
                "temperature": 0.0,
                "max_tokens": 256,
                "top_p": 1.0,
                "top_k": 0,
                "min_p": 0.0,
                "repeat_penalty": 1.1,
                "stream": False,
            },
        }
        runtimes[version] = runtime
        root = tmp_path / version
        package = root / "src/tunebench"
        package.mkdir(parents=True)
        roots[version] = str(root)
        (root / "pyproject.toml").write_text("# synthetic test only\n")
        (package / "__init__.py").write_text(f"__version__ = {package_version!r}\n")
        (package / "contracts.py").write_text(
            "def validate_task(task): return []\n"
            f"def load_tool_registry(): return {load_tool_registry()!r}\n"
        )
        (package / "evaluator.py").write_text(
            "def evaluate(tasks,predictions): return {'total_examples':len(tasks)}\n"
        )
        backend = "live_model.py" if version == "legacy" else "gguf_model.py"
        (package / backend).write_text(f"def model_status(): return {runtime!r}\n")
        responses = {item["prompt"]: case(item)["response"] for item in examples}
        (package / "assistant.py").write_text(
            f"responses={responses!r}\ndef respond(message,**kwargs): return responses[message]\n"
        )
        if version == "legacy":
            (root / "src/torch.py").write_text(
                "def set_num_threads(value): pass\ndef set_num_interop_threads(value): pass\n"
            )
            (root / "src/transformers.py").write_text("def set_seed(value): pass\n")
        else:
            for name in ("torch.py", "transformers.py"):
                (root / "src" / name).write_text(
                    "raise RuntimeError('Candidate worker must not import Torch or Transformers')\n"
                )
    protocol = {
        "roots": roots,
        "models": models,
        "examples": len(examples),
        "sources": {v: runner.source_hashes(Path(root)) for v, root in roots.items()},
        "runner_sha256": runner.digest(SCRIPT),
        "libraries": runner.versions(),
        "data_source": str(output / "tasks.jsonl"),
        "tasks_sha256": runner.digest(output / "tasks.jsonl"),
        "manifest_source": str(output / "dataset-manifest.json"),
        "dataset_manifest_sha256": runner.digest(output / "dataset-manifest.json"),
        "settings": runner.SETTINGS,
    }
    runner.write(output / "protocol.json", protocol)
    for version in runner.VERSIONS:
        command = [sys.executable, str(SCRIPT), "--worker", version, "--output", str(output)]
        first = subprocess.run(command, text=True, capture_output=True)
        assert first.returncode == 0, first.stderr
        saved = (output / version / "cases.partial.jsonl").read_bytes()
        resumed = subprocess.run(command, text=True, capture_output=True)
        assert resumed.returncode == 0, resumed.stderr
        assert "no generation" in resumed.stdout
        assert (output / version / "cases.partial.jsonl").read_bytes() == saved
        metadata = runner.loads((output / version / "metadata.json").read_text())
        assert metadata["source_package_version"] == (
            "0.4-test" if version == "legacy" else "0.5-test"
        )
        assert metadata["worker_events"][0]["status"] == "completed"
        assert metadata["model_runtime"] == runtimes[version]
        # A later metadata edit cannot make an error-free-looking result out of
        # a journal with different accounting; resume recomputes before reuse.
        report_path = output / version / "final.report.json"
        original = report_path.read_bytes()
        report = runner.loads(original)
        report["inference_metadata"]["active_seconds"] += 1
        runner.write(report_path, report)
        rejected = subprocess.run(command, text=True, capture_output=True)
        assert rejected.returncode != 0
        assert "metadata differs" in rejected.stderr
        assert (output / version / "cases.partial.jsonl").read_bytes() == saved
        report_path.write_bytes(original)
