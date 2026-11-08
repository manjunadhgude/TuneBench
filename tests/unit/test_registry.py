"""Packaged assets must remain usable outside the checkout."""

import json
from pathlib import Path

from tunebench.contracts import CONFIG_DIR, SCHEMA_DIR, load_schema, load_tool_registry


def test_registry_has_three_agreed_mock_tools():
    tools = load_tool_registry()
    assert [tool["name"] for tool in tools] == [
        "get_order_status",
        "check_refund_eligibility",
        "propose_refund",
    ]
    assert tools[2]["parameters"]["required"] == ["order_id", "refund_amount", "reason"]
    assert tools[2]["parameters"]["properties"]["refund_amount"]["exclusiveMinimum"] == 0


def test_registry_load_returns_independent_values():
    tools = load_tool_registry()
    tools[0]["name"] = "changed"
    assert load_tool_registry()[0]["name"] == "get_order_status"


def test_schema_load_returns_independent_values():
    schema = load_schema("task.schema.json")
    schema["properties"]["schema_version"]["const"] = "broken"
    assert load_schema("task.schema.json")["properties"]["schema_version"]["const"] == "3.0.0"


def test_loaders_work_from_other_directory(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert load_schema("task.schema.json")["properties"]["schema_version"]["const"] == "3.0.0"
    assert len(load_tool_registry()) == 3


def test_packaged_and_reviewable_assets_agree():
    root = Path(__file__).resolve().parents[2]
    for directory, resource in [("schemas", SCHEMA_DIR), ("configs", CONFIG_DIR)]:
        for path in (root / directory).glob("*.json"):
            assert json.loads(path.read_text()) == json.loads(
                resource.joinpath(path.name).read_text(encoding="utf-8")
            ), path.name


def test_schema_and_evaluation_configuration_versions_agree():
    configuration = json.loads(CONFIG_DIR.joinpath("evaluation.json").read_text(encoding="utf-8"))
    assert configuration["evaluation_version"] == "0.2.0"
    assert (
        configuration["task_schema_version"]
        == (load_schema("task.schema.json")["properties"]["schema_version"]["const"])
    )
