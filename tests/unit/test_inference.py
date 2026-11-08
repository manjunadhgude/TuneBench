import hashlib
import json
import sys
from contextlib import nullcontext
from copy import deepcopy
from types import SimpleNamespace

import pytest

from tunebench.contracts import load_tool_registry, validate_prediction
from tunebench.inference import (
    STRONG_V2_EXAMPLES,
    build_messages,
    generate_predictions,
    parse_output,
    run_inference,
)


@pytest.fixture
def inference_task():
    return {
        "schema_version": "3.0.0",
        "example_id": "secret-example-label",
        "family_id": "secret-family-label",
        "scenario_id": "secret-scenario-label",
        "split": "validation",
        "difficulty": "easy",
        "prompt": "Where is order A123?",
        "tools": load_tool_registry(),
        "expected_outcome": {
            "type": "tool_call",
            "tool_name": "get_order_status",
            "arguments": {"order_id": "SECRET-GOLD-ARGUMENT"},
        },
        "provenance": {"source_type": "manual", "reviewed_by": "secret-reviewer"},
    }


def test_prompt_never_includes_labels_or_benchmark_metadata(inference_task):
    for style in ("minimal", "strong", "strong-v2"):
        messages = build_messages(inference_task, style)
        text = json.dumps(messages)
        for secret in (
            "secret-example-label",
            "secret-family-label",
            "secret-scenario-label",
            "SECRET-GOLD-ARGUMENT",
            "secret-reviewer",
            "expected_outcome",
        ):
            assert secret not in text
        assert messages[-1] == {"role": "user", "content": inference_task["prompt"]}
        assert "propose_refund" in messages[0]["content"]


@pytest.mark.parametrize("style", ["minimal", "strong", "strong-v2"])
def test_prompt_is_unchanged_when_gold_changes(inference_task, style):
    changed = deepcopy(inference_task)
    changed["expected_outcome"] = {"type": "no_tool", "reason_code": "unsupported_request"}
    assert build_messages(changed, style) == build_messages(inference_task, style)


@pytest.mark.parametrize(
    ("style", "expected_hash"),
    [
        ("minimal", "bc067316246925f01dfbb4b299cb3fca7b34ac70e9a43ad2dee3ade4c0aad44c"),
        ("strong", "f72c80a8fab921cf1804780c16da36f0dfe28488d6933e2a7d573c059ba3867d"),
    ],
)
def test_legacy_prompt_messages_have_frozen_hashes(inference_task, style, expected_hash):
    serialized = json.dumps(
        build_messages(inference_task, style),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    assert hashlib.sha256(serialized.encode()).hexdigest() == expected_hash


def test_strong_v2_examples_obey_prediction_contract(inference_task):
    assert len(STRONG_V2_EXAMPLES) in {2, 3, 4}
    for index, (prompt, outcome) in enumerate(STRONG_V2_EXAMPLES):
        assert prompt
        assert (
            validate_prediction(
                {"example_id": f"prompt-example-{index}", "outcome": outcome},
                inference_task["tools"],
            )
            == []
        )
    instruction = build_messages(inference_task, "strong-v2")[0]["content"]
    assert '"target_tool_name":null' in instruction
    assert '"target_tool_name":"null"' not in instruction
    assert "missing_required_information = absent required values" in instruction
    assert "unsupported_request = requested action unavailable" in instruction


def test_strong_v2_prompt_and_record_have_separate_hashes(inference_task):
    record = generate_predictions([inference_task], lambda _messages: "bad output", "strong-v2")[0]
    metadata = record["metadata"]
    assert metadata["prompt_version"] == "strong-v2"
    messages = build_messages(inference_task, "strong-v2")
    assert (
        metadata["system_prompt_sha256"]
        == hashlib.sha256(messages[0]["content"].encode()).hexdigest()
    )
    assert len(metadata["prompt_template_sha256"]) == 64
    assert metadata["messages_sha256"] != metadata["system_prompt_sha256"]


def test_callback_receives_annotated_record_once_and_cannot_mutate_result(inference_task):
    calls = []
    received = []

    def backend(_messages):
        calls.append(True)
        return '{"type":"tool_call","tool_name":"get_order_status","arguments":{}}'

    def callback(record):
        assert record["metadata"]["validation_errors"]
        assert record["latency_ms"] >= 0
        assert record["metadata"]["prompt_version"] == "strong-v1"
        received.append(deepcopy(record))
        record["outcome"] = None

    result = generate_predictions([inference_task], backend, on_prediction=callback)
    assert len(calls) == len(received) == 1
    assert result[0]["outcome"] == received[0]["outcome"]


def test_callback_failure_propagates_before_next_generation(inference_task):
    second = deepcopy(inference_task)
    second["example_id"] = "second-example"
    calls = []

    def backend(_messages):
        calls.append(True)
        return "bad output"

    def callback(record):
        assert record["metadata"]["parse_error"]
        raise OSError("checkpoint failed")

    with pytest.raises(OSError, match="checkpoint failed"):
        generate_predictions([inference_task, second], backend, on_prediction=callback)
    assert calls == [True]


def test_run_inference_records_and_uses_inherited_generation_config(inference_task, monkeypatch):
    """Use small fake backends; this test never loads a tokenizer or model."""
    generated_configs = []
    checkpointed = []

    class Configuration:
        def __init__(self):
            self.values = {
                "do_sample": True,
                "num_beams": 3,
                "max_new_tokens": 77,
                "pad_token_id": None,
                "repetition_penalty": 1.1,
                "eos_token_id": [15, 16],
                "temperature": 0.6,
                "top_k": 20,
            }

        def update(self, **kwargs):
            self.values.update(kwargs)

        def to_dict(self):
            return deepcopy(self.values)

    class Tensor:
        shape = (1, 10)

        def to(self, device):
            assert device == "cpu"
            return self

        def __getitem__(self, key):
            return self

    class Model:
        config = SimpleNamespace(max_position_embeddings=1000, _commit_hash="test-revision")
        generation_config = Configuration()

        def to(self, device):
            assert device == "cpu"
            return self

        def eval(self):
            pass

        def generate(self, inputs, attention_mask, generation_config):
            generated_configs.append(generation_config.to_dict())
            return Tensor()

    tokenizer = SimpleNamespace(
        pad_token_id=None,
        eos_token_id=15,
        apply_chat_template=lambda *args, **kwargs: Tensor(),
        decode=lambda *args, **kwargs: '{"type":"no_tool","reason_code":"unsupported_request"}',
    )
    fake_torch = SimpleNamespace(
        __version__="fake-torch",
        float32="float32",
        float16="float16",
        bfloat16="bfloat16",
        cuda=SimpleNamespace(is_available=lambda: False),
        inference_mode=nullcontext,
        ones_like=lambda inputs: Tensor(),
    )
    fake_transformers = SimpleNamespace(
        __version__="fake-transformers",
        AutoModelForCausalLM=SimpleNamespace(from_pretrained=lambda *args, **kwargs: Model()),
        AutoTokenizer=SimpleNamespace(from_pretrained=lambda *args, **kwargs: tokenizer),
    )
    monkeypatch.setitem(sys.modules, "torch", fake_torch)
    monkeypatch.setitem(sys.modules, "transformers", fake_transformers)
    predictions, metadata = run_inference(
        [inference_task],
        model_id="test-model",
        prompt_style="strong-v2",
        max_new_tokens=88,
        on_prediction=checkpointed.append,
    )
    effective = metadata["effective_generation_config"]
    assert generated_configs == [effective]
    assert effective["repetition_penalty"] == 1.1
    assert effective["eos_token_id"] == [15, 16]
    assert effective["temperature"] == 0.6
    assert effective["top_k"] == 20
    assert effective["do_sample"] is False
    assert effective["num_beams"] == 1
    assert effective["max_new_tokens"] == 88
    assert effective["pad_token_id"] == 15
    assert Model.generation_config.to_dict()["do_sample"] is True
    assert predictions == checkpointed
    assert metadata["prompt_version"] == "strong-v2"


@pytest.mark.parametrize(
    "output",
    [
        "not JSON",
        '```json\n{"type":"no_tool","reason_code":"unsupported_request"}\n```',
        '[{"type":"no_tool"}]',
        '{"type":"no_tool","type":"tool_call"}',
        '{"arguments":{"refund_amount":NaN}}',
        '{"arguments":{"refund_amount":Infinity}}',
        '{"arguments":{"refund_amount":1e999}}',
        '{"type":"no_tool"} trailing words',
    ],
)
def test_invalid_json_retains_original_output_without_repair(output):
    record = parse_output("test-001", output)
    assert record["outcome"] is None
    assert record["raw_output"] == output
    assert record["metadata"]["parse_error"]
    assert validate_prediction(record) == []


def test_wrong_outcome_schema_retains_parsed_evidence():
    record = parse_output("test-001", '{"made_up":"shape"}')
    assert record["outcome"] == {"made_up": "shape"}
    assert validate_prediction(record)


def test_single_generation_and_latency_without_retry(inference_task):
    calls = []

    def backend(messages):
        calls.append(messages)
        return "bad model response"

    predictions = generate_predictions([inference_task], backend)
    assert len(calls) == 1
    record = predictions[0]
    assert record["outcome"] is None
    assert record["metadata"]["attempts"] == 1
    assert record["latency_ms"] >= 0
    assert record["raw_output"] == "bad model response"


def test_runtime_errors_propagate_instead_of_becoming_model_failures(inference_task):
    def backend(_messages):
        raise RuntimeError("out of memory")

    with pytest.raises(RuntimeError, match="out of memory"):
        generate_predictions([inference_task], backend)


def test_duplicate_tasks_fail_before_any_generation(inference_task):
    calls = []
    with pytest.raises(ValueError, match="duplicate example_id"):
        generate_predictions(
            [inference_task, inference_task], lambda messages: calls.append(messages)
        )
    assert calls == []


def test_empty_inference_is_rejected():
    with pytest.raises(ValueError, match="empty"):
        generate_predictions([], lambda messages: "{}")
