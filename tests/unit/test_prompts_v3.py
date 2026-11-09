"""Validate public few-shot examples, not claims about model accuracy."""

import json
import re
from decimal import Decimal

from tunebench.contracts import load_tool_registry, validate_prediction
from tunebench.prompts_v3 import PROMPT_VERSION, instruction_v3


def _examples():
    pairs = re.findall(r"Request: ([^\n]+)\nDecision: ([^\n]+)", instruction_v3())
    assert pairs, "The instruction must expose reviewable JSON few-shot examples"
    return [(request, json.loads(decision)) for request, decision in pairs]


def test_every_example_satisfies_canonical_tool_and_output_contracts():
    tools = load_tool_registry()
    for index, (request, decision) in enumerate(_examples()):
        assert request.strip()
        assert validate_prediction({"example_id": str(index), "outcome": decision}, tools) == []
        if decision["type"] == "tool_call":
            assert decision["tool_name"] in {tool["name"] for tool in tools}
        if decision["type"] == "clarification":
            assert decision["question"].strip()


def test_examples_cover_call_known_missing_unknown_action_and_all_no_tool_reasons():
    decisions = [decision for _, decision in _examples()]
    assert {decision["type"] for decision in decisions} == {
        "tool_call",
        "clarification",
        "no_tool",
    }
    assert {d["reason_code"] for d in decisions if d["type"] == "no_tool"} == {
        "informational_request",
        "unsupported_request",
        "no_action_requested",
    }
    clarifications = [d for d in decisions if d["type"] == "clarification"]
    known = next(d for d in clarifications if d["target_tool_name"] is not None)
    assert known["target_tool_name"] == "get_order_status"
    assert known["missing_fields"] == ["order_id"]
    ambiguous = next(d for d in clarifications if d["target_tool_name"] is None)
    assert ambiguous["missing_fields"] == []
    assert ambiguous["reason_code"] == "ambiguous_intent"


def test_refund_example_is_a_call_with_explicitly_derivable_amount():
    request, decision = next(
        (request, decision)
        for request, decision in _examples()
        if decision.get("tool_name") == "propose_refund"
    )
    assert "3 damaged units at 8.20 each" in request
    assert "excluding fees and tax" in request
    assert decision["type"] == "tool_call"
    assert decision["arguments"]["order_id"] == "sample:K/83"
    assert decision["arguments"]["reason"] == "damaged_item"
    assert Decimal(str(decision["arguments"]["refund_amount"])) == 3 * Decimal("8.20")


def test_correction_example_preserves_selected_literal_id():
    request, decision = next(
        (request, decision)
        for request, decision in _examples()
        if decision.get("tool_name") == "get_order_status"
    )
    assert "note:OLD/6" in request and "Correction: use note:NEW/9 instead" in request
    assert decision["arguments"] == {"order_id": "note:NEW/9"}


def test_actual_payment_example_never_substitutes_a_proposal():
    request, decision = next(
        (request, decision)
        for request, decision in _examples()
        if "actual refund payment" in request
    )
    assert "not a proposal" in request
    assert decision == {"type": "no_tool", "reason_code": "unsupported_request"}


def test_refund_example_clarifies_instead_of_inventing_a_default_amount():
    decision = next(
        decision
        for _, decision in _examples()
        if decision.get("target_tool_name") == "propose_refund"
    )
    assert decision["missing_fields"] == ["refund_amount"]
    assert decision["reason_code"] == "missing_required_information"


def test_prompt_defines_all_reason_codes_and_numeric_inference_boundaries():
    instruction = instruction_v3()
    definitions = {
        "missing_required_information": "required value absent",
        "ambiguous_reference": "competing values remain unresolved",
        "ambiguous_intent": "action unclear",
        "informational_request": "asks facts/advice/explanation",
        "unsupported_request": "requests an unavailable action",
        "no_action_requested": "statement, thanks, withdrawal",
    }
    for code, meaning in definitions.items():
        assert f"{code} = {meaning}" in instruction
    assert "quantity*price or percentage" in instruction
    assert "never assume missing inputs" in instruction
    assert '"target_tool_name":null' in instruction
    assert '"target_tool_name":"null"' not in instruction


def test_instruction_is_fixed_compact_and_independent_of_benchmark_metadata():
    instruction = instruction_v3()
    assert PROMPT_VERSION == "strong-v3"
    assert instruction == instruction_v3()
    assert len(instruction) <= 4100
    for label in ("expected_outcome", "example_id", "family_id", "scenario_id", "provenance"):
        assert label not in instruction
