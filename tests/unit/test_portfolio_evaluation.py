"""Accounting and freeze checks use synthetic responses, never model generation."""

import importlib.util
import json
import sys
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace

import pytest

from tunebench.contracts import load_tool_registry
from tunebench.io import write_json, write_jsonl

_SCRIPT = Path(__file__).resolve().parents[2] / "scripts/evaluate_portfolio.py"
_SPEC = importlib.util.spec_from_file_location("portfolio_evaluation", _SCRIPT)
evaluation = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(evaluation)


def task(identifier="case-1", *, outcome=None, split="validation"):
    return {
        "schema_version": "3.0.0",
        "example_id": identifier,
        "family_id": f"family-{identifier}",
        "scenario_id": f"scenario-{identifier}",
        "split": split,
        "difficulty": "medium",
        "prompt": "Get the current status of order TEST-100.",
        "tools": load_tool_registry(),
        "expected_outcome": outcome
        or {
            "type": "tool_call",
            "tool_name": "get_order_status",
            "arguments": {"order_id": "TEST-100"},
        },
    }


def attempt(outcome, *, raw=None, repair=False):
    return {
        "attempt": 2 if repair else 1,
        "repair": repair,
        "raw_output": raw if raw is not None else json.dumps(outcome),
        "parsed_outcome": outcome,
        "validation_errors": [],
        "schema_valid": outcome is not None,
        "latency_ms": 1,
    }


def response(outcome, *, attempts=None, status="validated", backend="model"):
    return {
        "backend": backend,
        "outcome": outcome,
        "accepted_outcome": outcome,
        "attempts": attempts if attempts is not None else [attempt(outcome)],
        "status": status,
        "tool_result": None,
        "elapsed_ms": 1,
    }


def test_raw_repair_and_final_decision_are_distinct_and_all_cases_count():
    tasks = [task(f"case-{number}") for number in range(4)]
    correct = tasks[0]["expected_outcome"]
    invalid = {"type": "tool_call", "tool_name": "invented_tool", "arguments": {}}
    responses = iter(
        [
            response(
                correct, attempts=[attempt(None, raw="not json"), attempt(correct, repair=True)]
            ),
            # Even a schema-correct last parsed outcome is not an accepted decision.
            {**response(correct, status="blocked"), "accepted_outcome": None},
            response(invalid, status="blocked"),
            RuntimeError("synthetic backend failure"),
        ]
    )
    calls = []
    checkpoints = []

    def responder(message, **kwargs):
        calls.append((message, kwargs))
        result = next(responses)
        if isinstance(result, Exception):
            raise result
        return result

    result = evaluation.collect_cases(
        tasks, responder, backend="model", checkpoint=checkpoints.append
    )
    assert len(result["cases"]) == len(checkpoints) == len(calls) == 4
    assert all(kwargs["execute_tools"] is False for _, kwargs in calls)
    assert result["raw_report"]["total_examples"] == 4
    assert result["final_report"]["total_examples"] == 4
    assert result["raw_report"]["task_success"]["correct"] == 1
    assert result["final_report"]["task_success"]["correct"] == 1
    assert result["final_report"]["invalid_predictions"] == 3
    assert result["raw_predictions"][0]["raw_output"] == "not json"
    assert result["raw_predictions"][0]["outcome"] is None
    assert result["final_predictions"][0]["outcome"] == correct
    assert result["final_predictions"][1]["outcome"] is None
    assert result["final_predictions"][2]["outcome"] is None
    assert result["cases"][3]["response"]["runtime_error"]["type"] == "RuntimeError"
    assert result["pipeline"]["cases_with_repair"] == 1
    assert result["pipeline"]["repair_attempts"] == 1
    assert result["pipeline"]["generation_attempts"] == 4
    assert result["pipeline"]["runtime_error_cases"] == 1
    assert result["pipeline"]["tool_execution_enabled"] is False


def test_clarification_prediction_keeps_required_question_field():
    gold = {
        "type": "clarification",
        "target_tool_name": "get_order_status",
        "missing_fields": ["order_id"],
        "reason_code": "missing_required_information",
    }
    example = task(outcome=gold)
    prediction = {**gold, "question": "Which order should I check?"}
    result = evaluation.collect_cases(
        [example], lambda *_args, **_kwargs: response(prediction), backend="model"
    )
    assert result["raw_report"]["invalid_predictions"] == 0
    assert result["final_report"]["task_success"]["correct"] == 1


def test_injected_responder_cannot_be_reported_as_actual_model():
    example = task()
    result = evaluation.collect_cases(
        [example],
        lambda *_args, **_kwargs: response(example["expected_outcome"], backend="injected"),
        backend="model",
    )
    assert result["final_report"]["task_success"]["correct"] == 0
    assert result["pipeline"]["runtime_error_cases"] == 1
    assert "backend differs" in result["cases"][0]["response"]["runtime_error"]["message"]


def test_checkpoint_failure_aborts_instead_of_rerunning():
    example = task()
    calls = []

    def responder(*_args, **_kwargs):
        calls.append(1)
        return response(example["expected_outcome"])

    def checkpoint(_case):
        raise OSError("synthetic full disk")

    with pytest.raises(OSError, match="full disk"):
        evaluation.collect_cases(
            [example, task("case-2")], responder, backend="model", checkpoint=checkpoint
        )
    assert len(calls) == 1


def test_holdout_requires_matching_manifest_and_all_ids_are_retained(tmp_path):
    data = tmp_path / "holdout.jsonl"
    tasks = [task("holdout-1", split="test"), task("holdout-2", split="test")]
    write_jsonl(data, tasks)
    with pytest.raises(ValueError, match="requires a frozen"):
        evaluation._manifest_for(data, tasks)
    entry = {
        "path": data.name,
        "sha256": evaluation.sha256(data),
        "examples": 2,
        "bytes": data.stat().st_size,
    }
    manifest = {"dataset_id": "synthetic-test-only", "files": {"holdout": entry}}
    write_json(tmp_path / "manifest.json", manifest)
    assert evaluation._manifest_for(data, tasks)[1] == manifest
    changed = deepcopy(manifest)
    changed["files"]["holdout"]["sha256"] = "0" * 64
    write_json(tmp_path / "manifest.json", changed)
    with pytest.raises(ValueError, match="checksum"):
        evaluation._manifest_for(data, tasks)


def test_protocol_precedes_responder_and_existing_output_is_preserved(tmp_path, monkeypatch):
    data = tmp_path / "development.jsonl"
    output = tmp_path / "evaluation"
    example = task()
    write_jsonl(data, [example])
    calls = []

    def responder(_message, **kwargs):
        protocol = json.loads((output / "protocol.json").read_text())
        assert protocol["status"] == "frozen_before_generation"
        assert protocol["tasks_sha256"] == evaluation.sha256(data)
        assert protocol["model_id"] is None
        assert protocol["source_files_sha256"]["scripts/evaluate_portfolio.py"]
        assert protocol["source_files_sha256"]["src/tunebench/grounding.py"]
        assert protocol["source_files_sha256"]["src/tunebench/prompts_v3.py"]
        assert protocol["source_files_sha256"]["src/tunebench/structured.py"]
        assert "lm-format-enforcer" in protocol["libraries"]
        assert protocol["prompt_style"] == "rules-v2"
        assert protocol["structured_output"]["enabled"] is False
        assert protocol["repair_policy"]["max_repairs"] == 0
        assert json.loads((output / "first-attempt.messages.json").read_text()) == []
        assert kwargs["execute_tools"] is False
        calls.append(1)
        return response(example["expected_outcome"], backend="rules")

    from tunebench import assistant

    monkeypatch.setattr(assistant, "respond", responder)
    result = evaluation.run_evaluation(
        data, output, backend="rules", model_path=None, max_repairs=1
    )
    assert result["results"][0]["label"] == "Deterministic rules baseline (not an LLM)"
    assert result["results"][0]["strict_correct"] == 1
    assert result["pipeline"]["generation_attempts"] == 0
    assert len((output / "cases.partial.jsonl").read_text().splitlines()) == 1
    assert (output / "final.report.json").is_file()
    with pytest.raises(ValueError, match="fresh output directory"):
        evaluation.run_evaluation(data, output, backend="rules", model_path=None, max_repairs=1)
    assert len(calls) == 1


def test_model_protocol_freezes_actual_v3_messages_and_bounded_evidence_repair(
    tmp_path, monkeypatch
):
    # Synthetic backend captures exercise metadata without loading any weights.
    monkeypatch.setitem(
        sys.modules,
        "torch",
        SimpleNamespace(set_num_threads=lambda _: None, set_num_interop_threads=lambda _: None),
    )
    monkeypatch.setitem(sys.modules, "transformers", SimpleNamespace(set_seed=lambda _: None))
    data = tmp_path / "development.jsonl"
    output = tmp_path / "evaluation"
    snapshot = tmp_path / "snapshot"
    snapshot.mkdir()
    example = task()
    write_jsonl(data, [example])
    manifest = {
        "model_id": "synthetic-test-only",
        "revision": "a" * 40,
        "files": {"model.safetensors": {"upstream_hash": "b" * 64}},
    }
    write_json(snapshot / "download-manifest.json", manifest)
    write_json(snapshot / "generation_config.json", {})
    from tunebench import assistant, live_model

    monkeypatch.setattr(live_model, "verify_local_snapshot", lambda _path: manifest)
    monkeypatch.setattr(live_model, "model_status", lambda: {"loaded": True})

    def responder(message, **_kwargs):
        protocol = json.loads((output / "protocol.json").read_text())
        messages = json.loads((output / "first-attempt.messages.json").read_text())
        assert messages == [evaluation.build_messages(example, "strong-v3")]
        assert messages[0][-1]["content"] == message
        assert protocol["protocol_version"] == "portfolio-decision-evaluation-v2"
        assert protocol["prompt_style"] == "strong-v3"
        assert protocol["structured_output"]["enabled"] is True
        assert protocol["structured_output"]["post_validation_required"] is True
        schema = evaluation.generation_schema()
        expected_hash = evaluation.hashlib.sha256(
            json.dumps(schema, sort_keys=True).encode()
        ).hexdigest()
        assert protocol["structured_output"]["schema_sha256"] == expected_hash
        assert protocol["repair_policy"]["max_repairs"] == 1
        assert "explicit_evidence_error" in protocol["repair_policy"]["triggers"]
        assert protocol["repair_policy"]["output_rewriting"] is False
        assert protocol["execution_guard_policy"] == "evidence-grounding-v2"
        return response(example["expected_outcome"])

    monkeypatch.setattr(assistant, "respond", responder)
    result = evaluation.run_evaluation(
        data, output, backend="model", model_path=snapshot, max_repairs=1
    )
    assert result["quality_claims_validated"] is True
    assert result["results"][0]["strict_correct"] == 1


def test_policy_mutation_stops_after_journaling_completed_case(tmp_path, monkeypatch):
    data = tmp_path / "development.jsonl"
    output = tmp_path / "evaluation"
    source = tmp_path / "policy.py"
    source.write_text("policy = 'frozen'\n")
    example = task()
    write_jsonl(data, [example, task("case-2")])
    monkeypatch.setattr(evaluation, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(evaluation, "_sources", lambda: [source])

    def responder(_message, **_kwargs):
        source.write_text("policy = 'changed'\n")
        return response(example["expected_outcome"], backend="rules")

    from tunebench import assistant

    monkeypatch.setattr(assistant, "respond", responder)
    with pytest.raises(ValueError, match="source or policy changed"):
        evaluation.run_evaluation(data, output, backend="rules", model_path=None, max_repairs=1)
    assert len((output / "cases.partial.jsonl").read_text().splitlines()) == 1
    assert not (output / "final.report.json").exists()
