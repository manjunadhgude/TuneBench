# Portfolio completion and evidence

The v0.7 software is implemented and verified for a fictional interview demo.
Model quality, user understanding, and production readiness are separate matters.

## Completed verification

- [x] Three explicitly labeled modes: rules demo, live CPU Qwen, and saved replay.
- [x] Schema-validated decisions, same-model review, restricted Decimal calculator, bounded retry, and preserved original outputs.
- [x] Three nonmutating mock tools with fixed fictional order/policy gates.
- [x] Full check workflow: 553 tests, lint, formatting, CLI, data audit and training export.
- [x] Core-only validation: 543 passed, 5 optional skips.
- [x] Fresh locked app installation: 549 passed, 4 optional skips; successful health response.
- [x] Standalone wheel imports outside the checkout and runs mock tools without optional model packages.
- [x] Chromium/Playwright: 11 checks, including actual Qwen3 execution and visible review trace, replay, and mobile layout.
- [x] Completed frozen 40-case same-test comparison, preserved failures, and score/review computational audit.

See [release evidence](assets/release-checks-v0.7.json),
[browser checks](assets/browser-checks.json), [current model results](../artifacts/semantic-comparison-v7/README.md),
and [remaining model failures](../artifacts/semantic-comparison-v7/error-analysis.md).
The current screenshots/recording show this release; prior v0.3/v0.4 media and
experiment results remain archived with their original identity. Earlier release
records retain their checkpoint status, including work that was pending then.

## Before using it in an interview

- Run the app and explain a primary answer, model review, retry, and calculator check.
- Discuss one remaining failure and why schema-valid JSON can still be wrong.
- State that quick demo uses rules, replay is recorded, and live mode uses an LLM.
- Explain your own contribution and development assistance accurately.

## Remaining research and production work

Independent human evaluation and broader representative/adversarial data are still
needed for stronger quality claims. The same-model reviewer can repeat mistakes;
correct arithmetic does not prove correct fact selection. CPU review adds latency
and memory. These are known limits of the current portfolio, not hidden completed
features.

No adapter was trained. The larger synthetic research dataset remains unreviewed;
LoRA/QLoRA runners are future experiment support. Real authentication, customer
integrations, payments, monitoring, and production deployment are outside this
simulation. Do not present it as a production refund agent.
