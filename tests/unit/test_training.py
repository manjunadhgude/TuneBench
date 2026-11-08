import json
from copy import deepcopy

import pytest

from tunebench.contracts import load_tool_registry
from tunebench.training import (
    export_training_data,
    prepare_training_records,
    tokenize_completion,
)


@pytest.fixture
def partitions():
    def task(split):
        return {
            "schema_version": "3.0.0",
            "example_id": f"{split}-001",
            "family_id": f"{split}-family",
            "scenario_id": f"{split}-scenario",
            "split": split,
            "difficulty": "medium",
            "prompt": f"Please propose a refund for order {split}-A123; the amount is missing.",
            "tools": load_tool_registry(),
            "expected_outcome": {
                "type": "clarification",
                "target_tool_name": "propose_refund",
                "missing_fields": ["refund_amount", "reason"],
                "reason_code": "missing_required_information",
            },
        }

    return [task("train")], [task("validation")]


def test_export_has_supervised_completion_and_no_gold_in_prompt(partitions, tmp_path):
    train, validation = partitions
    manifest = export_training_data(train, validation, tmp_path)
    assert manifest["test_included"] is False
    assert manifest["files"]["train"]["examples"] == 1
    record = json.loads((tmp_path / "train.jsonl").read_text())
    completion = json.loads(record["completion"])
    assert completion["missing_fields"] == ["refund_amount", "reason"]
    assert completion["question"]
    assert "expected_outcome" not in json.dumps(record["messages"])
    assert (tmp_path / "manifest.json").is_file()


@pytest.mark.parametrize("forbidden_split", ["test", "smoke", "validation"])
def test_training_rejects_non_training_records(partitions, forbidden_split):
    train, validation = partitions
    train[0]["split"] = forbidden_split
    with pytest.raises(ValueError, match="refuses task from split"):
        prepare_training_records(train, validation)


def test_cross_split_family_leakage_rejected(partitions):
    train, validation = partitions
    validation[0]["family_id"] = train[0]["family_id"]
    with pytest.raises(ValueError, match="family leakage"):
        prepare_training_records(train, validation)


def test_cross_split_duplicate_prompts_rejected(partitions):
    train, validation = partitions
    validation[0]["prompt"] = "  " + train[0]["prompt"].upper() + "  "
    with pytest.raises(ValueError, match="normalized prompt"):
        prepare_training_records(train, validation)


def test_duplicate_scenario_rejected(partitions):
    train, validation = partitions
    validation[0]["scenario_id"] = train[0]["scenario_id"]
    with pytest.raises(ValueError, match="scenario_id"):
        prepare_training_records(train, validation)


def test_test_record_never_exported_as_validation(partitions):
    train, validation = partitions
    validation[0]["split"] = "test"
    with pytest.raises(ValueError, match="refuses task from split"):
        prepare_training_records(train, validation)


class CharacterChatTokenizer:
    """A deterministic chat template fixture with a measurable assistant boundary."""

    def apply_chat_template(self, messages, tokenize, add_generation_prompt):
        text = "".join(f"<{message['role']}>{message['content']}!" for message in messages)
        if add_generation_prompt:
            text += "<assistant>"
        return list(text.encode())


def test_only_completion_tokens_have_loss_labels(partitions):
    train, validation = partitions
    record = prepare_training_records(train, validation)["train"][0]
    tokenizer = CharacterChatTokenizer()
    result = tokenize_completion(record, tokenizer, max_length=10000)
    prompt = tokenizer.apply_chat_template(record["messages"], True, True)
    boundary = len(prompt)
    assert result["input_ids"][:boundary] == prompt
    assert result["labels"][:boundary] == [-100] * boundary
    assert result["labels"][boundary:] == result["input_ids"][boundary:]
    assert bytes(result["input_ids"][boundary:]).decode() == record["completion"] + "!"


def test_truncation_cannot_remove_or_partially_cut_supervision(partitions):
    record = prepare_training_records(*partitions)["train"][0]
    tokenizer = CharacterChatTokenizer()
    boundary = len(tokenizer.apply_chat_template(record["messages"], True, True))
    with pytest.raises(ValueError, match="refusing to truncate"):
        tokenize_completion(record, tokenizer, max_length=boundary)
    with pytest.raises(ValueError, match="refusing to truncate"):
        tokenize_completion(record, tokenizer, max_length=boundary + 1)


def test_unsupported_template_boundary_rejected(partitions):
    class IncompatibleTemplate(CharacterChatTokenizer):
        def apply_chat_template(self, messages, tokenize, add_generation_prompt):
            ids = super().apply_chat_template(messages, tokenize, add_generation_prompt)
            return [999] + ids if add_generation_prompt else ids

    record = prepare_training_records(*partitions)["train"][0]
    with pytest.raises(ValueError, match="assistant prefix boundary"):
        tokenize_completion(record, IncompatibleTemplate(), max_length=10000)


def test_export_refuses_to_overwrite_prior_artifacts(partitions, tmp_path):
    export_training_data(*partitions, tmp_path)
    prior = (tmp_path / "train.jsonl").read_bytes()
    with pytest.raises(FileExistsError, match="refusing to overwrite"):
        export_training_data(*partitions, tmp_path)
    assert (tmp_path / "train.jsonl").read_bytes() == prior


def test_training_data_preparation_does_not_mutate_gold(partitions):
    original = deepcopy(partitions)
    prepare_training_records(*partitions)
    assert original == partitions
