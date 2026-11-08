from copy import deepcopy

import pytest

from tunebench.evaluator import evaluate


def tool_prediction(
    example_id="smoke-001",
    tool="get_order_status",
    args=None,
):
    return {
        "example_id": example_id,
        "outcome": {
            "type": "tool_call",
            "tool_name": tool,
            "arguments": {"order_id": "A123"} if args is None else args,
        },
    }


def clarification_gold(gold_record, target="get_order_status", fields=None):
    gold_record["expected_outcome"] = {
        "type": "clarification",
        "target_tool_name": target,
        "missing_fields": ["order_id"] if fields is None else fields,
        "reason_code": "missing_required_information" if target else "ambiguous_intent",
    }
    return gold_record


def no_tool_gold(gold_record):
    gold_record["expected_outcome"] = {"type": "no_tool", "reason_code": "informational_request"}
    return gold_record


def test_perfect_tool_call(gold_record):
    result = evaluate([gold_record], [tool_prediction()])
    assert result["outcome_accuracy"]["accuracy"] == 1.0
    assert result["tool_call"]["tool_selection"]["accuracy"] == 1.0
    assert result["tool_call"]["arguments_given_correct_tool"]["accuracy"] == 1.0
    assert result["tool_call"]["joint_exact_match"]["accuracy"] == 1.0


def test_wrong_tool(gold_record):
    result = evaluate([gold_record], [tool_prediction(tool="other_tool")])
    assert result["tool_call"]["tool_selection"]["accuracy"] == 0.0
    assert result["tool_call"]["arguments_given_correct_tool"]["denominator"] == 0


def test_wrong_arguments(gold_record):
    result = evaluate([gold_record], [tool_prediction(args={"order_id": "B999"})])
    assert result["tool_call"]["tool_selection"]["accuracy"] == 1.0
    assert result["tool_call"]["arguments_given_correct_tool"]["accuracy"] == 0.0
    assert result["tool_call"]["joint_exact_match"]["accuracy"] == 0.0


def test_correct_tool_with_null_arguments_keeps_tool_credit(gold_record):
    result = evaluate(
        [gold_record],
        [
            {
                "example_id": "smoke-001",
                "outcome": {
                    "type": "tool_call",
                    "tool_name": "get_order_status",
                    "arguments": None,
                },
            }
        ],
    )
    assert result["tool_call"]["tool_selection"]["accuracy"] == 1.0
    assert result["tool_call"]["arguments_given_correct_tool"]["accuracy"] == 0.0
    assert result["invalid_predictions"] == 1


def test_invalid_metadata_does_not_erase_metric_credit(gold_record):
    record = tool_prediction()
    record["metadata"] = "invalid"
    result = evaluate([gold_record], [record])
    assert result["tool_call"]["joint_exact_match"]["accuracy"] == 1.0
    assert result["invalid_predictions"] == 1


def test_correct_outcome_type_gets_credit_even_if_details_invalid(gold_record):
    result = evaluate(
        [gold_record],
        [
            {
                "example_id": "smoke-001",
                "outcome": {"type": "tool_call", "tool_name": None, "arguments": None},
            }
        ],
    )
    assert result["outcome_accuracy"]["accuracy"] == 1.0
    assert result["tool_call"]["tool_selection"]["accuracy"] == 0.0
    assert result["invalid_predictions"] == 1


def test_clarification_metrics(gold_record):
    clarification_gold(gold_record)
    prediction = {
        "example_id": "smoke-001",
        "outcome": {
            "type": "clarification",
            "target_tool_name": "get_order_status",
            "missing_fields": ["order_id"],
            "reason_code": "missing_required_information",
            "question": "What is your order ID?",
        },
    }
    result = evaluate([gold_record], [prediction])
    assert result["outcome_accuracy"]["accuracy"] == 1.0
    assert result["clarification"]["intended_tool_accuracy"]["accuracy"] == 1.0
    assert result["clarification"]["missing_fields_exact_accuracy"]["accuracy"] == 1.0
    assert result["clarification"]["missing_fields_micro"]["f1"] == 1.0


def test_clarification_question_wording_is_not_exact_match_scored(gold_record):
    clarification_gold(gold_record)
    prediction = {
        "example_id": "smoke-001",
        "outcome": {
            "type": "clarification",
            "target_tool_name": "get_order_status",
            "missing_fields": ["order_id"],
            "reason_code": "missing_required_information",
            "question": "Could you share the order number?",
        },
    }
    result = evaluate([gold_record], [prediction])
    assert result["clarification"]["missing_fields_exact_accuracy"]["accuracy"] == 1.0


def test_ambiguous_clarification_target_is_not_scored_as_tool_name(gold_record):
    clarification_gold(gold_record, target=None, fields=[])
    prediction = {
        "example_id": "smoke-001",
        "outcome": {
            "type": "clarification",
            "target_tool_name": None,
            "missing_fields": [],
            "reason_code": "ambiguous_intent",
            "question": "What would you like me to do?",
        },
    }
    result = evaluate([gold_record], [prediction])
    assert result["clarification"]["intended_tool_accuracy"]["denominator"] == 0
    assert result["clarification"]["missing_fields_exact_accuracy"]["accuracy"] == 1.0


def test_wrong_clarification_fields_are_detected(gold_record):
    clarification_gold(gold_record)
    prediction = {
        "example_id": "smoke-001",
        "outcome": {
            "type": "clarification",
            "target_tool_name": "get_order_status",
            "missing_fields": ["customer_id"],
            "reason_code": "missing_required_information",
            "question": "Which customer?",
        },
    }
    result = evaluate([gold_record], [prediction])
    assert result["clarification"]["missing_fields_exact_accuracy"]["accuracy"] == 0.0
    assert result["clarification"]["missing_fields_micro"]["f1"] == 0.0


def test_no_tool_metrics(gold_record):
    no_tool_gold(gold_record)
    prediction = {
        "example_id": "smoke-001",
        "outcome": {"type": "no_tool", "reason_code": "informational_request"},
    }
    result = evaluate([gold_record], [prediction])
    assert result["outcome_accuracy"]["accuracy"] == 1.0
    assert result["no_tool"]["recall"] == 1.0
    assert result["no_tool"]["reason_code_accuracy"]["accuracy"] == 1.0


def test_wrong_outcome_is_counted(gold_record):
    no_tool_gold(gold_record)
    result = evaluate([gold_record], [tool_prediction()])
    assert result["outcome_accuracy"]["accuracy"] == 0.0
    assert result["outcome_classification"]["confusion_matrix"]["no_tool"]["tool_call"] == 1


def test_missing_prediction_counts_as_incorrect(gold_record):
    result = evaluate([gold_record], [])
    assert result["missing_predictions"] == 1
    assert result["invalid_predictions"] == 1
    assert result["outcome_accuracy"]["accuracy"] == 0.0
    assert result["outcome_classification"]["confusion_matrix"]["tool_call"]["invalid"] == 1


def test_null_outcome_is_invalid_and_incorrect(gold_record):
    result = evaluate([gold_record], [{"example_id": "smoke-001", "outcome": None}])
    assert result["invalid_predictions"] == 1
    assert result["outcome_accuracy"]["accuracy"] == 0.0


def test_empty_gold_is_rejected():
    with pytest.raises(ValueError, match="empty"):
        evaluate([], [])


def test_duplicate_gold_ids_are_rejected(gold_record):
    with pytest.raises(ValueError, match="Duplicate gold"):
        evaluate([gold_record, gold_record], [])


def test_duplicate_prediction_ids_are_rejected(gold_record):
    with pytest.raises(ValueError, match="Duplicate prediction"):
        evaluate([gold_record], [tool_prediction(), tool_prediction()])


def test_unknown_prediction_ids_are_rejected(gold_record):
    with pytest.raises(ValueError, match="unknown"):
        evaluate([gold_record], [tool_prediction(example_id="unknown")])


def test_invalid_gold_tool_reference_is_rejected(gold_record):
    gold_record["expected_outcome"]["tool_name"] = "missing_tool"
    with pytest.raises(ValueError, match="not in tools"):
        evaluate([gold_record], [tool_prediction()])


@pytest.fixture
def gold_record():
    return {
        "schema_version": "3.0.0",
        "example_id": "smoke-001",
        "scenario_id": "scenario-001",
        "family_id": "order-status",
        "split": "smoke",
        "difficulty": "easy",
        "prompt": "Where is order A123?",
        "tools": [
            {
                "name": "get_order_status",
                "description": "Get an order status",
                "parameters": {
                    "type": "object",
                    "properties": {"order_id": {"type": "string"}},
                    "required": ["order_id"],
                    "additionalProperties": False,
                },
            }
        ],
        "expected_outcome": {
            "type": "tool_call",
            "tool_name": "get_order_status",
            "arguments": {"order_id": "A123"},
        },
    }


def clarification_prediction(target="get_order_status", fields=None):
    return {
        "example_id": "smoke-001",
        "outcome": {
            "type": "clarification",
            "target_tool_name": target,
            "missing_fields": ["order_id"] if fields is None else fields,
            "reason_code": "missing_required_information" if target else "ambiguous_intent",
            "question": "Could you clarify?",
        },
    }


def test_report_uses_current_contract_version(gold_record):
    assert evaluate([gold_record], [tool_prediction()])["task_schema_version"] == "3.0.0"


def test_wrong_available_target_excludes_field_scoring(gold_record):
    clarification_gold(gold_record)
    other = deepcopy(gold_record["tools"][0])
    other["name"] = "lookup_customer"
    gold_record["tools"].append(other)
    result = evaluate([gold_record], [clarification_prediction("lookup_customer")])
    assert result["outcome_accuracy"]["accuracy"] == 1.0
    assert result["clarification"]["intended_tool_accuracy"]["accuracy"] == 0.0
    assert result["clarification"]["missing_fields_exact_accuracy"]["denominator"] == 0
    assert result["clarification"]["missing_fields_micro"]["denominator"] == 0
    assert result["clarification"]["joint_exact_match"]["accuracy"] == 0.0
    assert result["per_example"][0]["clarification_missing_fields_exact"] is None


def test_null_gold_target_requires_null_predicted_target_for_fields(gold_record):
    clarification_gold(gold_record, target=None, fields=[])
    result = evaluate([gold_record], [clarification_prediction()])
    assert result["clarification"]["missing_fields_exact_accuracy"]["denominator"] == 0
    assert result["task_success"]["accuracy"] == 0.0
    assert result["clarification"]["intended_tool_accuracy"]["denominator"] == 0


def test_correct_null_target_is_eligible(gold_record):
    clarification_gold(gold_record, target=None, fields=[])
    result = evaluate([gold_record], [clarification_prediction(None, [])])
    assert result["clarification"]["missing_fields_exact_accuracy"]["denominator"] == 1
    assert result["task_success"]["accuracy"] == 1.0


def test_missing_clarification_still_penalizes_joint(gold_record):
    clarification_gold(gold_record)
    result = evaluate([gold_record], [])
    assert result["clarification"]["missing_fields_exact_accuracy"]["denominator"] == 0
    assert result["clarification"]["joint_exact_match"]["denominator"] == 1
    assert result["clarification"]["joint_exact_match"]["accuracy"] == 0


@pytest.mark.parametrize("outcome", [[], 3, True, "tool_call", {"type": []}, {"type": {}}])
def test_malformed_outcome_is_recorded_without_crashing(gold_record, outcome):
    result = evaluate([gold_record], [{"example_id": "smoke-001", "outcome": outcome}])
    assert result["invalid_predictions"] == 1
    assert result["task_success"]["accuracy"] == 0.0


def test_malformed_field_list_is_recorded_without_crashing(gold_record):
    clarification_gold(gold_record)
    result = evaluate([gold_record], [clarification_prediction(fields=[{}, [], 3])])
    assert result["invalid_predictions"] == 1
    assert result["task_success"]["accuracy"] == 0.0


def test_invalid_metadata_preserves_independent_credit_but_fails_success(gold_record):
    prediction = tool_prediction()
    prediction["metadata"] = "invalid"
    result = evaluate([gold_record], [prediction])
    assert result["tool_call"]["joint_exact_match"]["accuracy"] == 1.0
    assert result["task_success"]["accuracy"] == 0.0


def test_boolean_not_equal_to_numeric_argument(gold_record):
    gold_record["tools"][0]["parameters"]["properties"] = {"amount": {"type": "number"}}
    gold_record["tools"][0]["parameters"]["required"] = ["amount"]
    gold_record["expected_outcome"]["arguments"] = {"amount": 1}
    result = evaluate([gold_record], [tool_prediction(args={"amount": True})])
    assert result["invalid_predictions"] == 1
    assert result["tool_call"]["joint_exact_match"]["accuracy"] == 0.0


def test_denominators_and_breakdowns_include_every_gold_example(gold_record):
    second = deepcopy(gold_record)
    second["example_id"] = "smoke-002"
    second["scenario_id"] = "scenario-002"
    second["difficulty"] = "hard"
    result = evaluate([gold_record, second], [tool_prediction()])
    assert result["tool_call"]["joint_exact_match"]["denominator"] == 2
    assert result["tool_call"]["joint_exact_match"]["accuracy"] == 0.5
    assert result["tool_call"]["arguments_given_correct_tool"]["denominator"] == 1
    assert result["breakdown"]["difficulty"]["hard"]["task_success_accuracy"] == 0
    assert result["breakdown"]["difficulty"]["easy"]["task_success_accuracy"] == 1


@pytest.mark.parametrize("bad", [[None], [{"example_id": " "}], [3]])
def test_unindexable_prediction_record_is_input_error(gold_record, bad):
    with pytest.raises(ValueError):
        evaluate([gold_record], bad)
