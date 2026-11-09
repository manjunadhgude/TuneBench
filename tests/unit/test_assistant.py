import json
from copy import deepcopy

import pytest

from tunebench import assistant


def _call(name="get_order_status", **arguments):
    return {"type": "tool_call", "tool_name": name, "arguments": arguments}


def _injected(outcome):
    return lambda _messages: json.dumps(outcome)


def test_rules_execute_fictional_status_without_claiming_llm():
    result = assistant.respond("Where is order TB-1001?")
    assert result["status"] == "executed"
    assert result["backend"] == "rules"
    assert "no LLM" in result["backend_label"]
    assert result["tool_result"]["data"]["status"] == "shipped"
    assert result["tool_result"]["simulated"] is True
    assert len(result["attempts"]) == 1


@pytest.mark.parametrize(
    ("message", "target", "missing"),
    [
        ("Check the order status.", "get_order_status", ["order_id"]),
        ("Check refund eligibility for order TB-1002.", "check_refund_eligibility", ["reason"]),
        ("Propose a refund for damaged order TB-1002.", "propose_refund", ["refund_amount"]),
        (
            "Propose a refund; I gave no order ID, reason or amount.",
            "propose_refund",
            ["order_id", "reason", "refund_amount"],
        ),
    ],
)
def test_rules_clarify_all_missing_arguments(message, target, missing):
    result = assistant.respond(message)
    assert result["status"] == "clarification"
    assert result["outcome"]["target_tool_name"] == target
    assert result["outcome"]["missing_fields"] == missing
    assert result["tool_result"] is None


@pytest.mark.parametrize(
    "message",
    [
        "Execute a refund payment for order TB-1002.",
        "Send money back to my bank account for TB-1002, not a proposal.",
        "Cancel order TB-1001.",
    ],
)
def test_actual_payments_and_unsupported_actions_do_not_run_proposals(message):
    result = assistant.respond(message)
    assert result["status"] == "no_tool"
    assert result["outcome"]["reason_code"] == "unsupported_request"
    assert result["tool_result"] is None


def test_refund_proposal_runs_only_simulation_with_grounded_amount():
    result = assistant.respond(
        "Propose an INR 100 refund for damaged order TB-1002; do not execute a real refund."
    )
    assert result["status"] == "executed"
    proposal = result["tool_result"]["data"]["proposal"]
    assert proposal["refund_amount"] == "100.00"
    assert proposal["execution"] == "proposal_only"
    assert "No payment" in result["user_message"]


@pytest.mark.parametrize(
    ("message", "field"),
    [
        ("Check status for order TB-1001 or TB-1002.", "order_id"),
        ("Check refund eligibility for order TB-1002: damaged or wrong item.", "reason"),
        ("Propose an INR 100 or INR 200 refund for damaged order TB-1002.", "refund_amount"),
    ],
)
def test_conflicting_arguments_clarify_instead_of_picking(message, field):
    result = assistant.respond(message)
    assert result["status"] == "clarification"
    assert field in result["outcome"]["missing_fields"]
    assert result["outcome"]["reason_code"] == "ambiguous_reference"


def test_model_invalid_output_gets_one_visible_repair_without_losing_raw_evidence():
    calls = []
    raw_first = "not JSON; this is a bad response"
    raw_second = json.dumps(_call(order_id="TB-1001"))

    def generate(messages):
        calls.append(deepcopy(messages))
        return raw_first if len(calls) == 1 else raw_second

    result = assistant.respond("Where is order TB-1001?", backend="model", generate=generate)
    assert result["status"] == "executed"
    assert result["backend"] == "injected"
    assert result["repair_attempted"] is True
    assert result["raw_first_attempt_valid"] is False
    assert [a["raw_output"] for a in result["attempts"]] == [raw_first, raw_second]
    assert result["attempts"][0]["validation_errors"]
    assert result["attempts"][1]["validation_errors"] == []
    assert len(calls) == 2
    assert calls[1][-2] == {"role": "assistant", "content": raw_first}
    assert "failed validation" in calls[1][-1]["content"]


def test_invalid_output_never_retries_more_than_once():
    calls = []

    def generate(messages):
        calls.append(messages)
        return '{"nonsense":true}'

    result = assistant.respond("Where is order TB-1001?", generate=generate)
    assert len(calls) == 2
    assert result["status"] == "blocked"
    assert result["accepted_outcome"] is None
    assert result["tool_result"] is None


def test_repair_can_be_disabled_for_single_attempt_evidence():
    result = assistant.respond(
        "Where is order TB-1001?", generate=lambda _messages: "not JSON", max_repairs=0
    )
    assert len(result["attempts"]) == 1
    assert result["status"] == "blocked"


@pytest.mark.parametrize(
    ("message", "outcome", "error"),
    [
        ("Where is order TB-1001?", _call(order_id="TB-1002"), "single literal"),
        ("Where is order UNKNOWN-123?", _call(order_id="UNKNOWN-123"), "fictional demo"),
        (
            "Check refund eligibility for damaged order TB-1002.",
            _call("propose_refund", order_id="TB-1002", reason="damaged_item", refund_amount=100),
            "Requested action",
        ),
        (
            "Propose a refund for damaged order TB-1002; I have not chosen an amount.",
            _call("propose_refund", order_id="TB-1002", reason="damaged_item", refund_amount=29.99),
            "explicitly stated",
        ),
        (
            "Check refund eligibility for damaged order TB-1002.",
            _call("check_refund_eligibility", order_id="TB-1002", reason="wrong_item"),
            "unsupported by",
        ),
        (
            "Execute a refund payment for order TB-1002.",
            _call("propose_refund", order_id="TB-1002", reason="damaged_item", refund_amount=100),
            "Requested action",
        ),
    ],
)
def test_valid_json_does_not_bypass_grounding_or_action_guards(message, outcome, error):
    result = assistant.respond(message, generate=_injected(outcome))
    assert result["status"] == "blocked"
    assert result["accepted_outcome"] is None
    assert result["policy_override"] is True
    assert result["attempts"][0]["schema_valid"] is True
    assert any(error in e for e in result["validation_errors"])
    assert len(result["attempts"]) == 1  # Grounding blocks do not trigger a hidden repair.
    assert result["tool_result"] is None


def test_rule_backend_does_not_treat_support_reference_as_order_id():
    result = assistant.respond(
        "Check the order status; support reference TB-1001 is not an order ID."
    )
    assert result["status"] == "clarification"
    assert result["outcome"]["missing_fields"] == ["order_id"]


@pytest.mark.parametrize(
    "message",
    [
        "Do not check the order status for TB-1001.",
        "Don't retrieve the status of order TB-1001.",
        "Never propose an INR 100 refund for damaged order TB-1002.",
        "I do not want you to check refund eligibility for damaged order TB-1002.",
        "Without proposing an INR 100 refund for damaged order TB-1002.",
        "Hypothetically, propose an INR 100 refund for damaged order TB-1002.",
    ],
)
def test_explicitly_prohibited_or_hypothetical_actions_never_execute(message):
    result = assistant.respond(message)
    assert result["status"] == "no_tool"
    assert result["outcome"]["reason_code"] == "no_action_requested"
    assert result["tool_result"] is None


def test_negated_delivery_fact_keeps_explicit_eligibility_action():
    result = assistant.respond(
        "Check refund eligibility for order TB-1004; the item was not received."
    )
    assert result["status"] == "executed"
    assert result["outcome"]["arguments"]["reason"] == "not_received"
    assert result["tool_result"]["data"]["eligible"] is True


def test_schema_valid_model_call_cannot_override_explicit_prohibition():
    result = assistant.respond(
        "Do not check the order status for TB-1001.",
        generate=_injected(_call(order_id="TB-1001")),
    )
    assert result["status"] == "blocked"
    assert result["policy_override"] is True
    assert result["tool_result"] is None


def test_foreign_currency_is_not_silently_converted_to_inr():
    result = assistant.respond("Propose a USD 100 refund for damaged order TB-1002.")
    assert result["status"] == "blocked"
    assert "INR only" in " ".join(result["validation_errors"])


def test_mock_policy_remains_an_independent_execution_gate():
    result = assistant.respond("Propose an INR 1500 refund for damaged order TB-1002.")
    assert result["status"] == "blocked"
    assert result["tool_result"]["error"]["code"] == "amount_exceeds_remaining"
    assert result["accepted_outcome"] is None


def test_validation_only_never_executes_or_requires_a_store_order(monkeypatch):
    def forbidden(*_args, **_kwargs):
        raise AssertionError("No tool should execute during decision evaluation")

    monkeypatch.setattr(assistant, "execute_tool", forbidden)
    result = assistant.respond("Where is order FRESH-912?", execute_tools=False)
    assert result["status"] == "validated"
    assert result["accepted_outcome"]["arguments"] == {"order_id": "FRESH-912"}
    assert result["tool_result"] is None
    assert result["execute_tools"] is False


def test_backend_runtime_failure_is_not_mislabeled_as_model_response():
    def broken(_messages):
        raise RuntimeError("out of memory")

    result = assistant.respond("Where is order TB-1001?", generate=broken)
    assert result["status"] == "error"
    assert result["attempts"] == []
    assert "out of memory" in result["user_message"]


def test_model_requires_explicit_local_snapshot_without_downloading():
    result = assistant.respond("Where is order TB-1001?", backend="model")
    assert result["status"] == "error"
    assert "no download" in result["user_message"]


def test_model_messages_have_request_and_registry_but_no_gold_labels():
    captured = []

    def generate(messages):
        captured.append(messages)
        return json.dumps(_call(order_id="TB-1001"))

    assistant.respond("Where is order TB-1001?", generate=generate)
    serialized = json.dumps(captured)
    assert "expected_outcome" not in serialized
    assert "family_id" not in serialized
    assert "scenario_id" not in serialized
    assert captured[0][-1] == {"role": "user", "content": "Where is order TB-1001?"}


@pytest.mark.parametrize("value", ["", "   ", "x" * 4001, None])
def test_blank_invalid_or_oversized_input_returns_clear_error(value):
    result = assistant.respond(value)
    assert result["status"] == "error"
    assert result["attempts"] == []


@pytest.mark.parametrize("repairs", [-1, 2, True])
def test_repair_limit_is_explicitly_bounded(repairs):
    result = assistant.respond("Where is order TB-1001?", max_repairs=repairs)
    assert result["status"] == "error"
    assert result["attempts"] == []
