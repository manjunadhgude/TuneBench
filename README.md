# TuneBench
A reproducible research and engineering framework for evaluating and fine-tuning small language models for reliable tool selection and argument generation.

TuneBench asks whether supervised fine-tuning improves a small instruction model over
a strong prompting baseline, under matched inference and evaluation conditions.
It evaluates one decision per request: a tool call, a clarification, or no tool.
The three e-commerce tools are **mock definitions**; no customer data, orders, or
payments are accessed or modified.

## Run locally or in a cloud development environment

Python 3.12 is the tested runtime; Python 3.11+ is supported. Codespaces is not required.

```bash
git clone https://github.com/manjunadhgude/TuneBench.git
cd TuneBench
bash scripts/setup.sh
source .venv/bin/activate
tunebench doctor
bash scripts/check.sh
```

Use the existing checkout when already working in this repository. `setup.sh` installs
the hash-locked core and development dependencies into `.venv`; model libraries are
optional. It supports uv or standard Python venv/pip. Package caches are kept under
the checkout's ignored `.cache/uv` directory because home may be read-only.
For another machine set `UV_CACHE_DIR` to a writable path if needed.

## Exercise the complete CPU pipeline

```bash
# Controlled fixtures verify the scorer; this does not run an LLM.
tunebench demo --output artifacts/runs/demo

# 20 smoke examples, or 1250 synthetic candidates with --full.
tunebench generate --output data/generated/smoke
tunebench generate --full --seed 42 --output data/generated/candidates
tunebench audit --data-dir data/generated/candidates

# Train/validation supervision only: 1000 + 125 records; test is excluded.
tunebench export-training --data-dir data/generated/candidates \
  --output data/generated/training

tunebench evaluate --gold artifacts/runs/demo/smoke.jsonl \
  --predictions artifacts/runs/demo/corrupted-fixture.jsonl \
  --output artifacts/runs/demo/rescored.json
tunebench compare --baseline artifacts/runs/demo/corrupted-report.json \
  --candidate artifacts/runs/demo/oracle-report.json \
  --output artifacts/runs/demo/comparison.json
```

Generation, inference, and training/export commands refuse to replace existing outputs.
Choose a new directory for each experiment. The demo scores 20 gold-derived fixture
predictions correctly and 18/20 after one null and one missing prediction. Those
numbers demonstrate evaluator behavior and **are not measured model performance**.

## Real models and fine-tuning

The candidate model is `Qwen/Qwen2.5-1.5B-Instruct`. Model downloads and inference are
explicit operations, not installation side effects:

```bash
uv pip install --python .venv/bin/python -e '.[model]'
tunebench infer --tasks data/generated/smoke/smoke.jsonl \
  --prompt-style strong --device cpu --output artifacts/runs/baseline-b.jsonl
tunebench evaluate --gold data/generated/smoke/smoke.jsonl \
  --predictions artifacts/runs/baseline-b.jsonl --output artifacts/runs/baseline-b-report.json

# On a separate CUDA GPU machine after data review and baseline measurements:
uv pip install --python .venv/bin/python -e '.[training]'
tunebench train --data-dir data/generated/candidates --output artifacts/runs/lora
```

Use `[qlora]` and `train --quantize` for optional four-bit QLoRA. Baselines A (`minimal`)
and B (`strong`) use the same greedy decoding, output validation, and zero-retry policy.
Use `infer --adapter artifacts/runs/lora/adapter --prompt-style strong` for the matched
fine-tuned comparison. Train/validation preparation and token-masking tests run offline.
CPU model loading and the first 20-example smoke run are now verified. GPU fine-tuning
remains unrun; no GPU is exposed here.
See the [first real-model results](artifacts/baseline-smoke/README.md) for raw outputs,
the measured score, and the tested CPU installation/download commands. Model downloads
use `huggingface.co` and `us.aws.cdn.hf.co`; no credentials are required for this public model.

## Experimental safeguards

- Task schema **3.0.0**, prediction capture schema v2, evaluation protocol **0.2.0**.
  The report derives its task version from the actual schema.
- Reports keep per-example errors, missing/invalid predictions, independent outcome
  credit, tool/argument exact matches, conditional clarification-field metrics,
  no-tool metrics, strict task success, and family/difficulty breakdowns.
- Comparison uses paired examples, matching gold hashes and evaluator versions, with
  family-cluster bootstrap intervals. Inference metadata sidecars are included in reports
  automatically; mismatched model revision, prompt or decoding needs `--allow-unmatched`
  for intentional ablations. Reports without run metadata warn that matching is unverified.
- Synthetic candidates use 30 disjoint families with 1000/125/125 train/validation/test
  counts, and one distinct scenario per example. They are **unreviewed and unfrozen**.
  Difficulty reflects template reasoning; the plan's conflicting difficulty quotas are
  reported as unmet. Limited template diversity prevents scientific claims of generalization.
- Review gold labels and semantic near-duplicates before finalizing the benchmark.
  Develop prompts/checkpoints on validation only. Accessing test through `infer` requires
  `--allow-test`; reserve that flag for the final, frozen experiment.
- Training applies loss to completion tokens only, rejects truncation and unsafe chat
  boundaries, and refuses smoke/test partitions or train/validation family leakage.

## Repository layout

| Path | Purpose |
| --- | --- |
| `src/tunebench/` | Contracts, generator/audit, evaluator, comparison, CLI, optional model/training runners |
| `schemas/`, `configs/` | Human-readable contract and benchmark configuration copies |
| `src/tunebench/resources/` | Packaged copies, tested for synchronization and wheel portability |
| `tests/` | Offline contract, metric, data-integrity, prompt-isolation, token-masking, and CLI tests |
| `scripts/` | Repeatable setup and full CPU validation |
| `docs/` | Dataset design, model workflow, and reconstruction/remaining work |

See [implementation status](docs/status.md), [dataset design](docs/dataset.md), and
[model workflow](docs/model-workflow.md). The implementation was reconstructed from
the supplied prior-work conversation and project plan; it is not a byte-for-byte
recovery of uncommitted Codespaces files. Commit and push reviewed changes to preserve
progress beyond the local development session.
