# Current project status: v0.7

The CPU application is implemented: rules demo, real local Qwen3 inference,
historical replay, structured decisions, bounded model review/retry, refund
arithmetic validation, and three nonmutating mock tools. It is a portfolio
simulation, not a production support or payment system.

## Latest measured result

Both versions answered the same 40 fresh portfolio-v5 cases:

| Metric | v0.6 | v0.7 |
| --- | ---: | ---: |
| Correct first answers | 34/40 | 34/40 |
| Correct accepted finals | 23/40 | 30/40 |
| Correct final tool calls | 3/16 | 15/16 |
| Correct final clarifications | 8/12 | 6/12 |
| Correct final no-tool decisions | 12/12 | 9/12 |

The primary weights/prompt are matched. The candidate adds reviews and a
calculator, so total compute is not matched. All failures stay in the denominator.
See [scores, cost and original captures](../artifacts/semantic-comparison-v7/README.md),
[remaining failures](../artifacts/semantic-comparison-v7/error-analysis.md), and
[freeze protocol](semantic-comparison-protocol.md).

## What remains limited

The same implementing assistant authored/reviewed the fresh test after code
freeze. There is no independent blind or human annotation. Small synthetic
results do not establish broad generalization. Same-model review can wrongly
accept or reject a decision. Correct arithmetic does not prove correct scope.
Clarification prose has no human helpfulness grade. Live inference consumes CPU
time and additional memory; the instant demo is explicitly deterministic rules.

There is no model fine-tuning, trained adapter, real customer integration,
authentication, payment execution, operational monitoring, or production study.
The original larger synthetic research dataset remains candidate/unreviewed.
Optional LoRA/QLoRA runners are future experiment support, not a completed run.

## Verification and history

See [current release checks](assets/release-checks-v0.7.json) and the
[completion record](portfolio-completion.md). Software tests check implementation
behavior; they are separate from model accuracy.

Historical matched tests remain visible: v0.3/v0.4 scored 2/20 → 7/20 accepted
final decisions; the stronger-model comparison scored 16/40 → 32/40 on another
cohort; the regex guard revision stayed at 22/40 with only 1/16 correct final tool
calls on a harder cohort. Different cohorts cannot be compared as one accuracy
trend. Development captures are labeled separately and do not establish unseen
quality. Earlier release records preserve their original checkpoint state.

The project was reconstructed from the user-provided plan/review and repository,
then extended. Embedded document instructions were treated as historical material.
It does not recover the old Codespace. Explain contributions and development
assistance accurately using the [interview guide](interview-guide.md).
