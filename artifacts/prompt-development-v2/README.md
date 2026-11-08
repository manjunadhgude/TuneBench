# Versioned prompt development on CPU

This experiment compares the existing `strong` prompt (`strong-v1`) with a clearer
`strong-v2` policy on the same 12 new, reviewed development examples. No model weights
are trained or changed. The earlier 7/20 smoke result remains unchanged in
`artifacts/baseline-smoke/` and uses different questions; its percentage is not a
paired baseline for these 12 cases.

## Observed results

| Check | Legacy `strong` | Revised `strong-v2` |
| --- | ---: | ---: |
| Fully correct tasks | 2/12 (16.7%) | 5/12 (41.7%) |
| Correct outcome class | 4/12 | 6/12 |
| Schema-valid predictions | 6/12 | 7/12 |
| Parseable JSON responses | 11/12 | 10/12 |
| Model loading/inference/validation time | 295.9 s | 349.4 s |

Four cases improved (`dv2-04`, `dv2-06`, `dv2-07`, `dv2-12`), one regressed
(`dv2-02`), and seven kept the same full-task result. The net gain is three cases,
or 25 percentage points, on this constructed development set. The descriptive
family-bootstrap interval spans -8.3 to +58.3 percentage points and includes zero;
this is not evidence of a statistically established or general improvement.

The revised instructions fix a refund call's outcome tag, two missing-information
clarification cases, and a closing no-action decision. Remaining errors include a
tool-call format regression, missed contextual IDs, an empty invented ID, an
incorrectly resolved ambiguous action, two prose answers, and substituting a simulated
proposal for an explicitly requested real payment. See [the error analysis](error-analysis.md).
JSON syntax is worse by one response, so the higher full-task score does not mean
uniformly more reliable formatting. The normal CLI exactly reproduces both saved reports.

Keep `strong-v2` as an explicit development candidate; the legacy defaults are unchanged.
Review broader development cases and strengthen decision/format behavior before
selecting the final research prompt or starting fine-tuning. Never repair these outputs
or change their gold labels to raise the recorded score.

## Design

- Four tool calls, four clarification requests, and four no-tool cases.
- Hand-authored validation records with fresh values and wording, including contextual
  reference selection, wrong/not-received items, refund arithmetic, absent arguments,
  ambiguous action, information questions, actual-payment requests, and closing thanks.
- The dataset author did not inspect the revised instructions or model outputs; the
  prompt author did not inspect this development set. Both were frozen before generation.
- The data review and SHA-256 are recorded in
  [the development review](../../docs/development-review-v2.md).
- The final test set is excluded. These cases still cover related domain concepts;
  fresh family IDs and wording do not prove semantic independence or generalization.

## What changed in the instructions

`strong-v2` distinguishes outcome types from tool names, defines each reason code,
uses actual JSON null, explains how to handle missing/conflicting values, and gives
four generic contract-valid examples. It preserves the original input boundary:
only the user's request and tool definitions enter the prompt. Gold answers and
benchmark IDs are excluded. The old `minimal` and `strong` prompts remain identical;
the CLI exposes the revised version explicitly as `--prompt-style strong-v2`.

## Controlled comparison

`paired-run/protocol.json` was written before any generation. It records the exact
source/input hashes, both system prompts, model assets, prompt order, CPU threads,
seed, generation overrides, and inherited generation configuration.

Both runs use the pinned Qwen2.5-1.5B-Instruct base model, CPU float32, four compute
threads, greedy decoding, one beam, a 256-token limit, repetition penalty 1.1, the
same stop IDs, and no retries or repairs. A guard requires equal non-prompt conditions
before permitting the intentional prompt difference in the comparison.

Each run retains raw responses, latency, complete effective decoding configuration,
prompt/system/message hashes, checkpoint journals and final reports. A partial
journal alone is not evidence that a run completed. The process peak-RSS metadata
is cumulative; it does not isolate the second run's memory allocation.

Run order is fixed (`strong`, then `strong-v2`), so timings are descriptive and cannot
establish a speed advantage. Any bootstrap interval is descriptive on this small,
constructed set, with no claim of statistical significance.

## Reproduce

Use the verified model download and CPU installation from
[the initial smoke experiment](../baseline-smoke/README.md), then run:

```bash
OMP_NUM_THREADS=4 MKL_NUM_THREADS=4 OPENBLAS_NUM_THREADS=1 \
TOKENIZERS_PARALLELISM=false HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
.venv/bin/python scripts/run_prompt_development.py \
  --snapshot /workspace/models/Qwen2.5-1.5B-Instruct/989aa7980e4cf806f80c7fef2b1adb7bc71aa306 \
  --tasks artifacts/prompt-development-v2/development.jsonl \
  --output artifacts/runs/prompt-development-reproduction
```

Choose a new output directory. The helper refuses non-validation input and protects
existing results. Preserve each prompt version and its original score; develop any
later revision separately before making research or fine-tuning claims.
