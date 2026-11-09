"""Resume accounting tests use synthetic captures and never invoke generation."""

import importlib.util
import json
from copy import deepcopy
from pathlib import Path

import pytest

from tunebench.contracts import load_tool_registry

_SCRIPT = Path(__file__).resolve().parents[2] / "scripts/resume_portfolio_evaluation.py"
_SPEC = importlib.util.spec_from_file_location("portfolio_resume", _SCRIPT)
resume = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(resume)


def task(identifier):
    return {
        "schema_version": "3.0.0",
        "example_id": identifier,
        "family_id": f"family-{identifier}",
        "scenario_id": f"scenario-{identifier}",
        "split": "test",
        "difficulty": "medium",
        "prompt": f"Get the status of order {identifier}.",
        "tools": load_tool_registry(),
        "expected_outcome": {
            "type": "tool_call",
            "tool_name": "get_order_status",
            "arguments": {"order_id": identifier},
        },
    }


def protocol(tasks):
    return {
        "protocol_version": "portfolio-decision-evaluation-v1",
        "status": "frozen_before_generation",
        "backend": "model",
        "backend_label": "Local Qwen with validation and bounded repair",
        "examples": len(tasks),
        "example_ids_in_order": [item["example_id"] for item in tasks],
        "max_repairs": 1,
        "execute_tools": False,
        "created_at_utc": "2026-11-08T22:10:40+00:00",
        "dataset_id": "synthetic-resume-tests",
        "tasks_sha256": "0" * 64,
    }


def case(example, *, blocked=False, invalid_raw=False, elapsed_ms=1000):
    outcome = deepcopy(example["expected_outcome"])
    parsed = None if invalid_raw else outcome
    accepted = None if blocked else outcome
    attempts = [
        {
            "attempt": 1,
            "repair": False,
            "raw_output": "malformed" if invalid_raw else json.dumps(outcome),
            "parsed_outcome": parsed,
            "validation_errors": ["invalid JSON"] if invalid_raw else [],
            "schema_valid": not invalid_raw,
            "latency_ms": elapsed_ms,
        }
    ]
    if invalid_raw and not blocked:
        attempts.append(
            {
                "attempt": 2,
                "repair": True,
                "raw_output": json.dumps(outcome),
                "parsed_outcome": outcome,
                "validation_errors": [],
                "schema_valid": True,
                "latency_ms": 1,
            }
        )
    return {
        "example_id": example["example_id"],
        "response": {
            "backend": "model",
            "input": example["prompt"],
            "status": "blocked" if blocked else "validated",
            "outcome": parsed if blocked else outcome,
            "accepted_outcome": accepted,
            "attempts": attempts,
            "validation_errors": ["blocked"] if blocked else [],
            "tool_result": None,
            "elapsed_ms": elapsed_ms,
            "execute_tools": False,
            "execution_mode": "validation_only",
        },
        "raw_first_prediction": {
            "example_id": example["example_id"],
            "outcome": parsed,
            "raw_output": attempts[0]["raw_output"],
            "metadata": {"stage": "first_attempt", "backend": "model"},
        },
        "final_prediction": {
            "example_id": example["example_id"],
            "outcome": accepted,
            "metadata": {"stage": "accepted_final_decision", "backend": "model"},
        },
    }


def journal(cases):
    return "".join(json.dumps(item) + "\n" for item in cases).encode()


def test_valid_contiguous_journal_preserves_cases_including_rejection_and_repair():
    tasks = [task(f"TEST-{number}") for number in range(4)]
    cases = [case(tasks[0], blocked=True), case(tasks[1], invalid_raw=True)]
    data = journal(cases)
    assert resume.validate_journal(data, tasks, protocol(tasks)) == cases
    assert data == journal(cases)


@pytest.mark.parametrize("kind", ["duplicate", "gap", "truncated", "malformed", "blank"])
def test_invalid_prefix_is_rejected_without_touching_original_bytes(kind):
    tasks = [task(f"TEST-{number}") for number in range(3)]
    first = case(tasks[0])
    if kind == "duplicate":
        data = journal([first, first])
    elif kind == "gap":
        data = journal([first, case(tasks[2])])
    elif kind == "truncated":
        data = journal([first])[:-1]
    elif kind == "malformed":
        data = journal([first]) + b"{invalid}\n"
    else:
        data = journal([first]) + b"\n"
    before = bytes(data)
    with pytest.raises(ValueError):
        resume.validate_journal(data, tasks, protocol(tasks))
    assert data == before


@pytest.mark.parametrize("mutation", ["raw", "final", "backend", "execution", "repairs"])
def test_journal_cannot_change_original_raw_or_accepted_decision(mutation):
    tasks = [task("TEST-1"), task("TEST-2")]
    captured = case(tasks[0], blocked=True)
    if mutation == "raw":
        captured["raw_first_prediction"]["outcome"] = None
    elif mutation == "final":
        captured["final_prediction"]["outcome"] = tasks[0]["expected_outcome"]
    elif mutation == "backend":
        captured["response"]["backend"] = "injected"
    elif mutation == "execution":
        captured["response"]["tool_result"] = {"status": "success"}
    else:
        captured["response"]["attempts"] *= 3
    with pytest.raises(ValueError):
        resume.validate_journal(journal([captured]), tasks, protocol(tasks))


def test_finalization_counts_all_original_and_resumed_cases_and_excludes_idle_time(tmp_path):
    tasks = [task("TEST-1"), task("TEST-2"), task("TEST-3")]
    captures = [
        case(tasks[0], elapsed_ms=1200),
        case(tasks[1], blocked=True, elapsed_ms=2300),
        case(tasks[2], invalid_raw=True, elapsed_ms=3400),
    ]
    events = [
        {
            "started_at_utc": "2026-11-09T02:10:40+00:00",
            "completed_at_utc": "2026-11-09T02:11:40+00:00",
            "pid": 999999,
            "preserved_cases": 1,
            "remaining_cases": 2,
        }
    ]
    summary = resume.finalize_run(
        tmp_path,
        protocol(tasks),
        tasks,
        captures,
        {"loaded": True, "model_id": "synthetic-test-double"},
        events,
        "1" * 64,
    )
    report = json.loads((tmp_path / "final.report.json").read_text())
    raw = json.loads((tmp_path / "raw-first.report.json").read_text())
    metadata = json.loads((tmp_path / "metadata.json").read_text())
    assert report["total_examples"] == raw["total_examples"] == 3
    assert report["task_success"]["correct"] == 2
    assert raw["task_success"]["correct"] == 2
    assert report["invalid_predictions"] == 1
    assert metadata["elapsed_seconds"] == pytest.approx(6.9)
    assert summary["elapsed_seconds"] == pytest.approx(6.9)
    assert metadata["quality_claims_validated"] is True
    assert metadata["resumed"] is True
    assert metadata["resume_events"] == events
    assert len((tmp_path / "cases.jsonl").read_text().splitlines()) == 3
