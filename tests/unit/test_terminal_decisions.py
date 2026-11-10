"""Non-executing decisions must not be escalated by fallible review feedback."""

import json
from pathlib import Path

import pytest

from tunebench import assistant

PATH = "/missing/Qwen3-4B-Instruct-2507-Q4_K_M.gguf"


@pytest.mark.parametrize(
    "outcome",
    [
        {"type": "no_tool", "reason_code": "no_action_requested"},
        {"type": "no_tool", "reason_code": "unsupported_request"},
        {"type": "no_tool", "reason_code": "informational_request"},
        {
            "type": "clarification",
            "target_tool_name": "propose_refund",
            "missing_fields": ["refund_amount"],
            "reason_code": "missing_required_information",
            "question": "What amount do you want proposed?",
        },
    ],
)
def test_valid_non_executing_decision_is_terminal(monkeypatch, outcome):
    calls = []

    def primary(_):
        calls.append("primary")
        if len(calls) > 1:
            pytest.fail("A non-executing decision must not trigger another generation")
        return json.dumps(outcome)

    def forbidden(*_):
        pytest.fail("A non-executing decision must not invoke review or execution")

    monkeypatch.setattr(assistant, "execute_tool", forbidden)
    result = assistant.respond(
        "This is a bounded injected test of terminal decisions.",
        model_path=PATH,
        generate=primary,
        verify=forbidden,
        execute_tools=True,
    )
    assert result["accepted_outcome"] == outcome
    assert result["status"] == outcome["type"]
    assert len(result["attempts"]) == 1
    assert result["semantic_verifications"] == []
    assert result["tool_result"] is None


def test_recorded_false_review_cannot_escalate_past_event(monkeypatch):
    root = Path(__file__).resolve().parents[2]
    cases = root / "artifacts/semantic-comparison-v7/candidate/cases.partial.jsonl"
    case = next(
        json.loads(line)
        for line in cases.read_text().splitlines()
        if json.loads(line)["example_id"] == "portfolio-v5-holdout-40"
    )
    recorded = case["response"]
    primary = iter(a["raw_output"] for a in recorded["attempts"])
    reviews = iter(recorded["semantic_verifications"])

    def forbidden(*_):
        pytest.fail("The historical no-action message must never reach a tool")

    monkeypatch.setattr(assistant, "execute_tool", forbidden)
    result = assistant.respond(
        recorded["input"],
        model_path=PATH,
        generate=lambda _: next(primary),
        verify=lambda *_: next(reviews),
        execute_tools=True,
    )
    assert result["status"] == "no_tool"
    assert result["accepted_outcome"] == {"type": "no_tool", "reason_code": "no_action_requested"}
    assert len(result["attempts"]) == 1
    assert result["attempts"][0]["raw_output"] == recorded["attempts"][0]["raw_output"]
    assert result["semantic_verifications"] == []


def test_invalid_non_executing_output_still_requires_schema_repair():
    outputs = iter(
        [
            '{"type":"no_tool","reason_code":"invented"}',
            '{"type":"no_tool","reason_code":"informational_request"}',
        ]
    )

    def forbidden(*_):
        pytest.fail("Schema repair must not review a valid no-tool decision")

    result = assistant.respond(
        "What is delivery tracking?",
        model_path=PATH,
        generate=lambda _: next(outputs),
        verify=forbidden,
        execute_tools=True,
    )
    assert result["status"] == "no_tool"
    assert len(result["attempts"]) == 2
    assert result["attempts"][0]["schema_errors"]
    assert result["attempts"][1]["schema_valid"] is True
    assert result["tool_result"] is None
