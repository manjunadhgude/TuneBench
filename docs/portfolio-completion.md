# Portfolio completion and evidence

The planned portfolio app and the approved focused reliability fix are implemented.
The current release is v0.7.1. Broader model research and production deployment
remain outside this interview-level project.

## Current patch verification

- [x] Correct no-tool/clarification decisions are terminal; review cannot retry them into actions.
- [x] The original captured failure is reproduced with an execution spy and fixed.
- [x] Full offline workflow passes 559 tests, lint, formatting, CLI/data checks and training export.
- [x] Frozen paired native CPU check completes on all 12 new targeted requests.
- [x] Original outputs, remaining failure, freeze protocol and computational audit are retained.

Current package/browser evidence is recorded in [the patch release record](assets/release-checks-v0.7.1.json).
See [targeted model results](../artifacts/terminal-reliability-v071/README.md).
The native candidate scores 11/12, including all six no-tool/clarification cases
and five of six tool-call cases. This small targeted result is not a general
accuracy estimate. One legitimate tool request still receives an incorrect no-tool
answer; that failure remains visible and was not used for another round of tuning.

## Earlier completed foundation

The original v0.7 app has three explicitly labeled modes, local CPU Qwen3,
strict schemas, reviewed tool calls, a restricted Decimal calculator, mock policy,
CLI, evaluation reports, and original-response traces. Its full clean-install,
minimal-install, wheel and 11-browser-check evidence is preserved in
[the v0.7 record](assets/release-checks-v0.7.json). Historical media remains labeled
as v0.7 or archived v0.3/v0.4. Those old records are not relabeled as new patch runs.

## Outside this portfolio scope

Initial model decisions can still be wrong; same-model tool review can also make
mistakes. Independent human evaluation, broad representative/adversarial data,
and operational monitoring would be needed for stronger reliability claims.

No adapter was trained. The larger synthetic research dataset remains unreviewed;
LoRA/QLoRA runners are future experiment support. Real authentication, customer
integrations, payments and production deployment are outside the simulation.
These limitations do not imply that those production features must be added to
complete the agreed portfolio project.
