"""Paired comparisons with family-cluster bootstrap confidence intervals."""

import random
from statistics import mean
from typing import Any


def compare_reports(
    baseline: dict[str, Any],
    candidate: dict[str, Any],
    *,
    seed: int = 42,
    resamples: int = 2000,
    allow_unmatched: bool = False,
) -> dict[str, Any]:
    if resamples < 100:
        raise ValueError("Use at least 100 bootstrap resamples")

    def index(report):
        if not isinstance(report, dict) or not isinstance(report.get("per_example"), list):
            raise ValueError("Reports must be objects with a per_example array")
        records = report["per_example"]
        for row in records:
            if not isinstance(row, dict):
                raise ValueError("Each per_example row must be an object")
            if not isinstance(row.get("example_id"), str) or not row["example_id"].strip():
                raise ValueError("Each per_example row needs a nonempty example_id")
            if not isinstance(row.get("family_id"), str) or not row["family_id"].strip():
                raise ValueError("Each per_example row needs a nonempty family_id")
            if not isinstance(row.get("task_success"), bool):
                raise ValueError("task_success must be boolean")
        result = {row["example_id"]: row for row in records}
        if not result or len(result) != len(records):
            raise ValueError("Reports must have nonempty, unique example IDs")
        return result

    left, right = index(baseline), index(candidate)
    if left.keys() != right.keys():
        raise ValueError("Paired comparisons require exactly the same example IDs")
    for version in ("task_schema_version", "evaluation_version", "gold_sha256"):
        if version not in baseline or version not in candidate:
            raise ValueError(f"Reports must include {version} to establish comparability")
        if baseline[version] != candidate[version]:
            raise ValueError(f"Reports differ in {version}")
    warnings = []
    mismatches = []
    a_run, b_run = baseline.get("inference_metadata"), candidate.get("inference_metadata")
    if not isinstance(a_run, dict) or not isinstance(b_run, dict):
        warnings.append("Inference metadata missing; matched inference conditions are unverified.")
    else:
        for key in (
            "model_id",
            "resolved_model_revision",
            "prompt_style",
            "decoding",
            "retry_policy",
        ):
            if a_run.get(key) is None or b_run.get(key) is None:
                warnings.append(f"Inference metadata missing {key}; matching is unverified.")
            elif a_run[key] != b_run[key]:
                mismatches.append(key)
        if mismatches and not allow_unmatched:
            raise ValueError(
                f"Unmatched inference settings: {mismatches}; use allow_unmatched explicitly "
                "for an intentional ablation"
            )
    families: dict[str, list[int]] = {}
    regressions, improvements = [], []
    for key in sorted(left):
        a, b = left[key], right[key]
        if a["family_id"] != b["family_id"]:
            raise ValueError(f"Family mismatch for {key}")
        if not isinstance(a["task_success"], bool) or not isinstance(b["task_success"], bool):
            raise ValueError("task_success must be boolean")
        delta = int(b["task_success"]) - int(a["task_success"])
        families.setdefault(a["family_id"], []).append(delta)
        if delta < 0:
            regressions.append(key)
        elif delta > 0:
            improvements.append(key)
    rng = random.Random(seed)
    names = sorted(families)
    bootstrap = sorted(
        mean(value for name in rng.choices(names, k=len(names)) for value in families[name])
        for _ in range(resamples)
    )
    return {
        "examples": len(left),
        "families": len(names),
        "baseline_accuracy": mean(int(r["task_success"]) for r in left.values()),
        "candidate_accuracy": mean(int(r["task_success"]) for r in right.values()),
        "accuracy_delta": mean(value for values in families.values() for value in values),
        "cluster_bootstrap_95_percent_interval": [
            bootstrap[int(0.025 * (resamples - 1))],
            bootstrap[int(0.975 * (resamples - 1))],
        ],
        "seed": seed,
        "resamples": resamples,
        "regressions": regressions,
        "improvements": improvements,
        "inference_setting_mismatches": mismatches,
        "warnings": warnings,
        "limitations": "Descriptive uncertainty; few or synthetic families limit generalization.",
    }
