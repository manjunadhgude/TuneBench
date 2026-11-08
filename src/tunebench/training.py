"""Completion-only LoRA training, with explicit data and hardware prerequisites."""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any

from tunebench.contracts import validate_task
from tunebench.inference import DEFAULT_MODEL, build_messages


def prepare_training_records(
    train: list[dict[str, Any]], validation: list[dict[str, Any]]
) -> dict[str, list[dict[str, Any]]]:
    """Reject mislabeled partitions and family leakage before producing supervision."""
    partitions = {"train": train, "validation": validation}
    if not train or not validation:
        raise ValueError("nonempty train and validation partitions are required")
    seen_ids: set[str] = set()
    seen_scenarios: set[str] = set()
    families: dict[str, str] = {}
    prompts: dict[str, str] = {}
    result: dict[str, list[dict[str, Any]]] = {}
    for split, tasks in partitions.items():
        records = []
        for task in tasks:
            errors = validate_task(task)
            if errors:
                raise ValueError(f"invalid {split} task {task.get('example_id')!r}: {errors}")
            if task["split"] != split:
                raise ValueError(f"{split} export refuses task from split {task['split']!r}")
            if task["example_id"] in seen_ids or task["scenario_id"] in seen_scenarios:
                raise ValueError("duplicate example_id or scenario_id in training data")
            seen_ids.add(task["example_id"])
            seen_scenarios.add(task["scenario_id"])
            family = task["family_id"]
            if family in families and families[family] != split:
                raise ValueError(f"family leakage across partitions: {family}")
            families[family] = split
            prompt = " ".join(task["prompt"].casefold().split())
            if prompt in prompts and prompts[prompt] != split:
                raise ValueError("duplicate normalized prompt across partitions")
            prompts[prompt] = split
            expected = dict(task["expected_outcome"])
            # Gold clarification omits free-text question because it is not scored.
            if expected["type"] == "clarification":
                expected["question"] = (
                    "Please clarify " + ", ".join(expected["missing_fields"]) + "."
                    if expected["target_tool_name"] is not None
                    else "Which supported action would you like me to take?"
                )
            records.append(
                {
                    "example_id": task["example_id"],
                    "messages": build_messages(task, "strong"),
                    "completion": json.dumps(expected, ensure_ascii=False, sort_keys=True),
                }
            )
        result[split] = records
    return result


def export_training_data(
    train: list[dict[str, Any]], validation: list[dict[str, Any]], output_dir: str | Path
) -> dict[str, Any]:
    records = prepare_training_records(train, validation)
    directory = Path(output_dir)
    directory.mkdir(parents=True, exist_ok=True)
    for filename in ("train.jsonl", "validation.jsonl", "manifest.json"):
        if (directory / filename).exists():
            raise FileExistsError(f"refusing to overwrite training export: {directory / filename}")
    manifest: dict[str, Any] = {
        "format": "chat-prompt-completion",
        "prompt_style": "strong",
        "loss": "completion-only",
        "test_included": False,
        "files": {},
    }
    for split, rows in records.items():
        data = "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows)
        path = directory / f"{split}.jsonl"
        path.write_text(data, encoding="utf-8")
        manifest["files"][split] = {
            "path": str(path),
            "examples": len(rows),
            "sha256": hashlib.sha256(data.encode()).hexdigest(),
        }
    manifest_path = directory / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def tokenize_completion(
    record: dict[str, Any], tokenizer: Any, max_length: int = 2048
) -> dict[str, list[int]]:
    """Mask the exact chat-template prefix and fail on unsafe boundary/truncation."""
    if max_length < 1:
        raise ValueError("max_length must be positive")
    messages = record["messages"]
    prompt_ids = list(
        tokenizer.apply_chat_template(messages, tokenize=True, add_generation_prompt=True)
    )
    full_ids = list(
        tokenizer.apply_chat_template(
            [*messages, {"role": "assistant", "content": record["completion"]}],
            tokenize=True,
            add_generation_prompt=False,
        )
    )
    if full_ids[: len(prompt_ids)] != prompt_ids:
        raise ValueError("chat template does not preserve the assistant prefix boundary")
    if len(full_ids) <= len(prompt_ids):
        raise ValueError("chat template produced no completion tokens")
    if len(full_ids) > max_length:
        raise ValueError("example exceeds max_length; refusing to truncate supervised completion")
    return {
        "input_ids": full_ids,
        "attention_mask": [1] * len(full_ids),
        "labels": [-100] * len(prompt_ids) + full_ids[len(prompt_ids) :],
    }


def train_lora(
    train: list[dict[str, Any]],
    validation: list[dict[str, Any]],
    output_dir: str | Path,
    model_id: str = DEFAULT_MODEL,
    quantize: bool = False,
    max_length: int = 2048,
    epochs: float = 1.0,
    learning_rate: float = 2e-4,
    batch_size: int = 1,
    gradient_accumulation_steps: int = 8,
    seed: int = 42,
) -> dict[str, Any]:
    """Run actual GPU LoRA/QLoRA; no placeholder adapters or CPU training claims."""
    records = prepare_training_records(train, validation)
    if epochs <= 0 or learning_rate <= 0 or batch_size < 1 or gradient_accumulation_steps < 1:
        raise ValueError("epochs, learning rate, batch size and accumulation must be positive")
    output = Path(output_dir)
    if output.exists() and any(output.iterdir()):
        raise FileExistsError(f"training output directory is not empty: {output}")
    try:
        import torch
        from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
        from transformers import (
            AutoModelForCausalLM,
            AutoTokenizer,
            BitsAndBytesConfig,
            Trainer,
            TrainingArguments,
            set_seed,
        )
    except ImportError as exc:
        raise RuntimeError("Install TuneBench's [training] extra to fine-tune") from exc
    if not torch.cuda.is_available():
        raise RuntimeError("Fine-tuning requires a CUDA GPU; no training was started")
    if quantize:
        try:
            import bitsandbytes  # noqa: F401
        except ImportError as exc:
            raise RuntimeError("Install the [qlora] extra for 4-bit QLoRA") from exc
    set_seed(seed)
    tokenizer = AutoTokenizer.from_pretrained(model_id, trust_remote_code=False)
    if tokenizer.pad_token_id is None:
        tokenizer.pad_token = tokenizer.eos_token
    tokenized = {
        split: [tokenize_completion(row, tokenizer, max_length) for row in rows]
        for split, rows in records.items()
    }
    dtype = torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16
    kwargs: dict[str, Any] = {"torch_dtype": dtype, "trust_remote_code": False}
    if quantize:
        kwargs.update(
            quantization_config=BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_quant_type="nf4",
                bnb_4bit_compute_dtype=dtype,
                bnb_4bit_use_double_quant=True,
            ),
            device_map={"": 0},
        )
    model = AutoModelForCausalLM.from_pretrained(model_id, **kwargs)
    if quantize:
        model = prepare_model_for_kbit_training(model)
    else:
        model = model.to("cuda")
    model.config.use_cache = False
    model = get_peft_model(
        model,
        LoraConfig(
            r=16,
            lora_alpha=32,
            lora_dropout=0.05,
            bias="none",
            task_type="CAUSAL_LM",
            target_modules="all-linear",
        ),
    )

    def collate(examples: list[dict[str, list[int]]]) -> dict[str, Any]:
        width = max(len(row["input_ids"]) for row in examples)
        return {
            name: torch.tensor(
                [row[name] + [pad] * (width - len(row[name])) for row in examples],
                dtype=torch.long,
            )
            for name, pad in (
                ("input_ids", tokenizer.pad_token_id),
                ("attention_mask", 0),
                ("labels", -100),
            )
        }

    arguments = TrainingArguments(
        output_dir=str(output),
        num_train_epochs=epochs,
        learning_rate=learning_rate,
        per_device_train_batch_size=batch_size,
        per_device_eval_batch_size=batch_size,
        gradient_accumulation_steps=gradient_accumulation_steps,
        bf16=dtype == torch.bfloat16,
        fp16=dtype == torch.float16,
        eval_strategy="epoch",
        save_strategy="epoch",
        save_total_limit=2,
        logging_steps=1,
        report_to=[],
        seed=seed,
        data_seed=seed,
        remove_unused_columns=False,
    )
    trainer = Trainer(
        model=model,
        args=arguments,
        train_dataset=tokenized["train"],
        eval_dataset=tokenized["validation"],
        data_collator=collate,
    )
    torch.cuda.reset_peak_memory_stats()
    start = time.perf_counter()
    training_result = trainer.train()
    validation_metrics = trainer.evaluate()
    trainer.save_model(str(output / "adapter"))
    tokenizer.save_pretrained(output / "adapter")
    manifest = {
        "model_id": model_id,
        "resolved_model_revision": getattr(model.config, "_commit_hash", None),
        "quantization": "nf4" if quantize else None,
        "loss": "completion-only",
        "prompt_style": "strong",
        "max_length": max_length,
        "seed": seed,
        "train_examples": len(train),
        "validation_examples": len(validation),
        "test_included": False,
        "training_metrics": training_result.metrics,
        "validation_metrics": validation_metrics,
        "elapsed_seconds": time.perf_counter() - start,
        "peak_gpu_memory_bytes": torch.cuda.max_memory_allocated(),
        "torch_version": torch.__version__,
        "adapter_path": str(output / "adapter"),
        "hyperparameters": {
            "epochs": epochs,
            "learning_rate": learning_rate,
            "batch_size": batch_size,
            "gradient_accumulation_steps": gradient_accumulation_steps,
            "lora_rank": 16,
            "lora_alpha": 32,
            "lora_dropout": 0.05,
        },
        "data_sha256": {
            split: hashlib.sha256(
                json.dumps(rows, sort_keys=True, ensure_ascii=False).encode()
            ).hexdigest()
            for split, rows in records.items()
        },
    }
    output.mkdir(parents=True, exist_ok=True)
    (output / "training-manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    return manifest
