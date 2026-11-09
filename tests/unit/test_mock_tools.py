"""Business-rule and boundary tests for the explicitly simulated tool handlers."""

import hashlib
import json
from copy import deepcopy
from datetime import date
from decimal import Decimal
from importlib.resources import files

import pytest

import tunebench.mock_tools as mock_tools
from tunebench.contracts import load_tool_registry
from tunebench.mock_tools import execute_tool, load_demo_orders, load_demo_policy


def eligibility(order_id, reason):
    return execute_tool("check_refund_eligibility", {"order_id": order_id, "reason": reason})


def proposal(amount=499, order_id="TB-1002", reason="damaged_item"):
    return execute_tool(
        "propose_refund", {"order_id": order_id, "reason": reason, "refund_amount": amount}
    )


def test_order_status_returns_packaged_order_with_simulation_metadata():
    result = execute_tool("get_order_status", {"order_id": "TB-1001"})
    assert result["status"] == "success"
    assert result["simulated"] is True
    assert result["tool_name"] == "get_order_status"
    assert result["policy_version"] == "demo-refund-policy-v1"
    assert result["as_of"] == "2026-11-09"
    assert result["data"]["status"] == "shipped"
    assert result["data"]["currency"] == "INR"
    assert result["data"]["order_total"] == "2499.00"


@pytest.mark.parametrize("reason", ["damaged_item", "wrong_item", "changed_mind"])
def test_recent_delivered_order_eligible_for_supported_delivery_reasons(reason):
    result = eligibility("TB-1002", reason)
    assert result["status"] == "success"
    assert result["data"]["eligible"] is True
    assert result["data"]["rule_code"] == "within_refund_window"
    assert result["data"]["remaining_refundable"] == "999.00"


@pytest.mark.parametrize(
    ("order_id", "reason", "expected_rule"),
    [
        ("TB-1001", "damaged_item", "order_not_delivered"),
        ("TB-1001", "not_received", "delivery_not_overdue"),
        ("TB-1002", "not_received", "delivered_order_requires_dispute"),
        ("TB-1003", "damaged_item", "outside_refund_window"),
        ("TB-1005", "damaged_item", "no_refundable_balance"),
    ],
)
def test_ineligible_results_are_successful_reads_with_explicit_rules(
    order_id, reason, expected_rule
):
    result = eligibility(order_id, reason)
    assert result["status"] == "success"
    assert result["data"]["eligible"] is False
    assert result["data"]["rule_code"] == expected_rule
    assert proposal(1, order_id, reason)["error"]["code"] == "refund_ineligible"


def test_overdue_shipped_order_eligible_for_nonreceipt_only():
    result = eligibility("TB-1004", "not_received")
    assert result["data"]["eligible"] is True
    assert result["data"]["rule_code"] == "shipped_delivery_overdue"
    assert eligibility("TB-1004", "changed_mind")["data"]["eligible"] is False
    assert proposal(99, "TB-1004", "not_received")["status"] == "success"


def test_refund_window_is_inclusive_and_fixed_date(monkeypatch):
    fixture = deepcopy(mock_tools._demo_fixture())
    order = next(order for order in fixture["orders"] if order["order_id"] == "TB-1002")
    monkeypatch.setattr(mock_tools, "_demo_fixture", lambda: fixture)
    order["delivered_date"] = "2026-10-10"
    assert eligibility("TB-1002", "damaged_item")["data"]["eligible"] is True
    order["delivered_date"] = "2026-10-09"
    assert eligibility("TB-1002", "damaged_item")["data"]["eligible"] is False
    order["delivered_date"] = "2026-11-10"
    assert eligibility("TB-1002", "damaged_item")["data"]["eligible"] is False


def test_nonreceipt_requires_strictly_overdue_date(monkeypatch):
    fixture = deepcopy(mock_tools._demo_fixture())
    order = next(order for order in fixture["orders"] if order["order_id"] == "TB-1004")
    monkeypatch.setattr(mock_tools, "_demo_fixture", lambda: fixture)
    order["expected_delivery_date"] = "2026-11-09"
    assert eligibility("TB-1004", "not_received")["data"]["eligible"] is False
    order["expected_delivery_date"] = "2026-11-08"
    assert eligibility("TB-1004", "not_received")["data"]["eligible"] is True


def test_proposal_is_a_deterministic_nonmutating_simulation():
    before = load_demo_orders()
    result = proposal(499.9)
    assert result["status"] == "success"
    simulated_proposal = result["data"]["proposal"]
    assert simulated_proposal["refund_amount"] == "499.90"
    assert simulated_proposal["currency"] == "INR"
    assert simulated_proposal["execution"] == "proposal_only"
    assert simulated_proposal["proposal_id"].startswith("SIM-")
    assert simulated_proposal == proposal(499.9)["data"]["proposal"]
    assert simulated_proposal["proposal_id"] != proposal(500)["data"]["proposal"]["proposal_id"]
    assert result["data"]["remaining_refundable"] == "999.00"
    assert load_demo_orders() == before


def test_amount_is_capped_by_remaining_balance_not_original_total():
    assert proposal(999)["status"] == "success"
    for amount in (999.01, 1000, 1299, 1300):
        result = proposal(amount)
        assert result["status"] == "blocked"
        assert result["error"]["code"] == "amount_exceeds_remaining"


@pytest.mark.parametrize("amount", [0.001, 12.345, 0.30000000000000004])
def test_fractional_cents_are_rejected_without_rounding(amount):
    assert proposal(amount)["error"]["code"] == "invalid_money_precision"


@pytest.mark.parametrize("amount", [0, -1, True, "499", float("nan"), float("inf"), -float("inf")])
def test_invalid_amounts_are_blocked(amount):
    result = proposal(amount)
    assert result["status"] == "blocked"
    assert result["error"]["code"] == "invalid_arguments"


@pytest.mark.parametrize(
    ("name", "arguments", "expected_code"),
    [
        ("execute_refund", {"order_id": "TB-1002"}, "unknown_tool"),
        (None, {}, "unknown_tool"),
        ("get_order_status", None, "invalid_arguments"),
        ("get_order_status", {"order_id": "UNKNOWN"}, "unknown_order"),
        ("get_order_status", {}, "invalid_arguments"),
        ("get_order_status", {"order_id": "TB-1001", "extra": True}, "invalid_arguments"),
        (
            "check_refund_eligibility",
            {"order_id": "TB-1002", "reason": "other"},
            "invalid_arguments",
        ),
    ],
)
def test_unknown_tools_orders_and_invalid_arguments_are_gracefully_blocked(
    name, arguments, expected_code
):
    result = execute_tool(name, arguments)
    assert result["status"] == "blocked"
    assert result["simulated"] is True
    assert result["error"]["code"] == expected_code
    json.dumps(result, allow_nan=False)


def test_public_fixture_and_result_mutations_cannot_change_the_demo():
    orders = load_demo_orders()
    policy = load_demo_policy()
    orders[0]["order_total"] = "1.00"
    policy["as_of"] = "2099-01-01"
    result = execute_tool("get_order_status", {"order_id": "TB-1001"})
    result["data"]["order_total"] = "2.00"
    result = execute_tool("get_order_status", {"order_id": "TB-1001"})
    assert result["data"]["order_total"] == "2499.00"
    assert result["as_of"] == "2026-11-09"


def test_all_tools_return_json_without_modifying_resource_file():
    path = files("tunebench").joinpath("resources", "configs", "demo_orders.json")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    results = [
        execute_tool("get_order_status", {"order_id": "TB-1001"}),
        eligibility("TB-1002", "damaged_item"),
        proposal(1),
    ]
    assert {result["tool_name"] for result in results} == {
        tool["name"] for tool in load_tool_registry()
    }
    for result in results:
        assert result["status"] == "success"
        assert result["simulated"] is True
        json.dumps(result, allow_nan=False)
    assert hashlib.sha256(path.read_bytes()).hexdigest() == digest


def test_fixture_money_and_policy_are_public_and_consistent():
    policy = load_demo_policy()
    assert policy["refund_window_days"] == 30
    assert len(policy["rules"]) >= 6
    assert policy["simulated"] is True
    date.fromisoformat(policy["as_of"])
    orders = load_demo_orders()
    assert len({order["order_id"] for order in orders}) == len(orders)
    for order in orders:
        assert order["currency"] == policy["currency"] == "INR"
        assert Decimal(order["order_total"]) == (
            Decimal(order["refunded_amount"]) + Decimal(order["remaining_refundable"])
        )
