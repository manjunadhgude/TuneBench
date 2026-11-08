import json
import subprocess
import sys


def run(*args):
    return subprocess.run(
        [sys.executable, "-m", "tunebench", *map(str, args)], capture_output=True, text=True
    )


def test_demo_and_paired_comparison(tmp_path):
    directory = tmp_path / "demo"
    result = run("demo", "--output", directory)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["corrupted_correct"] == 18
    oracle = json.loads((directory / "oracle-report.json").read_text())
    flawed = json.loads((directory / "corrupted-report.json").read_text())
    assert oracle["task_schema_version"] == "3.0.0"
    assert flawed["missing_predictions"] == 1
    assert flawed["invalid_predictions"] == 2
    result = run(
        "compare",
        "--baseline",
        directory / "corrupted-report.json",
        "--candidate",
        directory / "oracle-report.json",
        "--output",
        tmp_path / "comparison.json",
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["accuracy_delta"] == 0.1


def test_cli_failure_has_nonzero_status_and_preserves_outputs(tmp_path):
    directory = tmp_path / "demo"
    assert run("demo", "--output", directory).returncode == 0
    result = run("demo", "--output", directory)
    assert result.returncode == 2
    assert "not empty" in result.stderr
    result = run(
        "evaluate",
        "--gold",
        tmp_path / "missing",
        "--predictions",
        tmp_path / "missing",
        "--output",
        tmp_path / "report.json",
    )
    assert result.returncode == 2
    assert not (tmp_path / "report.json").exists()


def test_full_generate_audit_export_and_tamper_detection(tmp_path):
    directory = tmp_path / "data"
    result = run("generate", "--full", "--output", directory)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["manifest"]["audit"]["total_examples"] == 1250
    assert run("audit", "--data-dir", directory).returncode == 0
    result = run("export-training", "--data-dir", directory, "--output", tmp_path / "training")
    assert result.returncode == 0, result.stderr
    exported = json.loads(result.stdout)
    assert exported["test_included"] is False
    assert exported["files"]["train"]["examples"] == 1000
    path = directory / "validation.jsonl"
    path.write_text(path.read_text().replace("wrong_item", "changed_mind", 1))
    result = run("audit", "--data-dir", directory)
    assert result.returncode == 2
    assert "checksum mismatch" in result.stderr


def test_inference_test_gate_precedes_model_loading(tmp_path):
    from tunebench.dataset import generate_dataset
    from tunebench.io import write_jsonl

    path = tmp_path / "test.jsonl"
    write_jsonl(path, generate_dataset()["test"][:1])
    result = run("infer", "--tasks", path, "--output", tmp_path / "predictions.jsonl")
    assert result.returncode == 2
    assert "--allow-test" in result.stderr


def test_evaluation_sidecar_checks_task_hash_and_preserves_settings(tmp_path):
    import hashlib

    directory = tmp_path / "demo"
    assert run("demo", "--output", directory).returncode == 0
    gold = directory / "smoke.jsonl"
    predictions = directory / "oracle-fixture.jsonl"
    metadata = {
        "tasks_sha256": hashlib.sha256(gold.read_bytes()).hexdigest(),
        "decoding": {"max_new_tokens": 256},
    }
    sidecar = directory / "oracle-fixture.jsonl.metadata.json"
    sidecar.write_text(json.dumps(metadata))
    output = tmp_path / "report.json"
    args = ("evaluate", "--gold", gold, "--predictions", predictions, "--output", output)
    result = run(*args)
    assert result.returncode == 0, result.stderr
    assert json.loads(output.read_text())["inference_metadata"] == metadata
    metadata["tasks_sha256"] = "tampered"
    sidecar.write_text(json.dumps(metadata))
    result = run(*args)
    assert result.returncode == 2
    assert "does not match" in result.stderr


def test_malformed_manifest_and_comparison_fail_without_tracebacks(tmp_path):
    directory = tmp_path / "data"
    assert run("generate", "--output", directory).returncode == 0
    (directory / "manifest.json").write_text("[]")
    result = run("audit", "--data-dir", directory)
    assert result.returncode == 2
    assert "Manifest must be an object" in result.stderr
    malformed = tmp_path / "malformed.json"
    malformed.write_text("[]")
    result = run(
        "compare",
        "--baseline",
        malformed,
        "--candidate",
        malformed,
        "--output",
        tmp_path / "report.json",
    )
    assert result.returncode == 2
    assert "Traceback" not in result.stderr
