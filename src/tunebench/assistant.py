"""Interactive reliability pipeline over fictional tools, separate from research scores."""

from __future__ import annotations

import hashlib
import json
import re
import time
from collections.abc import Callable
from copy import deepcopy
from decimal import Decimal
from typing import Any

from tunebench.contracts import load_tool_registry, validate_prediction
from tunebench.inference import build_messages, parse_output
from tunebench.mock_tools import execute_tool, load_demo_orders

_REASONS = {
    "damaged_item": r"\bdamaged(?:_item)?\b|\bbroken\b|\bcracked\b|\bshattered\b",
    "wrong_item": r"\bwrong[_ ](?:item|product)\b|\bincorrect item\b|\bdifferent item\b",
    "not_received": (
        r"\bnot[_ ]received\b|\bnever (?:arrived|delivered)\b|\bnot arrived\b|"
        r"\b(?:has not|hasn't|did not|didn't) arrive(?:d)?\b"
    ),
    "changed_mind": r"\bchanged[_ ](?:my[_ ])?mind\b|\bno longer (?:need|want)\b",
}
_NUMBER = r"-?\d+(?:,\d{3})*(?:\.\d+)?"
_AMOUNT_PATTERNS = (
    rf"(?:₹|INR\s*|Rs\.?\s*|\$|USD\s*)({_NUMBER})",
    rf"({_NUMBER})\s*(?:INR|rupees?|dollars?|USD)\b",
    rf"\b(?:refund_amount|amount)\s*(?:of|is|:|=)?\s*({_NUMBER})",
    rf"\brefund(?:\s+(?:proposal|of|for|amount))*\s+({_NUMBER})(?![\w.-])",
)


def _analysis(message: str) -> dict[str, Any]:
    text = message.casefold()
    # Remove explicitly prohibited actions, not negated facts such as "not received".
    # Clause-level removal is deliberately conservative rather than guessing scope.
    negative_action = (
        r"\b(?:do not|don't|never)\s+(?:(?:want(?: you)? to|need(?: you)? to)\s+)?"
        r"(?:execute|process|issue|send|pay|check|retrieve|look up|fetch|track|get|"
        r"propose|draft|prepare)\b[^.;\n]*|"
        r"\bwithout\s+(?:executing|checking|retrieving|tracking|proposing|drafting|preparing)"
        r"\b[^.;\n]*"
    )
    prohibited_action = bool(re.search(negative_action, text))
    actionable = re.sub(negative_action, " ", text)
    unsupported = bool(
        re.search(
            r"\bcancel\b|\b(?:execute|process|issue)\b.{0,30}\b(?:refund|payment)\b|"
            r"\brefund me\b|\b(?:actual|real) refund\b|"
            r"\b(?:send|transfer|pay|credit)\b.{0,50}\b(?:money|bank|account|back|payment)\b|"
            r"\bchange\b.{0,30}\b(?:password|address)\b",
            actionable,
        )
    )
    informational = bool(
        re.search(r"\b(?:explain|define|generally|in general|typical)\b|\bwhat does\b", text)
    )
    hypothetical = bool(re.search(r"\bhypothetical(?:ly)?\b|\bwhat if\b", text))
    no_action = prohibited_action or bool(
        re.search(r"\b(?:thanks|thank you|that's all|no action)\b", text)
    )
    tools = set()
    if re.search(r"\beligib\w*\b|\bqualif\w*\b", actionable):
        tools.add("check_refund_eligibility")
    if "refund" in actionable and re.search(r"\b(?:propos\w*|draft|simulat\w*)\b", actionable):
        tools.add("propose_refund")
    if re.search(
        r"\b(?:check|retrieve|look up|fetch|track|get)\s+(?:the\s+|current\s+|my\s+)*"
        r"(?:order\s+)?(?:status|tracking)\b|"
        r"\bwhere(?: is|'s| are)\b.{0,40}\b(?:order|parcel|package)\b|"
        r"\b(?:status|track)\s+(?:of\s+|for\s+)?(?:order\b|TB-)|"
        r"\bwhat\s+is\s+the\s+(?:current\s+)?status\b",
        actionable,
        re.IGNORECASE,
    ):
        tools.add("get_order_status")
    if unsupported:
        intent = "unsupported"
    elif hypothetical:
        intent = "none"
    elif informational:
        intent = "informational"
    elif len(tools) == 1:
        intent = next(iter(tools))
    elif len(tools) > 1:
        intent = "ambiguous"
    elif no_action:
        intent = "none"
    elif re.search(r"\b(?:refund|order|help|action)\b", text):
        intent = "ambiguous"
    else:
        intent = "informational"

    references = set(re.findall(r"\bTB-\d+\b", message))
    references.update(
        re.findall(
            r"\border(?:\s+(?:id|reference|number))?\s*[:#=]?\s+"
            r"([A-Za-z][A-Za-z0-9_-]*\d[A-Za-z0-9_-]*)\b",
            message,
            re.IGNORECASE,
        )
    )
    for reference in list(references):
        escaped = re.escape(reference)
        if re.search(
            rf"\bsupport(?:\s+(?:reference|ticket))?(?:\s+(?:id|number))?\s*[:#]?\s+"
            rf"{escaped}\b|\b{escaped}\b\s+(?:is\s+)?(?:only\s+)?a support",
            message,
            re.IGNORECASE,
        ):
            references.discard(reference)
    reason_text = re.sub(
        r"\b(?:not|isn't|wasn't)\s+(?:damaged|broken|cracked|shattered|the wrong item)\b",
        " ",
        text,
    )
    reasons = {reason for reason, pattern in _REASONS.items() if re.search(pattern, reason_text)}
    amounts = {
        Decimal(match.replace(",", ""))
        for pattern in _AMOUNT_PATTERNS
        for match in re.findall(pattern, message, re.IGNORECASE)
    }
    return {
        "intent": intent,
        "order_ids": sorted(references),
        "reasons": sorted(reasons),
        "amounts": sorted(amounts),
        "foreign_currency": bool(re.search(r"\$|€|£|\b(?:USD|EUR|GBP|dollars?)\b", message)),
    }


def _clarification(target: str | None, missing: list[str], ambiguous: bool = False) -> dict:
    return {
        "type": "clarification",
        "target_tool_name": target,
        "missing_fields": missing,
        "reason_code": (
            "ambiguous_intent"
            if target is None
            else "ambiguous_reference"
            if ambiguous
            else "missing_required_information"
        ),
        "question": (
            "Which action do you want: order status, refund eligibility, or a refund proposal?"
            if target is None
            else "Please specify " + ", ".join(missing) + "."
        ),
    }


def _rule_outcome(analysis: dict[str, Any]) -> dict[str, Any]:
    intent = analysis["intent"]
    reasons = {
        "unsupported": "unsupported_request",
        "informational": "informational_request",
        "none": "no_action_requested",
    }
    if intent in reasons:
        return {"type": "no_tool", "reason_code": reasons[intent]}
    if intent == "ambiguous":
        return _clarification(None, [])
    missing = []
    if len(analysis["order_ids"]) != 1:
        missing.append("order_id")
    if intent != "get_order_status" and len(analysis["reasons"]) != 1:
        missing.append("reason")
    if intent == "propose_refund" and (
        len(analysis["amounts"]) != 1 or analysis["amounts"][0] <= 0
    ):
        missing.append("refund_amount")
    if missing:
        ambiguous = any(len(analysis[field]) > 1 for field in ("order_ids", "reasons", "amounts"))
        return _clarification(intent, missing, ambiguous)
    arguments: dict[str, Any] = {"order_id": analysis["order_ids"][0]}
    if intent != "get_order_status":
        arguments["reason"] = analysis["reasons"][0]
    if intent == "propose_refund":
        arguments["refund_amount"] = float(analysis["amounts"][0])
    return {"type": "tool_call", "tool_name": intent, "arguments": arguments}


def _grounding_errors(
    outcome: dict[str, Any], analysis: dict[str, Any], *, execute_tools: bool
) -> list[str]:
    if outcome["type"] != "tool_call":
        return []
    errors = []
    name, arguments = outcome["tool_name"], outcome["arguments"]
    if analysis["intent"] != name:
        errors.append("Requested action does not unambiguously support this tool; no substitution")
    if len(analysis["order_ids"]) != 1 or arguments["order_id"] not in analysis["order_ids"]:
        errors.append("order_id must be the single literal order reference in the request")
    if execute_tools and arguments["order_id"] not in {
        order["order_id"] for order in load_demo_orders()
    }:
        errors.append("order_id is not one of the fictional demo orders")
    if name != "get_order_status" and (
        len(analysis["reasons"]) != 1 or arguments["reason"] not in analysis["reasons"]
    ):
        errors.append("reason is missing, conflicting, or unsupported by the request text")
    if name == "propose_refund":
        if analysis["foreign_currency"]:
            errors.append("Demo refund proposals use INR only; no currency conversion is supported")
        amount = Decimal(str(arguments["refund_amount"]))
        if len(analysis["amounts"]) != 1 or amount not in analysis["amounts"]:
            errors.append("refund_amount must be one explicitly stated amount; no invented amounts")
        if amount <= 0:
            errors.append("refund_amount must be positive")
    return errors


def _executed_message(tool_name: str, result: dict[str, Any]) -> str:
    data = result["data"]
    if tool_name == "get_order_status":
        return f"Demo order {data['order_id']} is {data['status']}."
    if tool_name == "check_refund_eligibility":
        label = "eligible" if data["eligible"] else "not eligible"
        return f"Demo order {data['order_id']} is {label}: {data['rule_code']}."
    proposal = data["proposal"]
    return (
        f"Simulated proposal {proposal['proposal_id']} for {proposal['currency']} "
        f"{proposal['refund_amount']}. No payment was executed."
    )


def respond(
    message: str,
    backend: str = "rules",
    model_path: str | None = None,
    *,
    generate: Callable[[list[dict[str, str]]], str] | None = None,
    max_repairs: int = 1,
    execute_tools: bool = True,
) -> dict[str, Any]:
    """Validate a decision and ground every tool execution; retain all raw attempts.

    ``generate`` is an injected test backend and is always labelled as such.
    ``execute_tools=False`` validates without looking up fictional demo orders.
    Interactive repair is separate from the unchanged single-attempt research API.
    """
    start = time.perf_counter()
    used_backend = "injected" if generate is not None else backend
    result: dict[str, Any] = {
        "status": "error",
        "backend": used_backend,
        "requested_backend": backend,
        "backend_label": {
            "rules": "Deterministic rules (no LLM)",
            "model": "Actual local Qwen model",
            "injected": "Injected test backend",
        }.get(used_backend, "Unknown backend"),
        "prompt": "strong-v2" if used_backend != "rules" else "rules-v1",
        "input": message,
        "outcome": None,
        "accepted_outcome": None,
        "attempts": [],
        "validation_errors": [],
        "tool_result": None,
        "elapsed_ms": 0,
        "execution_mode": "simulated_tools" if execute_tools else "validation_only",
        "execute_tools": execute_tools,
        "execution_guard_policy": "conservative-text-grounding-v1",
        "policy_override": False,
        "user_message": "",
        "simulated": True,
    }

    def finish() -> dict[str, Any]:
        result["elapsed_ms"] = (time.perf_counter() - start) * 1000
        return result

    if not isinstance(message, str) or not message.strip() or len(message) > 4000:
        result["user_message"] = "Enter a request between 1 and 4000 characters."
        return finish()
    if backend not in {"rules", "model"}:
        result["user_message"] = "Choose the rules or local model backend."
        return finish()
    if isinstance(max_repairs, bool) or max_repairs not in {0, 1}:
        result["user_message"] = "The demo allows zero or one explicit repair attempt."
        return finish()
    tools = load_tool_registry()
    analysis = _analysis(message)
    messages = build_messages({"prompt": message, "tools": tools}, "strong-v2")
    result["prompt_sha256"] = (
        hashlib.sha256(
            json.dumps(messages, sort_keys=True, ensure_ascii=False).encode()
        ).hexdigest()
        if used_backend != "rules"
        else None
    )
    if generate is None and backend == "model":
        if not model_path:
            result["user_message"] = (
                "Select a verified local Qwen snapshot; no download is started."
            )
            return finish()
        from tunebench.live_model import generate_local

        def generate(messages):
            return generate_local(messages, model_path)

    attempts_allowed = 1 if used_backend == "rules" else 1 + max_repairs
    for index in range(attempts_allowed):
        attempt_start = time.perf_counter()
        try:
            raw = (
                json.dumps(_rule_outcome(analysis), ensure_ascii=False, allow_nan=False)
                if used_backend == "rules"
                else generate(deepcopy(messages))
            )
            if not isinstance(raw, str):
                raise TypeError("Generation backend did not return text")
        except (ValueError, OSError, ImportError, RuntimeError, TypeError) as exc:
            result["user_message"] = f"Backend could not complete the request: {exc}"
            return finish()
        prediction = parse_output("interactive-request", raw)
        errors = validate_prediction(prediction, tools)
        if prediction["outcome"] is None:
            errors.append(prediction["metadata"].get("parse_error", "No JSON outcome returned"))
        attempt = {
            "attempt": index + 1,
            "repair": index > 0,
            "raw_output": raw,
            "parsed_outcome": prediction["outcome"],
            "validation_errors": list(errors),
            "schema_valid": not errors,
            "latency_ms": (time.perf_counter() - attempt_start) * 1000,
        }
        result["attempts"].append(attempt)
        result["outcome"] = prediction["outcome"]
        result["validation_errors"] = list(errors)
        if not errors:
            break
        if index + 1 < attempts_allowed:
            messages += [
                {"role": "assistant", "content": raw},
                {
                    "role": "user",
                    "content": (
                        "Your output failed validation: "
                        + "; ".join(errors)[:2000]
                        + ". Return one corrected JSON outcome only. Do not invent missing values."
                    ),
                },
            ]
    result["repair_attempted"] = len(result["attempts"]) > 1
    result["raw_first_attempt_valid"] = result["attempts"][0]["schema_valid"]
    if used_backend == "model":
        from tunebench.live_model import model_status

        result["model_metadata"] = model_status()
    if result["validation_errors"]:
        result["status"] = "blocked"
        result["user_message"] = "No tool ran: the returned decision failed validation."
        return finish()
    outcome = result["outcome"]
    errors = _grounding_errors(outcome, analysis, execute_tools=execute_tools)
    if errors:
        result["status"] = "blocked"
        result["policy_override"] = True
        result["validation_errors"] = errors
        result["user_message"] = "No tool ran: " + "; ".join(errors)
        return finish()
    result["accepted_outcome"] = deepcopy(outcome)
    if outcome["type"] == "clarification":
        result["status"] = "clarification"
        result["user_message"] = outcome["question"] or "Please clarify the required information."
    elif outcome["type"] == "no_tool":
        result["status"] = "no_tool"
        result["user_message"] = {
            "unsupported_request": "This action is unavailable. No payment or account action ran.",
            "informational_request": "This is an informational request; no order tool was run.",
            "no_action_requested": "No action was requested, so no tool was run.",
        }[outcome["reason_code"]]
    elif not execute_tools:
        result["status"] = "validated"
        result["user_message"] = (
            "Decision passed validation and grounding; tool execution is disabled."
        )
    else:
        tool_result = execute_tool(outcome["tool_name"], outcome["arguments"])
        result["tool_result"] = tool_result
        if tool_result["status"] == "blocked":
            result["status"] = "blocked"
            result["accepted_outcome"] = None
            result["validation_errors"] = [tool_result["error"]["message"]]
            result["user_message"] = (
                "Demo policy blocked the tool: " + tool_result["error"]["message"]
            )
        else:
            result["status"] = "executed"
            result["user_message"] = _executed_message(outcome["tool_name"], tool_result)
    return finish()
