import importlib.util
from pathlib import Path

import pytest

PATH = Path(__file__).resolve().parents[2] / "scripts/compare_semantic_versions.py"
spec = importlib.util.spec_from_file_location("semantic_runner_test", PATH)
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


def test_review_generations_are_included_in_total_cost():
    tasks = [{"example_id": "x"}]
    case = {
        "example_id": "x",
        "raw_first_prediction": {"example_id": "x", "outcome": None},
        "final_prediction": {"example_id": "x", "outcome": None},
        "response": {
            "status": "blocked",
            "elapsed_ms": 10,
            "attempts": [{}, {}],
            "semantic_verifications": [{}, {}],
        },
    }
    r = runner.score_cases(tasks, [case], lambda *_: {})["pipeline"]
    assert r["generation_attempts"] == 2
    assert r["review_generations"] == 2
    assert r["total_generation_records"] == 4


def _reviewed_case():
    import json

    outcome = {"type": "no_tool", "reason_code": "informational_request"}
    judgement = {"reason": "Advice question", "calculation": None, "verdict": "supported"}
    response = {
        "backend": "model",
        "execute_tools": False,
        "input": "What is tracking?",
        "status": "no_tool",
        "tool_result": None,
        "elapsed_ms": 10,
        "execution_guard_policy": "schema-literal-and-semantic-review-v1",
        "outcome": outcome,
        "accepted_outcome": outcome,
        "attempts": [
            {
                "attempt": 1,
                "repair": False,
                "raw_output": json.dumps(outcome),
                "parsed_outcome": outcome,
            }
        ],
        "semantic_verifications": [
            {
                **judgement,
                "raw_output": json.dumps(judgement),
                "primary_attempt": 1,
                "weights_sha256": runner.SHARED_MODEL["sha256"],
            }
        ],
    }
    task = {"example_id": "x", "prompt": response["input"]}
    raw, final = runner._predictions(task, response)
    return task, {
        "example_id": "x",
        "response": response,
        "raw_first_prediction": raw,
        "final_prediction": final,
    }


def test_valid_review_journal_round_trips_without_rewriting(tmp_path):
    import json

    task, case = _reviewed_case()
    path = tmp_path / "cases.jsonl"
    path.write_text(json.dumps(case) + "\n")
    assert runner.read_journal(path, [task]) == [case]


@pytest.mark.parametrize("corruption", ["raw", "duplicate", "verdict", "arithmetic", "weights"])
def test_tampered_or_unsupported_review_cannot_be_accepted(tmp_path, corruption):
    import json

    task, case = _reviewed_case()
    response = case["response"]
    review = response["semantic_verifications"][0]
    if corruption == "raw":
        review["reason"] = "Changed after generation"
    elif corruption == "duplicate":
        response["semantic_verifications"].append(dict(review))
    elif corruption == "verdict":
        review["verdict"] = "contradicted"
        review["raw_output"] = json.dumps(
            {k: review[k] for k in ("reason", "calculation", "verdict")}
        )
    elif corruption == "arithmetic":
        review["calculation_error"] = "Mismatch"
    else:
        review["weights_sha256"] = "different weights"
    path = tmp_path / "cases.jsonl"
    path.write_text(json.dumps(case) + "\n")
    with pytest.raises(ValueError):
        runner.read_journal(path, [task])
