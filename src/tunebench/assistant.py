"""Interactive reliability pipeline over fictional tools, separate from research scores."""

from __future__ import annotations

import hashlib
import json
import time
from collections.abc import Callable
from copy import deepcopy
from pathlib import Path
from typing import Any

from tunebench.contracts import load_tool_registry, validate_prediction
from tunebench.grounding import (
    analyze as _analysis,
)
from tunebench.grounding import (
    ground_outcome as _grounding_errors,
)
from tunebench.grounding import (
    rule_outcome as _rule_outcome,
)
from tunebench.inference import build_messages, parse_output
from tunebench.mock_tools import execute_tool


def _uses_gguf(model_path: str | None) -> bool:
    if not model_path:
        return False
    from tunebench.gguf_model import MODEL_FILENAME

    path = Path(model_path).expanduser()
    return path.suffix.lower() == ".gguf" or (path.is_dir() and (path / MODEL_FILENAME).is_file())


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
    Interactive schema/evidence repair is separate from the single-attempt research API.
    Grounding diagnostics for non-executing decisions are advisory: heuristic
    disagreements cannot turn a safe refusal or clarification into an action.
    """
    start = time.perf_counter()
    used_backend = "injected" if generate is not None else backend
    gguf = used_backend != "rules" and _uses_gguf(model_path)
    prompt_style = "strong-v4" if gguf else "strong-v3"
    result: dict[str, Any] = {
        "status": "error",
        "backend": used_backend,
        "requested_backend": backend,
        "backend_label": {
            "rules": "Deterministic rules (no LLM)",
            "model": "Actual local Qwen model",
            "injected": "Injected test backend",
        }.get(used_backend, "Unknown backend"),
        "prompt": prompt_style if used_backend != "rules" else "rules-v3",
        "model_profile": (
            None if used_backend == "rules" else "qwen3-4b-gguf" if gguf else "qwen2.5-1.5b"
        ),
        "input": message,
        "outcome": None,
        "accepted_outcome": None,
        "attempts": [],
        "validation_errors": [],
        "tool_result": None,
        "elapsed_ms": 0,
        "execution_mode": "simulated_tools" if execute_tools else "validation_only",
        "execute_tools": execute_tools,
        "execution_guard_policy": "evidence-grounding-v3",
        "non_execution_grounding_policy": "advisory_only_no_evidence_repair",
        "advisory_grounding_warnings": [],
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
    result["grounding_evidence"] = json.loads(json.dumps(analysis, default=str))
    messages = build_messages({"prompt": message, "tools": tools}, prompt_style)
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
        if gguf:
            from tunebench.gguf_model import generate_local, model_status
        else:
            from tunebench.live_model import generate_local, model_status

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
        schema_errors = list(errors)
        grounding_diagnostics = (
            _grounding_errors(prediction["outcome"], analysis, execute_tools=False)
            if not schema_errors
            else []
        )
        is_call = not schema_errors and prediction["outcome"]["type"] == "tool_call"
        semantic_errors = grounding_diagnostics if is_call else []
        advisory = grounding_diagnostics if not is_call else []
        errors.extend(semantic_errors)
        attempt = {
            "attempt": index + 1,
            "repair": index > 0,
            "raw_output": raw,
            "parsed_outcome": prediction["outcome"],
            "validation_errors": list(errors),
            "schema_valid": not schema_errors,
            "schema_errors": schema_errors,
            "grounding_errors": semantic_errors,
            "advisory_grounding_warnings": advisory,
            "latency_ms": (time.perf_counter() - attempt_start) * 1000,
        }
        result["attempts"].append(attempt)
        result["outcome"] = prediction["outcome"]
        result["validation_errors"] = list(errors)
        result["advisory_grounding_warnings"] = list(advisory)
        if not errors:
            break
        if index + 1 < attempts_allowed:
            feedback = "Your output failed validation: " + "; ".join(errors)[:2000]
            if semantic_errors:
                evidence = {
                    key: result["grounding_evidence"][key]
                    for key in ("intent", "order_ids", "reasons", "amounts", "ambiguities")
                }
                feedback += (
                    ". Evidence extracted from the request (not an answer key): "
                    + json.dumps(evidence, ensure_ascii=False)
                )
            messages += [
                {"role": "assistant", "content": raw},
                {
                    "role": "user",
                    "content": feedback
                    + ". Return one corrected JSON outcome only. Do not invent missing values.",
                },
            ]
    result["repair_attempted"] = len(result["attempts"]) > 1
    result["raw_first_attempt_valid"] = result["attempts"][0]["schema_valid"]
    result["repair_policy"] = (
        "at most one schema or tool-call evidence repair; "
        "non-executing grounding is advisory; no output rewriting"
    )
    if used_backend == "model":
        result["model_metadata"] = model_status()
    if result["validation_errors"]:
        result["policy_override"] = bool(result["attempts"][-1].get("grounding_errors"))
        result["status"] = "blocked"
        result["user_message"] = "No tool ran: the returned decision failed validation."
        return finish()
    outcome = result["outcome"]
    errors = (
        _grounding_errors(outcome, analysis, execute_tools=execute_tools)
        if outcome["type"] == "tool_call"
        else []
    )
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
