"""Deterministic customer-support tools over fictional, packaged order fixtures.

Policy ``demo-refund-policy-v1`` uses a fixed date and INR balances. Delivered
orders are eligible for damaged/wrong items or a change of mind for 30 days
(inclusive). Nonreceipt is eligible only for shipped orders past the promised
date. Proposals never change balances or contact an external payment service.

Amounts enter as JSON numbers, are checked using Decimal cents, and leave as
fixed-point strings to avoid binary floating-point money in API responses.
"""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from datetime import date
from decimal import Decimal, InvalidOperation
from functools import lru_cache
from importlib.resources import files
from typing import Any

from tunebench.contracts import load_tool_registry, validate_prediction


@lru_cache(maxsize=1)
def _demo_fixture() -> dict[str, Any]:
    path = files("tunebench").joinpath("resources", "configs", "demo_orders.json")
    return json.loads(path.read_text(encoding="utf-8"))


def load_demo_orders() -> list[dict[str, Any]]:
    """Return independent fictional orders; changes cannot affect tool execution."""
    return deepcopy(_demo_fixture()["orders"])


def load_demo_policy() -> dict[str, Any]:
    """Return the public, versioned rules and fixed evaluation date."""
    return deepcopy(_demo_fixture()["policy"])


def _result(tool_name: Any) -> dict[str, Any]:
    policy = _demo_fixture()["policy"]
    return {
        "simulated": True,
        "tool_name": tool_name if isinstance(tool_name, str) else None,
        "policy_version": policy["version"],
        "as_of": policy["as_of"],
    }


def _blocked(tool_name: Any, code: str, message: str) -> dict[str, Any]:
    return {**_result(tool_name), "status": "blocked", "error": {"code": code, "message": message}}


def _eligibility(order: dict[str, Any], reason: str) -> dict[str, Any]:
    policy = _demo_fixture()["policy"]
    today = date.fromisoformat(policy["as_of"])
    if Decimal(order["remaining_refundable"]) <= 0:
        eligible, rule = False, "no_refundable_balance"
    elif reason == "not_received":
        if order["status"] == "delivered":
            eligible, rule = False, "delivered_order_requires_dispute"
        elif order["status"] != "shipped":
            eligible, rule = False, "order_not_shipped"
        elif today > date.fromisoformat(order["expected_delivery_date"]):
            eligible, rule = True, "shipped_delivery_overdue"
        else:
            eligible, rule = False, "delivery_not_overdue"
    elif order["status"] != "delivered" or order["delivered_date"] is None:
        eligible, rule = False, "order_not_delivered"
    else:
        days = (today - date.fromisoformat(order["delivered_date"])).days
        eligible = 0 <= days <= policy["refund_window_days"]
        rule = "within_refund_window" if eligible else "outside_refund_window"
    return {
        "order_id": order["order_id"],
        "reason": reason,
        "eligible": eligible,
        "rule_code": rule,
        "remaining_refundable": order["remaining_refundable"],
        "currency": order["currency"],
    }


def execute_tool(tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    """Validate and execute a fictional read or a nonmutating refund proposal.

    Invalid requests return a blocked result. Eligibility checks are successful
    reads even when the business policy says the order is not eligible.
    """
    tools = load_tool_registry()
    names = {tool["name"] for tool in tools}
    if not isinstance(tool_name, str) or tool_name not in names:
        return _blocked(tool_name, "unknown_tool", "The requested tool is not available.")
    if not isinstance(arguments, dict):
        return _blocked(tool_name, "invalid_arguments", "Tool arguments must be a JSON object.")
    try:
        # Reject non-JSON values and NaN/Infinity before validating the registry schema.
        json.dumps(arguments, allow_nan=False)
    except (ValueError, TypeError, OverflowError):
        return _blocked(
            tool_name, "invalid_arguments", "Tool arguments must be finite JSON values."
        )
    capture = {
        "example_id": "demo-execution",
        "outcome": {"type": "tool_call", "tool_name": tool_name, "arguments": arguments},
    }
    if validate_prediction(capture, tools):
        return _blocked(
            tool_name, "invalid_arguments", "Arguments must match the tool definition exactly."
        )
    order = next(
        (
            order
            for order in _demo_fixture()["orders"]
            if order["order_id"] == arguments["order_id"]
        ),
        None,
    )
    if order is None:
        return _blocked(
            tool_name, "unknown_order", "This order ID is not in the fictional demo data."
        )
    result = {**_result(tool_name), "status": "success"}
    if tool_name == "get_order_status":
        return {**result, "data": deepcopy(order)}
    eligibility = _eligibility(order, arguments["reason"])
    if tool_name == "check_refund_eligibility":
        return {**result, "data": eligibility}
    if not eligibility["eligible"]:
        return _blocked(
            tool_name,
            "refund_ineligible",
            f"Demo refund policy blocked this proposal: {eligibility['rule_code']}.",
        )
    try:
        amount = Decimal(str(arguments["refund_amount"]))
        if amount > Decimal(order["remaining_refundable"]):
            return _blocked(
                tool_name,
                "amount_exceeds_remaining",
                "The proposal amount exceeds the remaining refundable balance.",
            )
        if amount != amount.quantize(Decimal("0.01")):
            return _blocked(
                tool_name,
                "invalid_money_precision",
                "INR amounts may have at most two decimal places.",
            )
    except InvalidOperation:
        return _blocked(
            tool_name, "invalid_money_precision", "The amount cannot be represented in cents."
        )
    proposal = {
        "order_id": order["order_id"],
        "refund_amount": format(amount, ".2f"),
        "currency": order["currency"],
        "reason": arguments["reason"],
        "execution": "proposal_only",
    }
    identity = json.dumps(
        {**proposal, "policy_version": result["policy_version"], "as_of": result["as_of"]},
        sort_keys=True,
        separators=(",", ":"),
    )
    proposal["proposal_id"] = "SIM-" + hashlib.sha256(identity.encode()).hexdigest()[:12].upper()
    return {
        **result,
        "data": {
            **eligibility,
            "proposal": proposal,
            "note": "Simulation only. No balance was changed and no payment was executed.",
        },
    }
