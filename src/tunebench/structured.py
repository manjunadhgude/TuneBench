"""Strict model-decision schemas and optional token-level JSON constraints.

This generation contract excludes malformed/null decisions retained by the
research capture format. Token constraints improve structure, not business-rule
correctness: callers must still run normal prediction and execution validation.
"""

from __future__ import annotations

from collections.abc import Callable
from copy import deepcopy
from typing import Any

from jsonschema import Draft202012Validator

from tunebench.contracts import load_tool_registry, validate_prediction


def _object(properties: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": "object",
        "properties": properties,
        "required": list(properties),
        "additionalProperties": False,
    }


def generation_schema(tools: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Build a strict, independent schema for the tools actually available.

    Each call names a specific tool and uses its argument schema. Clarification
    fields are required arguments of that same tool, never arbitrary strings.
    Ambiguous intent has a literal null target and no missing fields.
    """
    actual_tools = load_tool_registry() if tools is None else deepcopy(tools)
    if not isinstance(actual_tools, list) or not actual_tools:
        raise ValueError("generation tools must be a nonempty list")
    tool_errors = validate_prediction(
        {
            "example_id": "generation-schema-validation",
            "outcome": {"type": "no_tool", "reason_code": "informational_request"},
        },
        actual_tools,
    )
    if tool_errors:
        raise ValueError("invalid generation tools: " + "; ".join(tool_errors))
    branches = []
    for tool in actual_tools:
        name = tool["name"]
        parameters = deepcopy(tool["parameters"])
        parameters["additionalProperties"] = False
        branches.append(
            _object(
                {
                    "type": {"const": "tool_call"},
                    "tool_name": {"const": name},
                    "arguments": parameters,
                }
            )
        )
        required_fields = parameters.get("required", [])
        if required_fields:
            branches.append(
                _object(
                    {
                        "type": {"const": "clarification"},
                        "target_tool_name": {"const": name},
                        "missing_fields": {
                            "type": "array",
                            "items": {"type": "string", "enum": required_fields},
                            "minItems": 1,
                            "maxItems": len(required_fields),
                            "uniqueItems": True,
                        },
                        "reason_code": {
                            "enum": ["missing_required_information", "ambiguous_reference"]
                        },
                        "question": {"type": "string", "minLength": 1},
                    }
                )
            )
    branches.extend(
        [
            _object(
                {
                    "type": {"const": "clarification"},
                    "target_tool_name": {"type": "null"},
                    "missing_fields": {"type": "array", "maxItems": 0},
                    "reason_code": {"const": "ambiguous_intent"},
                    "question": {"type": "string", "minLength": 1},
                }
            ),
            _object(
                {
                    "type": {"const": "no_tool"},
                    "reason_code": {
                        "enum": [
                            "informational_request",
                            "unsupported_request",
                            "no_action_requested",
                        ]
                    },
                }
            ),
        ]
    )
    schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "TuneBench strict model decision",
        "oneOf": branches,
    }
    Draft202012Validator.check_schema(schema)
    return schema


def make_prefix_constraint(
    tokenizer: Any, tools: list[dict[str, Any]] | None = None
) -> Callable[..., list[int]]:
    """Create the Transformers ``prefix_allowed_tokens_fn`` without loading models.

    lm-format-enforcer is imported only when constrained generation is requested.
    Library versions can omit numeric bounds, array bounds, and uniqueness
    checks. Callers must retain post-generation validation of the complete schema.
    """
    schema = generation_schema(tools)
    try:
        from lmformatenforcer import JsonSchemaParser
        from lmformatenforcer.integrations.transformers import (
            build_transformers_prefix_allowed_tokens_fn,
        )
    except ImportError as exc:
        raise RuntimeError(
            "Install lm-format-enforcer to enable constrained JSON generation"
        ) from exc
    return build_transformers_prefix_allowed_tokens_fn(tokenizer, JsonSchemaParser(schema))
