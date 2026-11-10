# Focused terminal-decision reliability fix: v0.7.1

A fallible reviewer previously rejected a correct no-tool decision and induced a
retry into an unauthorized refund proposal. v0.7.1 makes **schema-valid no-tool
and clarification decisions terminal**. They receive no model review or retry.
Schema-invalid output remains repairable. Tool-call review, arithmetic validation,
literal ID checking, and mock business-policy gates remain in place.

This is a bounded application-policy fix. The primary model can still make an
incorrect initial call or abstain unnecessarily. A terminal answer is not assumed
to be semantically correct just because it executes nothing.

## The original failure is reproduced and fixed

[The replay](known-failure-replay.json) uses the original captured primary/reviewer
text for `portfolio-v5-holdout-40`, with an execution spy that never runs a tool.
It is a regression replay, not fresh inference or an accuracy estimate.

| Source | Primary attempts | Reviews | Attempts to invoke a tool |
| --- | ---: | ---: | ---: |
| v0.7 | 2 | 2 | 1 |
| v0.7.1 | 1 | 0 | 0 |

The original first answer is preserved unchanged. The patched result remains
`no_tool/no_action_requested`. The old replay's final blocked status comes from
the spy deliberately preventing execution; its attempted tool call is the defect.
The regression tests failed before the patch and pass afterward. They also cover
all three no-tool reasons, clarification, schema repair, and execution boundaries.

## Twelve new targeted CPU requests

Source and runner were frozen at `09dd1bc` before the 12 cases were written.
Dataset commit `fc73510` freezes six expected tool calls, two clarifications, and
four no-tool cases. The same implementing assistant authored/reviewed them;
there was no independent blind or human annotation. The set deliberately targets
this failure mode, not representative production accuracy.

Both frozen versions use the same pinned Qwen3 GGUF, primary prompt, decoding,
review prompt, schemas, and evaluator. Candidate runs first, then the archived
v0.7 source at `a8b668c`. Only customer text and tool definitions enter generation;
gold is used only for scoring. Tools are disabled. Every case is retained,
including incorrect answers. No labels or inference code changed after generation.

| Metric | v0.7 | v0.7.1 |
| --- | ---: | ---: |
| Correct first answers | 10/12 | 10/12 |
| Correct final answers | 10/12 | 11/12 |
| Correct final tool calls | 5/6 | 5/6 |
| Correct final clarifications | 2/2 | 2/2 |
| Correct final no-tool decisions | 3/4 | 4/4 |

All six expected non-executing cases are correct in v0.7.1. No incorrect tool calls were accepted in these 12 candidate cases. The fresh baseline also had no review-induced action escalation on these particular cases; the paired saved-failure replay above demonstrates that defect directly. Zero observed incidents in a small set is not a general safety guarantee.

| Recorded work across 12 requests | v0.7 | v0.7.1 |
| --- | ---: | ---: |
| Primary generations | 16 | 13 |
| Review generations | 16 | 6 |
| Active case seconds | 253.9 | 151.9 |

These are descriptive case wall times, including loading/retries, on shared CPU
resources. They are not a controlled latency benchmark. Non-executing decisions
skip review by construction, reducing model calls without rewriting their output.

## Remaining failure and scope

Both versions miss `terminal-v1-11`: a legitimate request to propose the discounted
price of a damaged item. The final answer is an incorrect no-tool decision. This
ordinary model-quality limitation remains in the raw captures and scores; it was
not patched after observing the test. The focused escalation fix is complete.
No new application features, larger benchmark, or fine-tuning work were added.

The historical 40-case v0.7 result remains 30/40 and is not relabeled as v0.7.1
accuracy. These new 12 questions cannot be compared directly with that cohort or
the historical 7/20 result.

## Evidence and audit

- [Frozen protocol](protocol.json), [tasks](tasks.jsonl), [manifest](manifest.json), and [author rationale](annotation-ledger.json).
- [Original v0.7 records](legacy/cases.jsonl) and [v0.7.1 records](candidate/cases.jsonl).
- [Computational audit](audit.json) and [known-failure replay](known-failure-replay.json).
- [Live browser regression](../../docs/assets/terminal-browser-v0.7.1.json) and [current screenshot](../../docs/assets/terminal-decision-v0.7.1.png).

The same assistant separately reparsed original outputs, recomputed canonical
scores, checked accepted-output identity, terminal invariants, journal hashes,
frozen source/data/model/runtime hashes, and identical primary prompt hashes.
There were no generation reruns. This is not an external independent audit.
The editable package metadata was upgraded only after the frozen check and audit.

Run `bash scripts/check.sh` for offline verification. To reproduce the native
check, archive `a8b668c` for legacy and `fc73510` for candidate into separate
folders, then invoke `scripts/check_terminal_reliability.py` from the candidate
archive with `--legacy-root`, `--candidate-root`, `--data` pointing to the archived
`datasets/terminal-v1/holdout.jsonl`, `--model` pointing to the pinned local GGUF,
and a **new** `--output` directory. Reproduction uses already observed data and
is not a new unseen test. Interrupted native checks preserve captures/inflight
markers and are not automatically rerun or resumed.
