"""Synthetic accounting/isolation tests; no holdout data or model weights are read."""

import ast
import importlib.util
import json
import subprocess
import sys
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace

import pytest

from tunebench.contracts import load_tool_registry
from tunebench.evaluator import evaluate

SCRIPT = Path(__file__).resolve().parents[2] / "scripts/compare_portfolio_versions.py"
SPEC = importlib.util.spec_from_file_location("portfolio_versions", SCRIPT)
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
        output=output, resume=False, legacy_root=tmp_path, candidate_root=tmp_path
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
    snapshot = tmp_path / "snapshot"
    snapshot.mkdir()
    (snapshot / "model.safetensors").write_bytes(b"synthetic-test-only")
    manifest = {
        "model_id": "Qwen/Qwen2.5-1.5B-Instruct",
        "revision": "synthetic-test-only",
        "files": {
            "model.safetensors": {
                "size": 19,
                "hash_algorithm": "sha256",
                "upstream_hash": runner.digest(snapshot / "model.safetensors"),
            }
        },
    }
    runner.write(snapshot / "download-manifest.json", manifest)
    runtime = {
        "loaded": True,
        "model_id": manifest["model_id"],
        "resolved_model_revision": manifest["revision"],
        "weights_sha256": manifest["files"]["model.safetensors"]["upstream_hash"],
        "device": "cpu",
        "dtype": "float32",
        "seed": 42,
        "cpu_threads": 4,
        "cpu_interop_threads": 1,
        "effective_generation_config": runner.SETTINGS,
    }
    roots = {}
    for version, package_version in (("legacy", "0.3-test"), ("candidate", "0.4-test")):
        root = tmp_path / version
        package = root / "src/tunebench"
        package.mkdir(parents=True)
        roots[version] = str(root)
        (root / "pyproject.toml").write_text("# synthetic test only\n")
        (package / "__init__.py").write_text(f"__version__ = {package_version!r}\n")
        (package / "contracts.py").write_text("def validate_task(task): return []\n")
        (package / "evaluator.py").write_text(
            "def evaluate(tasks,predictions): return {'total_examples':len(tasks)}\n"
        )
        (package / "live_model.py").write_text(f"def model_status(): return {runtime!r}\n")
        responses = {item["prompt"]: case(item)["response"] for item in examples}
        (package / "assistant.py").write_text(
            f"responses={responses!r}\ndef respond(message,**kwargs): return responses[message]\n"
        )
        (root / "src/torch.py").write_text(
            "def set_num_threads(value): pass\ndef set_num_interop_threads(value): pass\n"
        )
        (root / "src/transformers.py").write_text("def set_seed(value): pass\n")
    protocol = {
        "roots": roots,
        "sources": {v: runner.source_hashes(Path(root)) for v, root in roots.items()},
        "runner_sha256": runner.digest(SCRIPT),
        "libraries": runner.versions(),
        "data_source": str(output / "tasks.jsonl"),
        "tasks_sha256": runner.digest(output / "tasks.jsonl"),
        "manifest_source": str(output / "dataset-manifest.json"),
        "dataset_manifest_sha256": runner.digest(output / "dataset-manifest.json"),
        "snapshot": str(snapshot),
        "model_manifest": manifest,
        "model_manifest_sha256": runner.digest(snapshot / "download-manifest.json"),
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
            "0.3-test" if version == "legacy" else "0.4-test"
        )
        assert metadata["worker_events"][0]["status"] == "completed"
