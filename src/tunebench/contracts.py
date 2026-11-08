"""Portable, offline validation of TuneBench task and prediction records.

The prediction schema is a capture format: null outputs can be recorded without
losing the original response. Evaluators must count a null outcome as invalid.
"""

import json
import math
import re
from copy import deepcopy
from datetime import datetime
from functools import lru_cache
from importlib.resources import files
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import SchemaError, UnknownType
from referencing.exceptions import Unresolvable

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCHEMA_DIR = files("tunebench").joinpath("resources", "schemas")
CONFIG_DIR = files("tunebench").joinpath("resources", "configs")
FORMAT_CHECKER = FormatChecker()


@FORMAT_CHECKER.checks("date-time", raises=(ValueError, TypeError))
def _is_date_time(value: Any) -> bool:
    """Check timestamps without jsonschema's optional RFC3339 dependency."""
    if not isinstance(value, str):
        return True  # The schema's type keyword handles other JSON types.
    if not re.fullmatch(
        r"\d{4}-\d{2}-\d{2}[Tt]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:[Zz]|[+-]\d{2}:\d{2})",
        value,
    ):
        return False
    return datetime.fromisoformat(value.upper().replace("Z", "+00:00")).tzinfo is not None


@lru_cache(maxsize=8)
def _packaged_validator(name: str, location: str) -> Draft202012Validator:
    # location is part of the cache key so a replaced resource directory is not
    # confused with the original one. Packaged assets are immutable within a run.
    if name not in {"task.schema.json", "prediction.schema.json"}:
        raise ValueError(f"Unknown schema: {name!r}")
    schema = json.loads(SCHEMA_DIR.joinpath(name).read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, format_checker=FORMAT_CHECKER)


def load_schema(name: str) -> dict[str, Any]:
    """Return an independent packaged schema, independent of the current directory."""
    return deepcopy(_packaged_validator(name, str(SCHEMA_DIR)).schema)


def _format_validation_errors(
    validator: Draft202012Validator, record: Any, prefix: str = ""
) -> list[str]:
    errors = sorted(
        validator.iter_errors(record),
        key=lambda error: (tuple(map(str, error.absolute_path)), error.message),
    )
    result = []
    for error in errors:
        path = "/".join(map(str, error.absolute_path))
        path = f"{prefix}/{path}" if prefix and path else prefix or path or "<root>"
        result.append(f"{path}: {error.message}")
    return result


def _finite_errors(value: Any, path: str = "<root>") -> list[str]:
    if isinstance(value, float) and not math.isfinite(value):
        return [f"{path}: non-finite numbers are not JSON values"]
    errors = []
    if isinstance(value, dict):
        for key, item in value.items():
            errors.extend(_finite_errors(item, f"{path}/{key}"))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            errors.extend(_finite_errors(item, f"{path}/{index}"))
    return errors


def validate_record(record: Any, schema_name: str) -> list[str]:
    validator = _packaged_validator(schema_name, str(SCHEMA_DIR))
    return _format_validation_errors(validator, record) + _finite_errors(record)


def _external_references(value: Any) -> bool:
    if isinstance(value, dict):
        for key, item in value.items():
            if key in {"$ref", "$dynamicRef"} and isinstance(item, str):
                if not item.startswith("#"):
                    return True
            if _external_references(item):
                return True
    elif isinstance(value, list):
        return any(_external_references(item) for item in value)
    return False


@lru_cache(maxsize=256)
def _checked_parameters(serialized: str) -> tuple[str, ...]:
    """Cache by content so mutating an embedded schema cannot reuse stale checks."""
    parameters = json.loads(serialized)
    errors = []
    try:
        Draft202012Validator.check_schema(parameters)
    except (SchemaError, UnknownType) as exc:
        errors.append(f"invalid JSON Schema: {exc}")
    if _external_references(parameters):
        errors.append("external schema references are not supported")
    return tuple(errors)


@lru_cache(maxsize=256)
def _parameter_validator(serialized: str) -> Draft202012Validator:
    return Draft202012Validator(json.loads(serialized), format_checker=FORMAT_CHECKER)


def _tool_errors(tools: list[dict[str, Any]]) -> list[str]:
    errors = []
    seen = set()
    for index, tool in enumerate(tools):
        prefix = f"tools/{index}"
        if not isinstance(tool, dict):
            errors.append(f"{prefix}: tool must be an object")
            continue
        name = tool.get("name")
        if not isinstance(name, str) or not name.strip():
            errors.append(f"{prefix}/name: must be a non-empty string")
        elif name in seen:
            errors.append(f"{prefix}/name: duplicate tool name {name!r}")
        else:
            seen.add(name)
        if not isinstance(tool.get("description"), str) or not tool["description"].strip():
            errors.append(f"{prefix}/description: must be a non-empty string")
        parameters = tool.get("parameters")
        if not isinstance(parameters, dict) or parameters.get("type") != "object":
            errors.append(f"{prefix}/parameters: must be an object parameter schema")
            continue
        serialized = json.dumps(parameters, sort_keys=True, separators=(",", ":"))
        errors.extend(f"{prefix}/parameters: {error}" for error in _checked_parameters(serialized))
    return errors


@lru_cache(maxsize=8)
def _packaged_tools(location: str) -> list[dict[str, Any]]:
    registry = json.loads(CONFIG_DIR.joinpath("tool_registry.json").read_text(encoding="utf-8"))
    if not isinstance(registry, dict) or registry.get("registry_version") != "1.0.0":
        raise ValueError("Unsupported or malformed tool registry version")
    tools = registry.get("tools")
    if not isinstance(tools, list) or not tools:
        raise ValueError("Tool registry must contain a non-empty tools list")
    errors = _tool_errors(tools)
    if errors:
        raise ValueError("Invalid tool registry: " + "; ".join(errors))
    return tools


def load_tool_registry() -> list[dict[str, Any]]:
    """Return an independent copy of the canonical three mock tool definitions."""
    return deepcopy(_packaged_tools(str(CONFIG_DIR)))


def _outcome_errors(outcome: dict[str, Any], tools: list[dict[str, Any]], prefix: str) -> list[str]:
    errors = []
    by_name = {tool["name"]: tool for tool in tools}
    if outcome["type"] == "tool_call":
        name = outcome["tool_name"]
        arguments = outcome["arguments"]
        if not isinstance(name, str) or not name.strip():
            errors.append(f"{prefix}.tool_name: must be a non-empty string")
        elif name not in by_name:
            errors.append(f"{prefix}.tool_name: {name!r} is not in tools")
        elif isinstance(arguments, dict):
            validator = _parameter_validator(
                json.dumps(by_name[name]["parameters"], sort_keys=True, separators=(",", ":"))
            )
            try:
                errors.extend(
                    _format_validation_errors(validator, arguments, f"{prefix}.arguments")
                )
            except (Unresolvable, RecursionError) as exc:
                errors.append(f"{prefix}.arguments: unresolvable parameter schema: {exc}")
            for field, value in arguments.items():
                if isinstance(value, str) and not value.strip():
                    errors.append(f"{prefix}.arguments/{field}: must not be whitespace-only")
        if not isinstance(arguments, dict):
            errors.append(f"{prefix}.arguments: must be an object")
    elif outcome["type"] == "clarification":
        name = outcome["target_tool_name"]
        if name is not None:
            if not name.strip():
                errors.append(f"{prefix}.target_tool_name: must not be whitespace-only")
            elif name not in by_name:
                errors.append(f"{prefix}.target_tool_name: {name!r} is not in tools")
            else:
                required = set(by_name[name]["parameters"].get("required", []))
                unknown = sorted(set(outcome["missing_fields"]) - required)
                if unknown:
                    errors.append(f"{prefix}.missing_fields: unknown required fields: {unknown}")
    return errors


def validate_task(record: Any) -> list[str]:
    """Validate a gold task including embedded tools and outcome semantics."""
    errors = validate_record(record, "task.schema.json")
    if errors:
        return errors
    for field in ("example_id", "family_id", "scenario_id", "prompt"):
        if not record[field].strip():
            errors.append(f"{field}: must not be whitespace-only")
    tools_errors = _tool_errors(record["tools"])
    errors.extend(tools_errors)
    if not tools_errors:
        errors.extend(
            _outcome_errors(record["expected_outcome"], record["tools"], "expected_outcome")
        )
    return errors


def validate_prediction(record: Any, tools: list[dict[str, Any]] | None = None) -> list[str]:
    """Check capture structure, and tool-specific semantics when tools are supplied.

    Null outcomes are allowed by the capture contract, not valid model decisions.
    The evaluator reports them separately so raw malformed responses are retained.
    """
    errors = validate_record(record, "prediction.schema.json")
    if errors:
        return errors
    if not record["example_id"].strip():
        errors.append("example_id: must not be whitespace-only")
    if tools is not None and record["outcome"] is not None:
        tool_errors = _tool_errors(tools)
        errors.extend(tool_errors)
        if not tool_errors:
            errors.extend(_outcome_errors(record["outcome"], tools, "outcome"))
    return errors
