# Portfolio v1: frozen decision evaluation

This is a deliberately difficult, small fictional holdout: 20 cases (10 medium,
10 hard), with 8 tool calls, 6 clarifications, and 6 no-tool outcomes. The separate
40-case development set was not mixed into these scores. The same assistant authored
and reviewed the data; there is no independent human annotation or production sampling.

The measured result is negative for the current grounding policy. The workbench
makes this visible; it does not establish a reliable autonomous support agent.

| Measurement | Rules baseline (not an LLM) | Qwen first attempt | Accepted Qwen product decision |
| --- | ---: | ---: | ---: |
| Full task success | 6/20 | 7/20 | 3/20 |
| Correct outcome class | 11/20 | 12/20 | 7/20 |
| Valid/accepted decision | 20/20 | 15/20 | 11/20 |

All 20 cases remain in each denominator. A rejected final decision is represented
as null and counts as incorrect/invalid; the original generated decision stays in
the trace. These rows measure different stages and must not be conflated with each
other or the older 20-case smoke / 12-case development experiments.

## What the result means

- Four correct raw answers were lost to grounding checks: a corrected order reference,
  two supported calculations, and a punctuation-rich order ID.
- The guard also accepted an incorrect choice between ambiguous order IDs. Conservative
  pattern checks therefore neither guarantee semantic correctness nor improve accuracy.
- Five repair attempts produced no strict-success gains on this holdout. Twenty first
  generations plus five repairs were retained, for 25 total generations.
- Final statuses were 9 blocked, 7 clarifications, 2 no-tool decisions and 2 validated
  tool calls. Only three of those final decisions fully match the gold contract.
- No operational/backend errors occurred. This establishes that the workflow ran;
  it does not establish that its model decisions are good enough for real users.

The [error analysis](error-analysis.md) records concrete cases and tradeoffs.
Future improvements must use development data and a separately versioned evaluation,
without changing these labels or repairing these saved outputs after the fact.

## Execution and safety scope

This runner uses `execute_tools=False`: it measures canonical decisions without
requiring benchmark IDs to exist in the five-order demo store. Zero tool executions
are expected and are not evidence that all unsafe calls are blocked. Application
execution controls are checked separately by unit, CLI, AppTest and browser flows.
The interactive tool handlers only read fictional data or form nonmutating proposals.
No real customer system, order mutation or payment operation exists.

## Reproducibility and interruption

The model is the unchanged public `Qwen/Qwen2.5-1.5B-Instruct`, revision
`989aa7980e4cf806f80c7fef2b1adb7bc71aa306`. Verified weights, tokenizer/support files,
CPU float32, four compute threads, seed 42, `strong-v2`, greedy decoding, repetition
penalty 1.1, a 256-token cap and at most one parse/schema repair were frozen before
generation. Grounding failures receive no repair retry. Model weights were not trained.

The original worker stopped during a pause after six cases. The recovery validated
all source/data/model/library hashes and the original six-case journal prefix, then
generated only the remaining fourteen cases. `model/resume-events.json` records
this audited exception to the original fresh-run-only runner. No completed case
was regenerated or selected based on whether its output was successful.

The reported **804.44 seconds** sum active per-case response runtimes, including
two model startups, and exclude idle interruption time. This is not one continuous
wall-clock benchmark. Timings are descriptive for the shared CPU environment.

The final [integrity audit](integrity-audit.md) independently verifies the preserved
prefix, 20 unique ordered cases, unchanged frozen hashes, matching runtime settings,
raw/last/final captures, and exact recomputation of both evaluator reports.

## Files

- `summary.json`: combined dashboard rows, with rules and model stages labelled.
- `rules/`: deterministic baseline protocol, cases, predictions and reports.
- `model/protocol.json`: original frozen model evaluation protocol.
- `model/cases.jsonl`: all 20 response traces, attempts, errors and accepted decisions.
- `model/raw-first.report.json`: raw model first-attempt results.
- `model/final.report.json`: accepted product-decision results.
- `model/resume-events.json`: interruption/recovery evidence and prefix hashes.
- `integrity-audit.md`, `error-analysis.md`: independent read-only reviews.
