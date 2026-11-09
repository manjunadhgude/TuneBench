# Portfolio evaluation protocol

The portfolio evaluates one narrow GenAI task: select a tool call, ask for
clarification, or decline to call a tool. It separately demonstrates strict
validation, conservative grounding, one bounded repair, and simulated execution.
There is no fine-tuning and no real payment integration.

## Data and freezing

`datasets/portfolio-v1` contains 40 development cases and 20 held-out cases. All
60 were individually authored and semantically reviewed by the assistant;
independent human review is still outstanding. Cases are fictional. The manifest
records exact file hashes, sizes, counts, and limitations. The held-out file uses
the canonical `test` split. Entire input files are evaluated: no case is filtered
out for being difficult, invalid, blocked, or unsupported.

Development cases may inform implementation before the final run. Freeze data,
golds, prompt, model revision, guard, and repair policy before generating any
held-out output. After inspecting held-out output, do not change these items and
rerun the same holdout as though it were unseen. A later policy improvement needs
a new version and a fresh evaluation set. Historical smoke and prompt-development
experiments remain separate artifacts; their percentages use different data.

Before the first request, `scripts/evaluate_portfolio.py` writes `protocol.json`,
the exact task bytes, dataset manifest, and first-attempt messages. The protocol
includes SHA-256 hashes of data, source, packaged schemas/configuration, and the
verified local model manifest. It records the Git commit and whether uncommitted
work was present; file hashes identify the actual evaluated implementation.
Source/data/protocol hashes are checked between cases. A change aborts the run
while preserving the partial journal.

## Two backends and two model stages

Use these labels when presenting results:

| Result | What it measures |
| --- | --- |
| Deterministic rules baseline (not an LLM) | Handwritten parsing and guard decisions; zero model generation |
| Qwen raw first attempt | Original parsed first output before repair or acceptance filtering |
| Local Qwen with validation and bounded repair | Accepted product decision after schema/grounding checks and at most one repair |

Rules results must never be described as LLM accuracy. The final model stage is a
product pipeline measurement; it must not be described as raw model accuracy.
Save every original response and every repair in the case trace. A blocked/error
case with no accepted outcome becomes a null prediction and counts as invalid and
wrong in the final report, even if its rejected proposal looked plausible.

The existing canonical evaluator scores all three outcome types. Strict task
success requires a valid prediction and the exact decision details: tool and
arguments, clarification target/missing fields/reason, or no-tool reason.
Clarification predictions retain the required `question` capture field; question
wording is not an exact-match gold target. Outcome accuracy is a separate, weaker
metric. Both reports retain per-example details and the full denominator.

## Decisions and execution

The benchmark calls `respond(..., execute_tools=False)`. Accepted tool decisions
have status `validated`; fictional benchmark identifiers do not need to exist in
the five-order demonstration store. Schema and text-grounding checks still apply.
This mode avoids adding store membership or demo refund caps to the gold contract.

Reports count accepted decisions, blocks, operational errors, and repairs. They
explicitly state that execution is disabled. Zero executions in this mode is not
evidence of an execution guard's effectiveness. Guard/integration tests separately
check that invalid or hallucinated calls are blocked before the simulated tool is
invoked. Demo order lookup, refund-window checks, remaining-balance checks, and
proposal caps belong to that separate execution policy. Nothing transfers money.

## Reproducible CPU run

Use the verified, pinned local `Qwen/Qwen2.5-1.5B-Instruct` snapshot. The model
backend never downloads files. One cached model session serves all cases and
repairs. Use seed 42, CPU float32, four intra-operation threads, one inter-operation
thread, greedy decoding, one beam, 256 new tokens, and repetition penalty 1.1.
The saved runtime metadata records the full effective generation configuration
and library versions. The prompt style is `strong-v2`; repairs are guided only by
parse/schema errors, never by gold labels. Grounding failures block the call
without a repair; the frozen policy does not silently loosen after a rejection.

After the implementation and dataset are frozen, run the baselines into fresh,
separate directories:

```bash
.venv/bin/python scripts/evaluate_portfolio.py \
  --data datasets/portfolio-v1/holdout.jsonl \
  --outputdir artifacts/portfolio-evaluation/rules \
  --backend rules --max-repairs 1

OMP_NUM_THREADS=4 MKL_NUM_THREADS=4 OPENBLAS_NUM_THREADS=1 \
TOKENIZERS_PARALLELISM=false HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
.venv/bin/python scripts/evaluate_portfolio.py \
  --data datasets/portfolio-v1/holdout.jsonl \
  --outputdir artifacts/portfolio-evaluation/model \
  --backend model --max-repairs 1 \
  --model-path /path/to/verified/local/snapshot
```

The runner refuses to overwrite existing evidence. Each completed case is flushed
and synced to `cases.partial.jsonl` before progress is printed. There is no
automatic resume or rerun of failed cases. Interrupted runs retain their journal
and frozen protocol but do not produce completed reports. Operational failures
returned by the backend count as failed cases, with a
`completed_with_runtime_errors` status; do not hide them or present them as clean
model-quality evidence. `quality_claims_validated` is false if any operational
error occurred. If the model session cannot initialize, stop after preserving the
first failed checkpoint and save `run-status.json` with an incomplete status;
there is no completed model-quality report for a missing backend.

Completed runs save `raw-first.predictions.jsonl`, `raw-first.report.json`,
`final.predictions.jsonl`, `final.report.json`, `cases.jsonl`, `metadata.json`, and
`summary.json`. The dashboard may combine summaries with the same dataset hash.
Show counts such as `correct / 20`, limitations, and failure examples. Twenty
assistant-authored cases cannot establish production reliability or broad model
superiority. Runtime includes pipeline/model loading overhead and should not be
used as a controlled speed comparison between backends.
