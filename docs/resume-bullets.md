# Resume and portfolio wording

Choose statements you understand and can demonstrate. Describe your actual
contribution, including assistance used during development. If you integrated,
extended or tested a component rather than writing it independently, use that verb.

## Project description

**TuneBench — CPU tool-calling workbench and evaluation framework**
Python, llama.cpp/GGUF, JSON Schema, Streamlit, pytest; legacy Hugging Face
Transformers and optional PEFT training support.

A customer-support simulation with explicit tool-call, clarification and no-tool
outcomes, a trace of original answers and validation, and reproducible CPU model
evaluation. No real payment system is connected.

## Choose two or three bullets

- Integrated a verified quantized Qwen3-4B local CPU model with JSON-constrained
  generation, typed tool decisions and three nonmutating support tools in Streamlit.
- Added request-evidence checks before tool execution and bounded model repair,
  keeping original output intact; made heuristic diagnostics advisory for
  schema-valid non-executing decisions to avoid retries into actions.
- Built deterministic scoring for decision type, tool selection, arguments,
  clarification and strict success, retaining malformed, blocked and missing
  predictions in per-example diagnostics.
- Compared frozen system versions with pinned source/model/data hashes, original
  outputs, durable case journals, regression analysis and computational score audit.
- Tested the shared Python package, CLI and UI, including portable packaged
  contracts and standalone-wheel execution outside the source checkout.

Use wording such as “Integrated and tested” or “Extended an AI-assisted
implementation with …” when that reflects your contribution. Prepare to explain
a concrete change and its verification rather than reciting the entire feature list.

## Measured claims

The new 40-question comparison and independent score audit are still running at
this checkpoint. Add a numerical resume claim only after that report is complete,
using both versions on the same cases, the exact denominator and a link to evidence.
Include the tool-call result separately so an aggregate cannot hide false blocks.
Do not turn the tuned 40/40 development run into a claim of unseen accuracy.

The earlier weak result remains visible: on the same historical 20 questions,
v0.3/v0.4 raw strict success changed 8/20 → 9/20, schema validity 13/20 → 19/20 and
accepted final success 2/20 → **7/20**. That report exposed guard/repair failures and
motivated the new CPU model and policy. See the
[retained comparison](../artifacts/portfolio-version-comparison/README.md).
It must not be compared directly with a score from the new 40 cases.

The current full local software suite passes 469 tests; fresh app setup passes
465 with four optional checks skipped, and core-only passes 459 with five skips.
Evidence is in the [v0.5 release record](assets/release-checks-v0.5.json). A software
test count is distinct from successful model conversations. Quote the latest
completed count when submitting, and rerun `bash scripts/check.sh` after code changes.

## Accurate boundaries

The preferred model uses Unsloth's existing Q4_K_M conversion of official Qwen3
weights. This project integrates and evaluates it; it has not fine-tuned Qwen or
measured a LoRA benefit. Optional training preparation/runners are implemented,
while a GPU training experiment is not completed evidence.

The model, quantization, runtime, prompt and guard change together in the system
comparison. It cannot isolate which component caused a gain. Portfolio cases are
fictional and assistant-authored/reviewed, with no independent human annotation.
A small test result does not establish production accuracy or payment automation.

Link the repository, [architecture](architecture.md), [demo walkthrough](demo-script.md)
and completed experiment report. Be ready to explain both the improvement and the
remaining failures honestly.
