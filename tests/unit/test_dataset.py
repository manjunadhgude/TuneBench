"""Generation and quality gates should reject common benchmark leaks."""

from collections import Counter
from copy import deepcopy

import pytest

from tunebench.dataset import audit_dataset, generate_dataset, generate_smoke


@pytest.fixture(scope="module")
def candidate_splits():
    return generate_dataset(seed=19)


def test_smoke_is_deterministic_and_complete():
    records = generate_smoke()
    assert records == generate_smoke()
    assert records != generate_smoke(seed=7)
    assert len(records) == 20
    assert Counter(r["expected_outcome"]["type"] for r in records) == {
        "tool_call": 10,
        "clarification": 5,
        "no_tool": 5,
    }
    assert {r["split"] for r in records} == {"smoke"}
    assert all(r["provenance"]["source_type"] == "synthetic" for r in records)
    assert all("reviewed_by" not in r["provenance"] for r in records)


def test_full_candidate_counts_and_family_isolation(candidate_splits):
    splits = candidate_splits
    report = audit_dataset(splits)
    assert report["total_examples"] == 1250
    assert report["dataset_status"] == "candidate_unreviewed"
    assert {k: len(v) for k, v in splits.items()} == {"train": 1000, "validation": 125, "test": 125}
    assert report["splits"]["train"]["outcomes"] == {
        "tool_call": 500,
        "clarification": 250,
        "no_tool": 250,
    }
    assert report["splits"]["validation"]["outcomes"] == {
        "tool_call": 63,
        "clarification": 31,
        "no_tool": 31,
    }
    assert report["splits"]["test"]["outcomes"] == {
        "tool_call": 62,
        "clarification": 31,
        "no_tool": 32,
    }
    family_sets = [{r["family_id"] for r in rs} for rs in splits.values()]
    assert all(len(s) == 10 for s in family_sets)
    assert sum(map(len, family_sets)) == len(set.union(*family_sets)) == 30
    assert report["splits"]["test"]["distinct_scenarios"] == 125
    assert len({r["scenario_id"] for rs in splits.values() for r in rs}) == 1250


def test_audit_rejects_invalid_arguments():
    records = generate_smoke()
    records[0]["expected_outcome"]["arguments"]["order_id"] = 123
    with pytest.raises(ValueError, match="Invalid task"):
        audit_dataset({"smoke": records})


def test_audit_rejects_duplicate_id_and_duplicate_prompt():
    records = generate_smoke()
    with pytest.raises(ValueError, match="Duplicate example_id"):
        audit_dataset({"smoke": records + [deepcopy(records[0])]})
    duplicate = deepcopy(records[0])
    duplicate["example_id"] = "different-id"
    duplicate["prompt"] = "  " + duplicate["prompt"].upper() + "  "
    with pytest.raises(ValueError, match="Duplicate prompt"):
        audit_dataset({"smoke": records + [duplicate]})


@pytest.mark.parametrize(
    "field,expected",
    [
        ("family_id", "Family leakage"),
        ("scenario_id", "Scenario leakage"),
    ],
)
def test_audit_rejects_cross_split_leakage(field, expected):
    smoke = generate_smoke()
    other = deepcopy(smoke[0])
    other["split"] = "validation"
    other["example_id"] = "validation-unique-id"
    other["family_id"] = "validation-unique-family"
    other["scenario_id"] = "validation-unique-scenario"
    other["prompt"] += " This is a separate request."
    other[field] = smoke[0][field]
    with pytest.raises(ValueError, match=expected):
        audit_dataset({"smoke": smoke, "validation": [other]})


def test_audit_rejects_split_mismatch_and_family_outcome_conflict():
    smoke = generate_smoke()
    with pytest.raises(ValueError, match="split mismatch"):
        audit_dataset({"train": smoke})
    smoke[-1]["family_id"] = smoke[0]["family_id"]
    with pytest.raises(ValueError, match="Mixed outcomes"):
        audit_dataset({"smoke": smoke})


def test_derived_refund_matches_supplied_unit_price_and_quantity(candidate_splits):
    import re

    record = next(
        r for r in candidate_splits["test"] if r["family_id"] == "TE_REFUND_DERIVED_AMOUNT"
    )
    quantity = int(re.search(r"contains (\d+) damaged", record["prompt"])[1])
    unit = float(re.search(r"priced at (\d+\.\d+)", record["prompt"])[1])
    assert record["expected_outcome"]["arguments"]["refund_amount"] == pytest.approx(
        quantity * unit
    )
    assert record["difficulty"] == "hard"


@pytest.mark.parametrize("seed", [-1, True, 2.5, "42"])
def test_bad_seed_is_rejected(seed):
    with pytest.raises(ValueError, match="nonnegative integer"):
        generate_smoke(seed)


def test_difficulty_is_not_mislabeled_to_hit_a_quota():
    smoke = generate_smoke()
    assert all(
        r["difficulty"] == "medium"
        for r in smoke
        if r["expected_outcome"]["type"] == "clarification"
    )
    report = audit_dataset({"smoke": smoke})
    assert report["warnings"]


def test_empty_split_cannot_pass_as_valid_dataset():
    with pytest.raises(ValueError, match="no tasks"):
        audit_dataset({"test": []})
