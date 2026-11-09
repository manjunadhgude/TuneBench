"""Public prompt demonstrations must satisfy the real decision contract."""

import json
import re

from tunebench.contracts import load_tool_registry, validate_prediction
from tunebench.inference import build_messages
from tunebench.prompts_v4 import instruction_v4


def test_public_decision_examples_are_valid_and_cover_clarification_distinctions():
    examples = re.findall(r"Request: ([^\n]+)\nDecision: ([^\n]+)", instruction_v4())
    assert examples
    clarifications = []
    for index, (request, raw) in enumerate(examples):
        assert request.strip()
        outcome = json.loads(raw)
        assert not validate_prediction(
            {"example_id": str(index), "outcome": outcome}, load_tool_registry()
        )
        if outcome["type"] == "clarification":
            clarifications.append(outcome)
    assert {outcome["reason_code"] for outcome in clarifications} == {
        "ambiguous_intent",
        "ambiguous_reference",
        "missing_required_information",
    }
    ambiguous = next(x for x in clarifications if x["reason_code"] == "ambiguous_intent")
    assert ambiguous["target_tool_name"] is None
    assert ambiguous["missing_fields"] == []


def test_v4_prompt_exposes_no_evaluation_labels_or_case_metadata():
    tools = load_tool_registry()
    messages = build_messages(
        {
            "prompt": "A standalone request",
            "tools": tools,
            "example_id": "DO_NOT_EXPOSE_THIS_ID",
            "expected_outcome": {"private_label": True},
        },
        "strong-v4",
    )
    text = json.dumps(messages)
    assert "DO_NOT_EXPOSE_THIS_ID" not in text
    assert "private_label" not in text
    assert messages[-1] == {"role": "user", "content": "A standalone request"}
