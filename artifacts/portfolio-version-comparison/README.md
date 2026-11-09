# Frozen v0.3 versus v0.4 system comparison

Both systems answered the same **20 fresh, frozen fictional questions** using the same pretrained Qwen2.5-1.5B-Instruct model on CPU. Every question remains in each denominator, including invalid, blocked and failed decisions. The data was assistant-authored and assistant-reviewed; it has no independent human annotation.

| System | Stage | Strictly correct / 20 | Correct outcome / 20 | Valid decisions / 20 |
| --- | --- | ---: | ---: | ---: |
| v0.3 | Original first answer | 8/20 | 11/20 | 13/20 |
| v0.3 | Accepted final decision | 2/20 | 4/20 | 5/20 |
| v0.4 | Original first answer | 9/20 | 12/20 | 19/20 |
| v0.4 | Accepted final decision | 7/20 | 7/20 | 7/20 |

Strict success requires the canonical decision and its required details. Clarification-question wording is checked only for contract validity, not human-graded helpfulness. Valid structure can still contain the wrong action or invented values. A blocked final decision is null and counts as a failure. Final success includes validation and bounded repair; it is not raw model accuracy. Candidate first answers also use token constraints, so this compares configured generation systems, not unconstrained model knowledge.

Original outputs parsed as JSON objects: v0.3 **16/20**, v0.4 **20/20**. Canonical schema-valid decisions are a separate metric: **13/20** and **19/20**, respectively.

## Matched conditions and intentional changes

The unchanged v0.3 source is `a6e143a`; the frozen v0.4 code matches commit `b7758905e3b9c268432883bfb02cd410d9c7fc29`. Source, data, model and selected runtime-library hashes were frozen before generation in [protocol.json](protocol.json). The full supplementary package inventory in [independent-audit.json](independent-audit.json) was captured during the legacy run and verified unchanged at the final audit; it is not a pre-generation freeze of every transitive dependency.

Both versions use model revision `989aa7980e4cf806f80c7fef2b1adb7bc71aa306`, CPU float32, four intra-operation threads, one inter-operation thread, seed 42, greedy decoding, one beam, 256 maximum new tokens, repetition penalty 1.1 and at most one repair. Full effective generation configurations match. No model weights were changed.

v0.4 changes the strong-v3 prompt, JSON token constraints, evidence grounding and repair feedback. v0.3 repairs parse/schema failures; v0.4 can also repair explicit request-evidence failures. This is a **system-version comparison**, not a prompt ablation or a fine-tuning experiment. No model answer is rewritten into the deterministic rules answer.

## Paired effects and cost

Original first answers: **3 improvements and 2 regressions**. Accepted final decisions: **7 improvements and 2 regressions**. Case IDs and validator/model failures are in [error-analysis.md](error-analysis.md).

v0.4's own final score still falls from 9/20 first answers to 7/20 accepted decisions: five correct first answers were lost, while three initially incorrect answers were repaired successfully. The revised guard improves the comparison with v0.3 but remains a source of failures.

| System | Generations | Repairs | Blocked finals | Runtime errors | Active case elapsed time on CPU |
| --- | ---: | ---: | ---: | ---: | ---: |
| v0.3 | 27 | 7 | 15 | 0 | 877.1 s |
| v0.4 | 36 | 16 | 13 | 0 | 1143.2 s |

Timing is the sum of recorded request wall times, including initial loading and repairs, excluding idle interruptions. It is not process CPU-seconds or a controlled hardware latency benchmark.

## Inspect or reproduce

- [Run protocol and resume rules](../../docs/version-comparison-protocol.md).
- [Frozen tasks](tasks.jsonl) and [dataset manifest](dataset-manifest.json).
- [Legacy raw captures](legacy/cases.partial.jsonl) and [candidate raw captures](candidate/cases.partial.jsonl).
- [Paired comparison](comparison.json) and [independent computational audit](independent-audit.json).

The audit reparsed original text, recomputed all scores, checked accepted decisions against generated outputs and verified source/model/runtime hashes and durable journal checkpoints. It performed no generation reruns and did not change labels. Historical evaluation artifacts remain separate.

These small synthetic results do not establish production accuracy, reliable real-world execution, general improvement or a training benefit. Tool execution was disabled for scoring; the application’s fictional business-policy simulation is tested separately. Any further implementation tuning needs development data and a new final test set.
