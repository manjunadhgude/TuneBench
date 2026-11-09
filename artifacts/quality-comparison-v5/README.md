# Frozen v0.4 versus v0.5 quality comparison

Both complete systems answered the same **40 new, frozen fictional support questions**. Every question remains in each denominator, including invalid, blocked and failed outputs. Data was assistant-authored and assistant-reviewed; this is not independent human annotation.

| System | Stage | Strictly correct / 40 | Correct outcome / 40 | Schema-valid decisions / 40 |
| --- | --- | ---: | ---: | ---: |
| v0.4 | Original first answer | 21/40 | 27/40 | 37/40 |
| v0.4 | Accepted final decision | 16/40 | 18/40 | 19/40 |
| v0.5 | Original first answer | 37/40 | 38/40 | 40/40 |
| v0.5 | Accepted final decision | 32/40 | 33/40 | 39/40 |

Strict success checks the canonical outcome and all required details. Valid structure can still contain the wrong action or invented facts. Clarification question wording is checked only for contract validity, not human-graded helpfulness. A blocked final decision is null and counts as failure. Accepted final quality includes validation and bounded repair; report it separately from the original first answer.

Original texts parsed as JSON objects: **40/40** for v0.4 and **40/40** for v0.5. Schema-valid decisions are a separate measure.

The candidate itself changes from **37/40** original first answers to **32/40** accepted finals: the guard/repair pipeline loses 6 correct first answers and repairs 1 initial errors. That remaining degradation is a validator limitation that should remain visible alongside the paired results. Incorrect accepted candidate decisions: **7**, including **0** tool calls; non-executing mistakes still count as failures. Tools were disabled during scoring.

Candidate breakdown by reference outcome:

| Reference outcome | Original first correct | Accepted final correct |
| --- | ---: | ---: |
| tool_call | 15/16 | 9/16 |
| clarification | 10/12 | 11/12 |
| no_tool | 12/12 | 12/12 |

## Frozen systems and intentional differences

Baseline source: `7498d78` (v0.4), Qwen2.5-1.5B-Instruct float32 through Torch/Transformers with LM Format Enforcer. Candidate source: `5d52dc8` (v0.5), Qwen3-4B-Instruct-2507 through llama.cpp using Unsloth's pinned Q4_K_M GGUF conversion. The quantized artifact is a third-party conversion of the official Qwen model. No model was fine-tuned.

Model weights, quantization, runtime, prompt, JSON constraints and guard/repair policy change together. This is a **system-version comparison**, not an isolated model or prompt experiment. Both use CPU execution, four generation threads, seed 42, greedy decoding, at most 256 new tokens and at most one repair. Exact identities, hashes and runtime settings are retained in [protocol.json](protocol.json). The canonical scoring code and tool contracts are identical. Both sources and the data were frozen before either worker generated a test answer. The fixed order was candidate, then baseline.

## Paired effects and observed cost

Original first answers: **17 improvements and 1 regressions**. Accepted final decisions: **16 improvements and 0 regressions**. See [error-analysis.md](error-analysis.md) for case-level effects and remaining failures.

| System | Generations | Repairs | Blocked finals | Runtime errors | Active case elapsed time on CPU |
| --- | ---: | ---: | ---: | ---: | ---: |
| v0.4 | 67 | 27 | 21 | 0 | 2460.0 s |
| v0.5 | 47 | 7 | 1 | 0 | 290.4 s |

These are recorded request wall times, including initial loading and repairs, excluding idle pauses. Different models, quantization, caching and libraries prevent interpreting them as a controlled model-speed benchmark.

## Evidence and limits

- [Frozen tasks](tasks.jsonl) and [dataset manifest](dataset-manifest.json).
- [Original baseline captures](legacy/cases.partial.jsonl) and [candidate captures](candidate/cases.partial.jsonl).
- [Matched comparison](comparison.json), [independent computational audit](independent-audit.json), and [run protocol](../../docs/quality-comparison-protocol.md).

The audit reparsed original text, independently checked strict matches, recomputed canonical scores and verified source/model/runtime hashes and durable journals. It made no generation reruns or label changes. The supplementary full package inventory was captured during candidate generation and verified unchanged; the pre-generation protocol froze selected libraries.

These 40 curated synthetic questions do not establish production accuracy, broad generalization, independent reasoning families or real execution safety. Tools were disabled for decision scoring; fictional business-policy execution is checked separately. Clarification prose has no independent human helpfulness grade. This test set is now observed; further tuning needs development data and a new final test set. Historical results remain unchanged and use different questions.
