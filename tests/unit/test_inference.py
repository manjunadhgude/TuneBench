import json
from copy import deepcopy

import pytest

from tunebench.contracts import load_tool_registry, validate_prediction
from tunebench.inference import build_messages, generate_predictions, parse_output


@pytest.fixture
def inference_task():
    return {
        "schema_version": "3.0.0",
        "example_id": "secret-example-label",
        "family_id": "secret-family-label",
        "scenario_id": "secret-scenario-label",
        "split": "validation",
        "difficulty": "easy",
        "prompt": "Where is order A123?",
        "tools": load_tool_registry(),
        "expected_outcome": {
            "type": "tool_call",
            "tool_name": "get_order_status",
            "arguments": {"order_id": "SECRET-GOLD-ARGUMENT"},
        },
        "provenance": {"source_type": "manual", "reviewed_by": "secret-reviewer"},
    }


def test_prompt_never_includes_labels_or_benchmark_metadata(inference_task):
    for style in ("minimal", "strong"):
        messages = build_messages(inference_task, style)
        text = json.dumps(messages)
        for secret in (
            "secret-example-label",
            "secret-family-label",
            "secret-scenario-label",
            "SECRET-GOLD-ARGUMENT",
            "secret-reviewer",
            "expected_outcome",
        ):
            assert secret not in text
        assert messages[-1] == {"role": "user", "content": inference_task["prompt"]}
        assert "propose_refund" in messages[0]["content"]


def test_prompt_is_unchanged_when_gold_changes(inference_task):
    changed = deepcopy(inference_task)
    changed["expected_outcome"] = {"type": "no_tool", "reason_code": "unsupported_request"}
    assert build_messages(changed) == build_messages(inference_task)


@pytest.mark.parametrize(
    "output",
    [
        "not JSON",
        '```json\n{"type":"no_tool","reason_code":"unsupported_request"}\n```',
        '[{"type":"no_tool"}]',
        '{"type":"no_tool","type":"tool_call"}',
        '{"arguments":{"refund_amount":NaN}}',
        '{"arguments":{"refund_amount":Infinity}}',
        '{"arguments":{"refund_amount":1e999}}',
        '{"type":"no_tool"} trailing words',
    ],
)
def test_invalid_json_retains_original_output_without_repair(output):
    record = parse_output("test-001", output)
    assert record["outcome"] is None
    assert record["raw_output"] == output
    assert record["metadata"]["parse_error"]
    assert validate_prediction(record) == []


def test_wrong_outcome_schema_retains_parsed_evidence():
    record = parse_output("test-001", '{"made_up":"shape"}')
    assert record["outcome"] == {"made_up": "shape"}
    assert validate_prediction(record)


def test_single_generation_and_latency_without_retry(inference_task):
    calls = []

    def backend(messages):
        calls.append(messages)
        return "bad model response"

    predictions = generate_predictions([inference_task], backend)
    assert len(calls) == 1
    record = predictions[0]
    assert record["outcome"] is None
    assert record["metadata"]["attempts"] == 1
    assert record["latency_ms"] >= 0
    assert record["raw_output"] == "bad model response"


def test_runtime_errors_propagate_instead_of_becoming_model_failures(inference_task):
    def backend(_messages):
        raise RuntimeError("out of memory")

    with pytest.raises(RuntimeError, match="out of memory"):
        generate_predictions([inference_task], backend)


def test_duplicate_tasks_fail_before_any_generation(inference_task):
    calls = []
    with pytest.raises(ValueError, match="duplicate example_id"):
        generate_predictions(
            [inference_task, inference_task], lambda messages: calls.append(messages)
        )
    assert calls == []


def test_empty_inference_is_rejected():
    with pytest.raises(ValueError, match="empty"):
        generate_predictions([], lambda messages: "{}")
