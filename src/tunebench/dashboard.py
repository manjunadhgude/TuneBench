"""Read-only presentation helpers for the local portfolio workbench."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
MODEL_REVISION = "989aa7980e4cf806f80c7fef2b1adb7bc71aa306"
MODES = ("Quick demo", "Live local Qwen", "Saved model replay")
PRESETS = {
    "Track an order": "Check the status of order TB-1001.",
    "Check refund eligibility": (
        "Check refund eligibility for order TB-1002 because the item arrived damaged."
    ),
    "Ask for a missing amount": (
        "Propose a simulated refund for order TB-1002 because the item arrived damaged. "
        "I have not specified a refund amount."
    ),
    "Prepare a refund proposal": (
        "Propose a simulated refund of 250 INR for order TB-1002 because the item arrived damaged."
    ),
    "Answer an information request": "What does a refund eligibility check mean?",
    "Decline a real payment": "Execute a real refund payment of 250 INR for order TB-1002.",
}


def default_model_path() -> str:
    """Suggest a local path only; never initiate a model download."""
    configured = os.environ.get("TUNEBENCH_MODEL_PATH")
    if configured:
        return configured
    candidate = Path("/workspace/models/Qwen2.5-1.5B-Instruct") / MODEL_REVISION
    return str(candidate) if candidate.is_dir() else ""


def read_artifact(relative_path: str, root: Path = PROJECT_ROOT) -> dict[str, Any] | None:
    path = root / relative_path
    if not path.is_file():
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return value if isinstance(value, dict) else None


def historical_reports(root: Path = PROJECT_ROOT) -> dict[str, dict[str, Any] | None]:
    return {
        "smoke": read_artifact("artifacts/baseline-smoke/strong/report.json", root),
        "strong": read_artifact(
            "artifacts/prompt-development-v2/paired-run/strong/report.json", root
        ),
        "strong-v2": read_artifact(
            "artifacts/prompt-development-v2/paired-run/strong-v2/report.json", root
        ),
        "comparison": read_artifact(
            "artifacts/prompt-development-v2/paired-run/comparison.json", root
        ),
    }


def report_summary(report: dict[str, Any]) -> dict[str, Any]:
    total = report["total_examples"]
    return {
        "examples": total,
        "strict_correct": report["task_success"]["correct"],
        "outcome_correct": report["outcome_accuracy"]["correct"],
        # The evaluator's invalid count already includes missing predictions.
        "valid_predictions": total - report["invalid_predictions"],
    }


def replay_records(root: Path = PROJECT_ROOT) -> list[dict[str, Any]]:
    """Join historical smoke inputs to their original, unmodified model captures."""
    directory = root / "artifacts/baseline-smoke/strong"
    try:
        tasks = [json.loads(line) for line in (directory / "smoke.jsonl").read_text().splitlines()]
        predictions = [
            json.loads(line)
            for line in (directory / "strong.predictions.jsonl").read_text().splitlines()
        ]
    except (OSError, ValueError):
        return []
    by_id = {prediction["example_id"]: prediction for prediction in predictions}
    return [
        {"task": task, "prediction": by_id[task["example_id"]]}
        for task in tasks
        if task["example_id"] in by_id
    ]


def replay_result(record: dict[str, Any]) -> dict[str, Any]:
    from tunebench.contracts import validate_prediction

    task, prediction = record["task"], record["prediction"]
    errors = validate_prediction(prediction, task["tools"])
    return {
        "status": "recorded",
        "backend": "recorded model replay",
        "input": task["prompt"],
        "outcome": prediction.get("outcome"),
        "attempts": [
            {
                "raw_output": prediction.get("raw_output", ""),
                "parsed_outcome": prediction.get("outcome"),
                "validation_errors": errors,
            }
        ],
        "validation_errors": errors,
        "tool_result": None,
        "elapsed_ms": prediction.get("latency_ms", 0),
        "user_message": "Recorded response from the original CPU model run. No tool was executed.",
    }
