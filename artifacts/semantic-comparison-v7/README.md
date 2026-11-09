# Semantic review and calculator comparison

Both versions answered the **same 40 new frozen fictional questions**. The primary
Qwen3 model, prompt, grammar and decoding are identical. v0.7 adds same-model review
of all decision kinds, review feedback for a bounded primary retry, and restricted
Decimal arithmetic checks for refund proposals. Extra review calls add compute.

| Version | First answers correct | Accepted final correct | Correct final tool calls |
| --- | ---: | ---: | ---: |
| v0.6 | 34/40 | 23/40 | 3/16 |
| v0.7 | 34/40 | 30/40 | 15/16 |

Every failed, invalid and blocked case stays in the denominator. First-answer and accepted-final scores measure different stages. Clarification wording is contract-checked, not human-graded. No tools executed during scoring.

## Final correctness by expected decision

| Decision | v0.6 | v0.7 |
| --- | ---: | ---: |
| Tool call | 3/16 | 15/16 |
| Clarification | 8/12 | 6/12 |
| No tool | 12/12 | 9/12 |

## Recorded cost and errors

| Version | Primary generations | Reviews | Total generations | Active case seconds | Incorrect accepted calls |
| --- | ---: | ---: | ---: | ---: | ---: |
| v0.6 | 51 | 0 | 51 | 272.6 | 0 |
| v0.7 | 48 | 47 | 95 | 751.7 | 1 |

v0.7 had 12 paired final improvements and 5 regressions. Its own guard/retry path lost 5 correct first answers and repaired 1 first-answer errors. It accepted 16 tool calls, of which 1 were incorrect by canonical scoring. Runtime errors: 0. See [all remaining failures](error-analysis.md). A zero observed incorrect-call count, if present, would not prove execution safety.

The extra model calls and longer review prompt affect latency; total compute is
not matched. Times sum recorded case wall time, including loading/retries and
excluding idle gaps. Shared CPU load and caching prevent treating this as a
controlled standalone model-speed benchmark.

## Freeze, authorship and limitations

The baseline source is `5559e30`; candidate source/runner was frozen at `eb4e227`.
Dataset commit `e020ef8` adds portfolio-v5 without inference changes. The same
implementing assistant authored/reviewed these 40 questions **after source freeze**.
There was no independent blind review or human annotation. Cases are targeted
fictional examples, not representative production traffic. The same-model reviewer
can share the proposer's errors. Arithmetic validation checks the expression's
numbers and result, but cannot guarantee that the correct facts/scope were chosen.

The first prompts match and gold labels never enter either generation stage.
No model weights were trained. These questions are now observed; additional tuning
requires development data and a new untouched test set. The earlier 7/20 result
uses different questions and is retained, not directly compared with this score.

## Evidence

- [Frozen protocol](protocol.json), [tasks](tasks.jsonl), [dataset manifest](dataset-manifest.json), and [run instructions](../../docs/semantic-comparison-protocol.md).
- [Original v0.6 captures](legacy/cases.partial.jsonl) and [v0.7 captures including raw reviews](candidate/cases.partial.jsonl).
- [Paired scores](comparison.json) and [score/review computational audit](score-and-review-audit.json).

The same assistant performed a separate computational audit: reparsing all original
primary/review text, recomputing canonical scores and Decimal results, checking
review prompt hashes, and verifying frozen source/data/model/library hashes and
durable journal checkpoints. No generation reruns, rewritten labels or substituted
outputs were used. This is not an external independent evaluation.
