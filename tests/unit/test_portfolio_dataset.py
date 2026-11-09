"""Integrity and contract gates for the reviewed portfolio dataset artifacts."""

import hashlib
import json
import re
from collections import Counter
from decimal import Decimal
from pathlib import Path

import pytest

from tunebench.contracts import load_tool_registry, validate_task

DATASET = Path(__file__).resolve().parents[2] / "datasets" / "portfolio-v1"
HOLDOUT_SHA256 = "41bc632a179f769c0b9080f6a54c0952e148cb359cba1885cf263a3dfab80510"
REFUND_REASONS = {"damaged_item", "wrong_item", "not_received", "changed_mind"}


def _load(name):
    return [json.loads(line) for line in (DATASET / f"{name}.jsonl").read_text().splitlines()]


@pytest.mark.parametrize("name", ["development", "holdout"])
def test_artifact_matches_frozen_manifest_and_canonical_contract(name):
    manifest = json.loads((DATASET / "manifest.json").read_text())
    entry = manifest["files"][name]
    raw = (DATASET / entry["path"]).read_bytes()
    rows = _load(name)
    assert hashlib.sha256(raw).hexdigest() == entry["sha256"]
    assert len(raw) == entry["bytes"]
    assert len(rows) == entry["examples"]
    assert {r["split"] for r in rows} == {entry["split"]}
    assert Counter(r["expected_outcome"]["type"] for r in rows) == entry["outcomes"]
    assert Counter(r["difficulty"] for r in rows) == entry["difficulty"]
    assert Counter(r["family_id"] for r in rows) == entry["families"]
    canonical = load_tool_registry()
    for row in rows:
        assert validate_task(row) == [], row["example_id"]
        assert row["tools"] == canonical
        assert row["provenance"]["source_type"] == "manual"
        assert "not human" in row["provenance"]["reviewed_by"]


def test_holdout_cannot_silently_change_with_its_manifest():
    assert hashlib.sha256((DATASET / "holdout.jsonl").read_bytes()).hexdigest() == HOLDOUT_SHA256


def test_coverage_counts_and_disjoint_family_scenarios():
    development, holdout = _load("development"), _load("holdout")
    assert len(development) == 40
    assert len(holdout) == 20
    assert Counter(r["expected_outcome"]["type"] for r in development) == {
        "tool_call": 14,
        "clarification": 13,
        "no_tool": 13,
    }
    assert Counter(r["expected_outcome"]["type"] for r in holdout) == {
        "tool_call": 8,
        "clarification": 6,
        "no_tool": 6,
    }
    for field in ("family_id", "scenario_id", "example_id"):
        assert not ({r[field] for r in development} & {r[field] for r in holdout})
    combined = development + holdout
    assert len({r["example_id"] for r in combined}) == 60
    assert len({r["scenario_id"] for r in combined}) == 60

    def normalize(text):
        return " ".join(text.casefold().split())

    assert len({normalize(r["prompt"]) for r in combined}) == 60
    # Surface identifier/amount-only substitutions; the set is more than ID swaps.
    shapes = [
        re.sub(r"\b[a-z]*[-:/]?\d+(?:\.\d+)?(?:-[a-z])?\b", "<value>", normalize(r["prompt"]))
        for r in combined
    ]
    assert len(set(shapes)) == 60


@pytest.mark.parametrize("name", ["development", "holdout"])
def test_each_partition_covers_reasons_tools_and_no_tool_boundaries(name):
    rows = _load(name)
    calls = [r["expected_outcome"] for r in rows if r["expected_outcome"]["type"] == "tool_call"]
    assert {o["tool_name"] for o in calls} == {
        "get_order_status",
        "check_refund_eligibility",
        "propose_refund",
    }
    assert {o["arguments"]["reason"] for o in calls if o["tool_name"] == "propose_refund"} == (
        REFUND_REASONS
    )
    assert {
        r["expected_outcome"]["reason_code"]
        for r in rows
        if r["expected_outcome"]["type"] == "no_tool"
    } == {"informational_request", "unsupported_request", "no_action_requested"}
    clarifications = [
        r["expected_outcome"] for r in rows if r["expected_outcome"]["type"] == "clarification"
    ]
    assert {o["target_tool_name"] for o in clarifications} == {
        None,
        "get_order_status",
        "check_refund_eligibility",
        "propose_refund",
    }


def test_reviewed_holdout_arithmetic_and_literal_reference_facts():
    by_family = {}
    for row in _load("holdout"):
        by_family.setdefault(row["family_id"], []).append(row)
    arithmetic = by_family["PV1_H_DERIVED_PROPOSAL"]
    assert Decimal(str(arithmetic[0]["expected_outcome"]["arguments"]["refund_amount"])) == (
        Decimal("4") * Decimal("6.35")
    )
    assert Decimal(str(arithmetic[1]["expected_outcome"]["arguments"]["refund_amount"])) == (
        Decimal("0.20") * Decimal("75.00")
    )
    literal = by_family["PV1_H_LITERAL_REFERENCE_CALL"][0]
    assert literal["expected_outcome"]["arguments"]["order_id"] == "ledger:409-B"
    assert '"ledger:409-B"' in literal["prompt"]


def test_gold_does_not_import_unstated_demo_amount_caps():
    row = next(
        r
        for r in _load("development")
        if r["expected_outcome"].get("arguments", {}).get("refund_amount") == 410.0
    )
    assert "410.00" in row["prompt"]
    assert validate_task(row) == []
