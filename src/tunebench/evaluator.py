"""Deterministic evaluator for tool_call, clarification, and no_tool outcomes."""

from collections import Counter
from typing import Any

from tunebench.contracts import load_schema, validate_prediction, validate_task

OUTCOMES = ("tool_call", "clarification", "no_tool")


def _unique_index(records: list[dict[str, Any]], label: str) -> dict[str, dict]:
    indexed = {}
    for position, record in enumerate(records):
        if not isinstance(record, dict):
            raise ValueError(f"{label} record at position {position} must be an object")
        example_id = record.get("example_id")
        if not isinstance(example_id, str) or not example_id.strip():
            raise ValueError(f"{label} record at position {position} has no valid example_id")
        if example_id in indexed:
            raise ValueError(f"Duplicate {label} example_id: {example_id}")
        indexed[example_id] = record
    return indexed


def _ratio(numerator: int, denominator: int) -> float:
    return numerator / denominator if denominator else 0.0


def _prf(tp: int, fp: int, fn: int) -> dict[str, float]:
    precision = _ratio(tp, tp + fp)
    recall = _ratio(tp, tp + fn)
    f1 = _ratio(2 * precision * recall, precision + recall)
    return {"precision": precision, "recall": recall, "f1": f1}


def _json_equal(left: Any, right: Any) -> bool:
    """JSON equality without Python's boolean-as-number equivalence."""
    if isinstance(left, bool) or isinstance(right, bool):
        return type(left) is type(right) and left == right
    if isinstance(left, dict) and isinstance(right, dict):
        return left.keys() == right.keys() and all(
            _json_equal(left[key], right[key]) for key in left
        )
    if isinstance(left, list) and isinstance(right, list):
        return len(left) == len(right) and all(
            _json_equal(a, b) for a, b in zip(left, right, strict=True)
        )
    return left == right


def _breakdown(rows: list[dict[str, Any]], dimension: str) -> dict[str, Any]:
    groups: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        groups.setdefault(row[dimension], []).append(row)
    return {
        name: {
            "total": len(group),
            "outcome_accuracy": _ratio(sum(r["outcome_correct"] for r in group), len(group)),
            "task_success_accuracy": _ratio(sum(r["task_success"] for r in group), len(group)),
            "invalid_predictions": sum(not r["prediction_valid"] for r in group),
        }
        for name, group in sorted(groups.items())
    }


def evaluate(
    gold_records: list[dict[str, Any]],
    prediction_records: list[dict[str, Any]],
) -> dict[str, Any]:
    """Evaluate outcome selection and the details relevant to each outcome.

    Invalid prediction details are reported but do not erase independently
    correct outcome, tool, or field-level credit. Missing predictions are wrong.
    """
    if not gold_records:
        raise ValueError("Gold dataset is empty")

    gold = _unique_index(gold_records, "gold")
    predictions = _unique_index(prediction_records, "prediction")
    extra_ids = sorted(set(predictions) - set(gold))
    if extra_ids:
        raise ValueError(f"Predictions contain unknown example IDs: {extra_ids[:10]}")

    for example_id, record in gold.items():
        errors = validate_task(record)
        if errors:
            raise ValueError(f"Invalid gold record {example_id}: {'; '.join(errors)}")

    total = len(gold)
    confusion = {g: {p: 0 for p in OUTCOMES + ("invalid",)} for g in OUTCOMES}
    invalid_count = 0
    missing_count = 0
    error_categories = Counter()
    per_example = []

    outcome_correct = 0
    tool_total = tool_correct = 0
    argument_denominator = argument_correct = 0
    tool_joint_correct = 0
    clarification_total = clarification_target_total = clarification_target_correct = 0
    clarification_exact_fields = 0
    clarification_fields_total = 0
    clarification_field_tp = clarification_field_fp = clarification_field_fn = 0
    clarification_reason_correct = 0
    no_tool_total = no_tool_correct = no_tool_reason_correct = 0

    for example_id, expected in gold.items():
        gold_outcome = expected["expected_outcome"]
        gold_kind = gold_outcome["type"]
        predicted = predictions.get(example_id)

        if predicted is None:
            missing_count += 1
            invalid_count += 1
            error_categories["missing_prediction"] += 1
            prediction_errors = ["prediction record is missing"]
            predicted_outcome = None
            predicted_kind = "invalid"
            prediction_valid = False
        else:
            prediction_errors = validate_prediction(predicted, expected["tools"])
            predicted_outcome = predicted.get("outcome")
            if predicted_outcome is None:
                prediction_errors.append("outcome must not be null for a valid prediction")
                error_categories["null_outcome"] += 1
            predicted_kind = (
                predicted_outcome.get("type") if isinstance(predicted_outcome, dict) else None
            )
            if predicted_kind not in OUTCOMES:
                predicted_kind = "invalid"

            prediction_valid = not prediction_errors
            if not prediction_valid:
                invalid_count += 1
                error_categories["invalid_prediction"] += 1

        if predicted_kind == "invalid":
            confusion[gold_kind]["invalid"] += 1
        else:
            confusion[gold_kind][predicted_kind] += 1

        outcome_match = predicted_kind == gold_kind
        if outcome_match:
            outcome_correct += 1
        else:
            error_categories["wrong_outcome"] += 1

        row = {
            "example_id": example_id,
            "family_id": expected["family_id"],
            "scenario_id": expected["scenario_id"],
            "split": expected["split"],
            "difficulty": expected["difficulty"],
            "gold_outcome": gold_kind,
            "predicted_outcome": predicted_kind,
            "outcome_correct": outcome_match,
            "prediction_valid": prediction_valid,
            "prediction_errors": prediction_errors,
        }

        if gold_kind == "tool_call":
            tool_total += 1
            expected_name = gold_outcome["tool_name"]
            expected_args = gold_outcome["arguments"]
            predicted_name = (
                predicted_outcome.get("tool_name") if predicted_kind == "tool_call" else None
            )
            predicted_args = (
                predicted_outcome.get("arguments") if predicted_kind == "tool_call" else None
            )
            tool_match = (
                predicted_kind == "tool_call"
                and isinstance(predicted_name, str)
                and predicted_name == expected_name
            )
            args_match = (
                tool_match
                and isinstance(predicted_args, dict)
                and _json_equal(predicted_args, expected_args)
            )
            if tool_match:
                tool_correct += 1
                argument_denominator += 1
                if args_match:
                    argument_correct += 1
            if args_match:
                tool_joint_correct += 1
            row.update(
                {
                    "tool_correct": bool(tool_match),
                    "arguments_correct": bool(args_match),
                    "tool_call_joint_correct": bool(args_match),
                    "task_success": bool(args_match and prediction_valid),
                }
            )

        elif gold_kind == "clarification":
            clarification_total += 1
            expected_target = gold_outcome["target_tool_name"]
            expected_fields = set(gold_outcome["missing_fields"])
            if expected_target is not None:
                clarification_target_total += 1

            pred_target = (
                predicted_outcome.get("target_tool_name")
                if predicted_kind == "clarification"
                else None
            )
            pred_fields_value = (
                predicted_outcome.get("missing_fields", [])
                if predicted_kind == "clarification"
                else []
            )
            pred_fields = (
                set(x for x in pred_fields_value if isinstance(x, str))
                if isinstance(pred_fields_value, list)
                else set()
            )
            target_match = (
                expected_target is not None
                and predicted_kind == "clarification"
                and pred_target == expected_target
            )
            if target_match:
                clarification_target_correct += 1

            fields_eligible = predicted_kind == "clarification" and (
                target_match if expected_target is not None else pred_target is None
            )
            fields_match = fields_eligible and pred_fields == expected_fields
            if fields_eligible:
                clarification_fields_total += 1
                clarification_field_tp += len(expected_fields & pred_fields)
                clarification_field_fp += len(pred_fields - expected_fields)
                clarification_field_fn += len(expected_fields - pred_fields)
                if fields_match:
                    clarification_exact_fields += 1

            reason_match = (
                predicted_kind == "clarification"
                and predicted_outcome.get("reason_code") == gold_outcome["reason_code"]
            )
            if reason_match:
                clarification_reason_correct += 1
            row.update(
                {
                    "clarification_target_correct": (
                        bool(target_match) if expected_target is not None else None
                    ),
                    "clarification_missing_fields_exact": bool(fields_match)
                    if fields_eligible
                    else None,
                    "clarification_reason_correct": bool(reason_match),
                    "task_success": bool(fields_match and reason_match and prediction_valid),
                }
            )

        else:
            no_tool_total += 1
            reason_match = (
                predicted_kind == "no_tool"
                and predicted_outcome.get("reason_code") == gold_outcome["reason_code"]
            )
            if predicted_kind == "no_tool":
                no_tool_correct += 1
            if reason_match:
                no_tool_reason_correct += 1
            row["no_tool_reason_correct"] = bool(reason_match)
            row["task_success"] = bool(reason_match and prediction_valid)

        row["end_to_end_correct"] = row["task_success"]
        per_example.append(row)

    class_metrics = {}
    f1_values = []
    for kind in OUTCOMES:
        tp = confusion[kind][kind]
        fp = sum(confusion[other][kind] for other in OUTCOMES if other != kind)
        fn = sum(confusion[kind][other] for other in OUTCOMES if other != kind)
        fn += confusion[kind]["invalid"]
        metrics = _prf(tp, fp, fn)
        class_metrics[kind] = {
            "support": sum(confusion[kind].values()),
            **metrics,
        }
        f1_values.append(metrics["f1"])

    field_metrics = _prf(
        clarification_field_tp,
        clarification_field_fp,
        clarification_field_fn,
    )

    return {
        "evaluation_version": "0.2.0",
        "task_schema_version": load_schema("task.schema.json")["properties"]["schema_version"][
            "const"
        ],
        "total_examples": total,
        "prediction_records": len(predictions),
        "missing_predictions": missing_count,
        "invalid_predictions": invalid_count,
        "task_success": {
            "correct": sum(row["task_success"] for row in per_example),
            "total": total,
            "accuracy": _ratio(sum(row["task_success"] for row in per_example), total),
        },
        "outcome_accuracy": {
            "correct": outcome_correct,
            "total": total,
            "accuracy": _ratio(outcome_correct, total),
        },
        "outcome_classification": {
            "labels": list(OUTCOMES),
            "confusion_matrix": confusion,
            "per_class": class_metrics,
            "macro_f1": _ratio(sum(f1_values), len(f1_values)),
        },
        "tool_call": {
            "total": tool_total,
            "tool_selection": {
                "correct": tool_correct,
                "denominator": tool_total,
                "accuracy": _ratio(tool_correct, tool_total),
            },
            "arguments_given_correct_tool": {
                "correct": argument_correct,
                "denominator": argument_denominator,
                "accuracy": _ratio(argument_correct, argument_denominator),
            },
            "joint_exact_match": {
                "correct": tool_joint_correct,
                "denominator": tool_total,
                "accuracy": _ratio(tool_joint_correct, tool_total),
            },
        },
        "clarification": {
            "total": clarification_total,
            "intended_tool_accuracy": {
                "correct": clarification_target_correct,
                "denominator": clarification_target_total,
                "accuracy": _ratio(clarification_target_correct, clarification_target_total),
            },
            "missing_fields_exact_accuracy": {
                "correct": clarification_exact_fields,
                "denominator": clarification_fields_total,
                "accuracy": _ratio(clarification_exact_fields, clarification_fields_total),
            },
            "missing_fields_micro": {**field_metrics, "denominator": clarification_fields_total},
            "joint_exact_match": {
                "correct": sum(
                    r["task_success"] for r in per_example if r["gold_outcome"] == "clarification"
                ),
                "denominator": clarification_total,
                "accuracy": _ratio(
                    sum(
                        r["task_success"]
                        for r in per_example
                        if r["gold_outcome"] == "clarification"
                    ),
                    clarification_total,
                ),
            },
            "reason_code_accuracy": {
                "correct": clarification_reason_correct,
                "denominator": clarification_total,
                "accuracy": _ratio(clarification_reason_correct, clarification_total),
            },
        },
        "no_tool": {
            "total": no_tool_total,
            "recall": _ratio(no_tool_correct, no_tool_total),
            "reason_code_accuracy": {
                "correct": no_tool_reason_correct,
                "denominator": no_tool_total,
                "accuracy": _ratio(no_tool_reason_correct, no_tool_total),
            },
        },
        "error_categories": dict(sorted(error_categories.items())),
        "breakdown": {
            dimension: _breakdown(per_example, dimension)
            for dimension in ("family_id", "difficulty", "gold_outcome", "split")
        },
        "per_example": per_example,
    }
