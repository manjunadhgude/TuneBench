from copy import deepcopy

import pytest

from tunebench.comparison import compare_reports


def report(success):
    return {
        "task_schema_version": "3.0.0",
        "evaluation_version": "0.2.0",
        "gold_sha256": "same-gold",
        "per_example": [
            {"example_id": str(i), "family_id": f"family-{i // 2}", "task_success": s}
            for i, s in enumerate(success)
        ],
    }


def test_paired_improvements_and_reproducible_cluster_interval():
    left, right = report([False] * 6), report([True] * 6)
    result = compare_reports(left, right)
    assert result == compare_reports(left, right)
    assert result["accuracy_delta"] == 1
    assert result["cluster_bootstrap_95_percent_interval"] == [1, 1]
    assert len(result["improvements"]) == 6
    assert result["regressions"] == []


def test_paired_regressions_and_zero_change():
    assert compare_reports(report([True] * 4), report([False] * 4))["accuracy_delta"] == -1
    assert compare_reports(report([True, False]), report([True, False]))["accuracy_delta"] == 0


@pytest.mark.parametrize("field", ["gold_sha256", "task_schema_version", "evaluation_version"])
def test_mismatched_experiments_refuse_comparison(field):
    left = report([True, False])
    right = deepcopy(left)
    right[field] = "different"
    with pytest.raises(ValueError, match=field):
        compare_reports(left, right)


def test_nonpaired_ids_refuse_comparison():
    left, right = report([True, False]), report([True, False, True])
    with pytest.raises(ValueError, match="same example"):
        compare_reports(left, right)


@pytest.mark.parametrize(
    "malformed", [[], {"per_example": [1]}, {"per_example": [{"example_id": []}]}]
)
def test_malformed_reports_fail_clearly(malformed):
    with pytest.raises(ValueError):
        compare_reports(malformed, report([True]))


def test_inference_settings_require_explicit_unmatched_override():
    left, right = report([True, False]), report([True, True])
    metadata = {
        "model_id": "base",
        "resolved_model_revision": "abc",
        "prompt_style": "strong",
        "decoding": {"max_new_tokens": 256},
        "retry_policy": "none",
    }
    left["inference_metadata"] = metadata
    right["inference_metadata"] = {**metadata, "decoding": {"max_new_tokens": 1000}}
    with pytest.raises(ValueError, match="Unmatched inference settings"):
        compare_reports(left, right)
    assert compare_reports(left, right, allow_unmatched=True)["inference_setting_mismatches"] == [
        "decoding"
    ]
