"""Regression checks for capture versus gold-data contracts."""

from copy import deepcopy

import pytest

from tunebench.contracts import (
    load_schema,
    load_tool_registry,
    validate_prediction,
    validate_record,
    validate_task,
)


def task():
    return {
        "schema_version": "3.0.0",
        "example_id": "contract-001",
        "family_id": "contract",
        "scenario_id": "scenario-001",
        "split": "smoke",
        "difficulty": "easy",
        "prompt": "What is the status of order A123?",
        "tools": load_tool_registry(),
        "expected_outcome": {
            "type": "tool_call",
            "tool_name": "get_order_status",
            "arguments": {"order_id": "A123"},
        },
    }


def clarification(target="get_order_status", fields=None):
    return {
        "example_id": "contract-001",
        "outcome": {
            "type": "clarification",
            "target_tool_name": target,
            "missing_fields": ["order_id"] if fields is None else fields,
            "reason_code": "missing_required_information" if target else "ambiguous_intent",
            "question": "Which order do you mean?",
        },
    }


def test_valid_gold_and_prediction():
    gold = task()
    assert validate_task(gold) == []
    assert (
        validate_prediction(
            {"example_id": gold["example_id"], "outcome": gold["expected_outcome"]}, gold["tools"]
        )
        == []
    )


@pytest.mark.parametrize("field", ["schema_version", "scenario_id", "example_id"])
def test_required_gold_fields(field):
    gold = task()
    del gold[field]
    assert validate_task(gold)


@pytest.mark.parametrize("field", ["example_id", "family_id", "scenario_id", "prompt"])
def test_whitespace_gold_fields(field):
    gold = task()
    gold[field] = "   "
    assert validate_task(gold)


@pytest.mark.parametrize("arguments", [{}, {"order_id": 2}, {"order_id": "A123", "extra": 1}])
def test_tool_parameters_apply_to_gold_and_predictions(arguments):
    gold = task()
    gold["expected_outcome"]["arguments"] = arguments
    assert validate_task(gold)
    assert validate_prediction(
        {"example_id": gold["example_id"], "outcome": gold["expected_outcome"]}, gold["tools"]
    )


@pytest.mark.parametrize("amount", [0, -1, True, "5", float("nan"), float("inf")])
def test_refund_requires_positive_finite_number(amount):
    gold = task()
    gold["expected_outcome"] = {
        "type": "tool_call",
        "tool_name": "propose_refund",
        "arguments": {"order_id": "A123", "reason": "damaged_item", "refund_amount": amount},
    }
    assert validate_task(gold)


def test_invalid_embedded_schema_is_error_not_exception():
    gold = task()
    gold["tools"][0]["parameters"]["properties"]["order_id"]["type"] = "unknown-type"
    assert any("invalid JSON Schema" in error for error in validate_task(gold))


def test_cached_validation_uses_mutated_schema_content():
    gold = task()
    assert validate_task(gold) == []
    gold["tools"][0]["parameters"]["properties"]["order_id"]["type"] = "integer"
    assert validate_task(gold)
    gold["expected_outcome"]["arguments"]["order_id"] = 123
    assert validate_task(gold) == []
    gold["tools"][0]["parameters"]["properties"]["order_id"]["type"] = "invalid-type"
    assert any("invalid JSON Schema" in error for error in validate_task(gold))


def test_unknown_tool_and_duplicate_tools_rejected():
    gold = task()
    gold["expected_outcome"]["tool_name"] = "unknown"
    assert any("not in tools" in error for error in validate_task(gold))
    gold = task()
    gold["tools"].append(deepcopy(gold["tools"][0]))
    assert any("duplicate tool" in error for error in validate_task(gold))


def test_external_schema_references_are_offline_errors():
    gold = task()
    gold["tools"][0]["parameters"]["properties"]["order_id"] = {
        "$ref": "https://example.invalid/schema.json"
    }
    assert any("external schema references" in error for error in validate_task(gold))


@pytest.mark.parametrize(
    ("target", "fields", "valid"),
    [
        ("get_order_status", ["order_id"], True),
        (None, [], True),
        ("get_order_status", [], False),
        (None, ["order_id"], False),
        ("get_order_status", ["reason"], False),
        ("unknown", ["order_id"], False),
    ],
)
def test_clarification_target_and_missing_fields(target, fields, valid):
    predicted = clarification(target, fields)
    assert (validate_prediction(predicted, load_tool_registry()) == []) is valid
    gold = task()
    gold["expected_outcome"] = {k: v for k, v in predicted["outcome"].items() if k != "question"}
    assert (validate_task(gold) == []) is valid


def test_null_capture_is_distinct_from_valid_gold():
    capture = {"example_id": "bad-json", "outcome": None, "raw_output": "{oops"}
    assert validate_prediction(capture) == []
    assert validate_prediction(capture, load_tool_registry()) == []
    gold = task()
    gold["expected_outcome"] = None
    assert validate_task(gold)


def test_null_tool_capture_has_structural_but_not_semantic_validity():
    capture = {
        "example_id": "null-call",
        "outcome": {"type": "tool_call", "tool_name": None, "arguments": None},
    }
    assert validate_prediction(capture) == []
    assert validate_prediction(capture, load_tool_registry())


def test_provenance_date_format_is_checked():
    gold = task()
    gold["provenance"] = {"source_type": "synthetic", "created_at": "not-a-date"}
    assert validate_task(gold)


def test_capture_rejects_extra_fields_and_nonobjects():
    assert validate_prediction({"example_id": "x", "outcome": None, "gold": {}})
    for record in [None, [], "invalid"]:
        assert validate_record(record, "prediction.schema.json")


def test_loader_restricts_schema_names():
    with pytest.raises(ValueError, match="Unknown schema"):
        load_schema("../configs/project.json")
