"""The generation schema is stricter than the research capture contract."""

import builtins
import json
import os
import string
import sys
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace

import pytest
from jsonschema import Draft202012Validator

from tunebench.contracts import load_tool_registry, validate_prediction
from tunebench.structured import generation_schema, make_prefix_constraint


def decision(kind="tool_call", **fields):
    return {"type": kind, **fields}


def clarification(target="get_order_status", fields=None, reason="missing_required_information"):
    return decision(
        "clarification",
        target_tool_name=target,
        missing_fields=["order_id"] if fields is None else fields,
        reason_code=reason,
        question="Which order?",
    )


@pytest.fixture
def schema_validator():
    return Draft202012Validator(generation_schema())


@pytest.mark.parametrize(
    "outcome",
    [
        decision(tool_name="get_order_status", arguments={"order_id": "EXAMPLE-1"}),
        decision(
            tool_name="check_refund_eligibility",
            arguments={
                "order_id": "EXAMPLE-2",
                "reason": "damaged_item",
            },
        ),
        decision(
            tool_name="propose_refund",
            arguments={
                "order_id": "EXAMPLE-3",
                "reason": "wrong_item",
                "refund_amount": 1.25,
            },
        ),
        clarification(),
        clarification("propose_refund", ["refund_amount", "reason"], "ambiguous_reference"),
        clarification(None, [], "ambiguous_intent"),
        decision("no_tool", reason_code="informational_request"),
        decision("no_tool", reason_code="unsupported_request"),
        decision("no_tool", reason_code="no_action_requested"),
    ],
)
def test_valid_outcomes_match_strict_generation_and_capture_schemas(schema_validator, outcome):
    assert schema_validator.is_valid(outcome)
    assert (
        validate_prediction({"example_id": "example", "outcome": outcome}, load_tool_registry())
        == []
    )


@pytest.mark.parametrize(
    "outcome",
    [
        None,
        [],
        {"type": "made_up"},
        decision(tool_name=None, arguments=None),
        decision(tool_name="unknown", arguments={}),
        decision(tool_name="get_order_status", arguments={}),
        decision(tool_name="get_order_status", arguments={"order_id": 123}),
        decision(tool_name="get_order_status", arguments={"order_id": "X", "extra": 1}),
        decision(tool_name="get_order_status", arguments={"order_id": "X"}, commentary="extra"),
        decision(
            tool_name="propose_refund",
            arguments={
                "order_id": "X",
                "refund_amount": 0,
                "reason": "damaged_item",
            },
        ),
        decision(
            tool_name="propose_refund",
            arguments={
                "order_id": "X",
                "refund_amount": -1,
                "reason": "damaged_item",
            },
        ),
        decision(
            tool_name="propose_refund",
            arguments={
                "order_id": "X",
                "refund_amount": True,
                "reason": "damaged_item",
            },
        ),
        decision(
            tool_name="check_refund_eligibility", arguments={"order_id": "X", "reason": "bad"}
        ),
        clarification(fields=[]),
        clarification(fields=["reason"]),
        clarification(fields=["order_id", "order_id"]),
        clarification(target="unknown"),
        clarification(reason="invented_reason"),
        clarification(reason="ambiguous_intent"),
        clarification(None, ["order_id"], "ambiguous_intent"),
        clarification(None, [], "missing_required_information"),
        {**clarification(), "question": ""},
        {**clarification(), "question": None},
        {**clarification(), "extra": "not allowed"},
        decision("no_tool", reason_code="invented_reason"),
        decision("no_tool", reason_code="unsupported_request", question="extra"),
    ],
)
def test_invalid_outcomes_are_rejected_by_generation_schema(schema_validator, outcome):
    assert not schema_validator.is_valid(outcome)


def test_schema_only_contains_available_tools_and_does_not_mutate_inputs():
    tools = load_tool_registry()[:1]
    original = deepcopy(tools)
    schema = generation_schema(tools)
    validator = Draft202012Validator(schema)
    assert validator.is_valid(decision(tool_name="get_order_status", arguments={"order_id": "X"}))
    assert not validator.is_valid(
        decision(
            tool_name="propose_refund",
            arguments={
                "order_id": "X",
                "reason": "damaged_item",
                "refund_amount": 1,
            },
        )
    )
    assert tools == original
    schema["oneOf"][0]["properties"]["arguments"]["properties"]["order_id"]["type"] = "number"
    new_arguments = generation_schema(tools)["oneOf"][0]["properties"]["arguments"]
    assert new_arguments["properties"]["order_id"]["type"] == "string"


@pytest.mark.parametrize("tools", [[], {}, [None], [{"name": "bad"}]])
def test_invalid_tool_definitions_raise_actionable_errors(tools):
    with pytest.raises(ValueError, match="generation tools"):
        generation_schema(tools)


def test_duplicate_tools_are_rejected():
    tool = load_tool_registry()[0]
    with pytest.raises(ValueError, match="duplicate tool"):
        generation_schema([tool, deepcopy(tool)])


def test_optional_dependency_is_not_needed_for_schema_and_fails_clearly(monkeypatch):
    original_import = builtins.__import__

    def guarded_import(name, *args, **kwargs):
        if name.startswith("lmformatenforcer"):
            raise ImportError("optional dependency absent")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", guarded_import)
    assert generation_schema()
    with pytest.raises(RuntimeError, match="Install lm-format-enforcer"):
        make_prefix_constraint(object())


def test_adapter_delegates_to_official_transformers_prefix_builder(monkeypatch):
    captured = {}
    tokenizer = object()

    def callback(batch_id, tokens):
        return [7]

    class Parser:
        def __init__(self, schema):
            captured["schema"] = schema

    def builder(actual_tokenizer, parser):
        captured["tokenizer"] = actual_tokenizer
        captured["parser"] = parser
        return callback

    monkeypatch.setitem(sys.modules, "lmformatenforcer", SimpleNamespace(JsonSchemaParser=Parser))
    monkeypatch.setitem(
        sys.modules,
        "lmformatenforcer.integrations.transformers",
        SimpleNamespace(build_transformers_prefix_allowed_tokens_fn=builder),
    )
    assert make_prefix_constraint(tokenizer) is callback
    assert captured["tokenizer"] is tokenizer
    assert isinstance(captured["parser"], Parser)
    assert captured["schema"] == generation_schema()


def test_installed_parser_accepts_each_decision_branch_without_loading_models():
    library = pytest.importorskip("lmformatenforcer")
    examples = [
        decision(tool_name="get_order_status", arguments={"order_id": "EXAMPLE"}),
        decision(
            tool_name="check_refund_eligibility",
            arguments={
                "order_id": "EXAMPLE",
                "reason": "damaged_item",
            },
        ),
        decision(
            tool_name="propose_refund",
            arguments={
                "order_id": "EXAMPLE",
                "refund_amount": 1.25,
                "reason": "wrong_item",
            },
        ),
        clarification(),
        clarification("check_refund_eligibility", ["reason"], "ambiguous_reference"),
        clarification("propose_refund", ["refund_amount"]),
        clarification(None, [], "ambiguous_intent"),
        decision("no_tool", reason_code="unsupported_request"),
    ]
    for outcome in examples:
        parser = library.JsonSchemaParser(generation_schema())
        for character in json.dumps(outcome, separators=(",", ":")):
            assert character in parser.get_allowed_characters(), outcome
            parser = parser.add_character(character)
        assert parser.can_end(), outcome


def test_installed_transformers_adapter_masks_real_token_ids_without_a_model():
    pytest.importorskip("lmformatenforcer.integrations.transformers")
    from lmformatenforcer import TokenEnforcerTokenizerData

    # Character tokens exercise the real adapter and enforcer with no tokenizer
    # downloads, model weights, Torch generation, or external network requests.
    alphabet = string.printable[:95]
    token_ids = {character: index for index, character in enumerate(alphabet)}
    eos_id = len(alphabet)
    tokenizer_data = TokenEnforcerTokenizerData(
        [(index, character, False) for character, index in token_ids.items()],
        lambda ids: "".join(alphabet[index] for index in ids),
        eos_token_id=eos_id,
        use_bitmask=False,
        vocab_size=eos_id + 1,
    )
    allowed = make_prefix_constraint(tokenizer_data)
    generated = []

    def ids():
        return SimpleNamespace(tolist=lambda: list(generated))

    assert token_ids["{"] in allowed(0, ids())
    assert token_ids["n"] not in allowed(0, ids())
    text = '{"type":"no_tool","reason_code":"unsupported_request"}'
    for character in text:
        assert token_ids[character] in allowed(0, ids())
        generated.append(token_ids[character])
    assert eos_id in allowed(0, ids())


def test_existing_local_qwen_tokenizer_can_reach_every_decision_without_loading_weights():
    transformers = pytest.importorskip("transformers")
    pytest.importorskip("lmformatenforcer.integrations.transformers")
    from lmformatenforcer.integrations.transformers import build_token_enforcer_tokenizer_data

    snapshot = Path(
        os.environ.get(
            "TUNEBENCH_TEST_MODEL_PATH",
            "/workspace/models/Qwen2.5-1.5B-Instruct/989aa7980e4cf806f80c7fef2b1adb7bc71aa306",
        )
    )
    if not (snapshot / "tokenizer.json").is_file():
        pytest.skip("No existing local Qwen tokenizer; this check never downloads files")
    tokenizer = transformers.AutoTokenizer.from_pretrained(
        snapshot, local_files_only=True, trust_remote_code=False
    )
    shared_data = build_token_enforcer_tokenizer_data(tokenizer)
    prefix = tokenizer.apply_chat_template(
        [
            {"role": "system", "content": "Return one JSON decision."},
            {"role": "user", "content": "Execute a real refund payment for order SAMPLE-1."},
        ],
        tokenize=True,
        add_generation_prompt=True,
    )
    outcomes = [
        decision("no_tool", reason_code="unsupported_request"),
        clarification("propose_refund", ["refund_amount"]),
        clarification(None, [], "ambiguous_intent"),
        decision(tool_name="get_order_status", arguments={"order_id": "SAMPLE-1"}),
    ]
    for outcome in outcomes:
        # Reuse vocabulary data, but initialize a new grammar for every request.
        allowed = make_prefix_constraint(shared_data)
        sequence = list(prefix)
        for token_id in tokenizer.encode(json.dumps(outcome, separators=(",", ":"))):
            assert token_id in allowed(
                0, SimpleNamespace(tolist=lambda sequence=sequence: list(sequence))
            ), outcome
            sequence.append(token_id)
        assert tokenizer.eos_token_id in allowed(
            0, SimpleNamespace(tolist=lambda sequence=sequence: list(sequence))
        ), outcome
