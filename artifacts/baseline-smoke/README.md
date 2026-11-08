# First real-model smoke experiment

This directory retains a small engineering check of the base instruction model,
without TuneBench fine-tuning. It is not the final benchmark or evidence that
fine-tuning helps.

## Observed result

| Check | Result |
| --- | --- |
| Full task success | 7/20 (35%) |
| Correct outcome class | 11/20 (55%) |
| Schema-valid predictions | 13/20 (65%) |
| Parseable JSON | 20/20 (100%) |
| Model loading plus inference/validation | 507.6 seconds (about 8.5 minutes) |
| Mean / median generation latency | 25.23 / 24.08 seconds per question |
| Process peak RSS | 9.00 GiB |

The normal CLI independently reproduced the saved report exactly. No outputs were
repaired, retried, excluded, or relabeled. The first seven status/eligibility calls
passed fully; all other examples failed at least one strict requirement.

The main mistakes were confusing the outcome type with a tool name, inventing missing
arguments, and mixing up no-tool/clarification decisions or reason codes. The initial
prompt needs clearer examples and reason-code definitions before it can serve as a
strong research baseline. Improve it on reviewed development data, preserve this
initial result, and keep the eventual final test separate.

- Model: `Qwen/Qwen2.5-1.5B-Instruct`, public, Apache-2.0.
- Pinned revision: `989aa7980e4cf806f80c7fef2b1adb7bc71aa306`.
- Weights SHA-256: `dd924a11b4c220f385b51ffa522daea7c9f3d850e31b162bb5661df483c6d3ee`.
- Data: the 20 seed-42 smoke records, checked in [the semantic review](../../docs/smoke-review.md).
- Prompt: the existing strong prompt, chosen before seeing this run's outputs.
- Inference: CPU float32, four compute threads, greedy decoding, maximum 256 new tokens,
  one attempt per question, no retries or output repair.
- Other generation defaults come from the verified `generation_config.json`, including
  repetition penalty 1.1. Explicit metadata overrides set sampling off and one beam.
- No final-test records, model fine-tuning, or prompt changes are part of this experiment.

`strong/report.json` contains the actual scores and per-example diagnostics;
`strong/strong.predictions.jsonl` retains raw model text and parsed outputs.
The metadata sidecar records the pinned model revision, source/runner hashes,
versions, input checksum, threads, wall time, and process peak memory.
`runtime-packages.json` records the installed package versions.

`elapsed_seconds` includes model loading, inference and output validation, excluding
the download and model-file verification. Each `latency_ms` measures generation,
including tokenization/prefill/decoding; it excludes output parsing and scoring.
Peak RSS measures the Python process on Linux, not all host or container memory.

## Reproduce on a CPU machine

Run the repository's normal setup, then install the tested optional model stack:

```bash
bash scripts/setup.sh
UV_CACHE_DIR="$PWD/.cache/uv" uv pip install --python .venv/bin/python \
  --torch-backend cpu 'torch==2.8.0' 'transformers==4.57.6' 'accelerate==1.15.0'

.venv/bin/python scripts/download_smoke_model.py \
  --output /workspace/models/Qwen2.5-1.5B-Instruct/989aa7980e4cf806f80c7fef2b1adb7bc71aa306

OMP_NUM_THREADS=4 MKL_NUM_THREADS=4 OPENBLAS_NUM_THREADS=1 \
TOKENIZERS_PARALLELISM=false HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
.venv/bin/python scripts/run_smoke_baseline.py \
  --snapshot /workspace/models/Qwen2.5-1.5B-Instruct/989aa7980e4cf806f80c7fef2b1adb7bc71aa306 \
  --tasks artifacts/baseline-smoke/smoke.jsonl \
  --output artifacts/runs/smoke-reproduction
```

Choose another writable model directory outside managed cloud environments, and a
new output directory for each run. The downloader uses the retained upstream
metadata to verify the official weights and support files; existing valid downloads
are reused. The runner verifies those hashes again before loading. No model weights
are committed to Git. Artifact access needs `huggingface.co` and `us.aws.cdn.hf.co`.

Interpret results cautiously: the questions are deliberately easy and templated,
cover only the damaged-item refund reason, and have no hard or ambiguous-target cases.
Any successful score is a pipeline milestone, not a claim of generalization.
