# Portfolio completion and evidence

This page separates a demonstrable software project from the larger research
question. TuneBench can show a complete request-to-result simulation without
claiming that a fine-tuned model exists or that the model is ready for real users.

## Existing measured foundation

- [x] Installable Python package, CLI, packaged contracts and automated CPU checks.
- [x] Three-outcome evaluation: tool call, clarification and no tool.
- [x] Per-example scoring, invalid/missing-output diagnostics and paired comparisons.
- [x] Synthetic dataset generation and structural leakage checks; generated candidates
  remain unreviewed and unfrozen.
- [x] Actual Qwen2.5-1.5B-Instruct inference on CPU with pinned model assets and raw outputs.
- [x] Initial 20-case smoke experiment: 7/20 strict successes, with errors retained.
- [x] Separate paired 12-case prompt experiment: 2/12 versus 5/12 strict successes,
  four improvements and one regression, with uncertainty documented.
- [x] Training-data preparation and completion-only loss masking; optional training
  code is implemented, while a GPU training run is not part of the evidence.

Evidence: [baseline smoke experiment](../artifacts/baseline-smoke/README.md),
[paired prompt experiment](../artifacts/prompt-development-v2/README.md),
[model workflow](model-workflow.md), and [implementation status](status.md).
The older `artifacts/validation.json` is a historical check result; it does not
supersede later model runs or establish that newer UI changes have been checked.

## Historical v0.3 demonstration checks

The checked items below were exercised against v0.3. They remain useful historical
evidence, but do not establish that revised v0.4 browser flows have passed. A checked
source feature alone is not evidence that its browser flow was exercised.

- [x] **Quick demo** is labeled as deterministic Python and runs without a model download.
- [x] A supported status request produces a visible validated mock-tool result.
- [x] Missing order information produces clarification without tool execution.
- [x] A refund proposal shows a simulated, nonmutating result and the mock policy.
- [x] An actual-payment request produces no tool execution.
- [x] Invalid or ungrounded model output is visibly blocked; raw output and any
  permitted repair attempt remain distinguishable from the final result.
- [x] **Saved model replay** is labeled as recorded and does not imply fresh inference.
- [x] **Live local Qwen** uses the actual local Qwen model and reports actual timing;
  absence of a model produces a clear setup message rather than a fabricated response.
- [x] Streamlit browser behavior and the v0.3 automated check suite were verified.
- [x] A screenshot or short demo recording is saved, with backend identity visible.
- [x] The README's setup/launch commands have been exercised from their documented directories.

Verified v0.3 evidence: [browser checks](assets/v0.3/browser-checks.json),
[demo video](assets/v0.3/tunebench-demo.webm), [live Qwen screenshot](assets/v0.3/tunebench-live.png),
and [frozen holdout results](../artifacts/portfolio-evaluation/README.md).
The v0.3 full app suite passed 274 tests; its core-only environment passed 268 with
the optional UI module skipped. Setup, launch and standalone-wheel CLI were
exercised. These checks establish the earlier working prototype; they are not
current v0.4 check results.

## v0.4 changes and final verification

The revised source adds `strong-v3`, optional `lm-format-enforcer` JSON constraints,
request-evidence checks for corrections/context and exact derived amounts, and at
most one visible schema or evidence repair. Complete validation remains necessary:
constraints do not enforce every schema restriction or prove decision correctness.
Both attempts remain intact; application code never rewrites the model answer.
Quick demo is still deterministic Python, not model inference.

Final verification:

- [x] Complete the fresh matched v0.3/v0.4 20-case system comparison: raw strict
  success 8/20 → 9/20, first-answer schema validity 13/20 → 19/20, accepted final
  success 2/20 → 7/20. Every case, raw attempt, regression and generation cost is
  retained in the [report](../artifacts/portfolio-version-comparison/README.md) and
  [independent computational audit](../artifacts/portfolio-version-comparison/independent-audit.json).
- [x] Full v0.4 checks pass: 401 tests, lint, formatting and CLI/data workflows.
- [x] All 11 current browser checks pass, including an actual local Qwen request,
  a 390px mobile layout and no browser errors. Retained
  [checks](assets/browser-checks.json), [live screenshot](assets/tunebench-live.png)
  and [demo recording](assets/tunebench-demo.webm) show the current version.
- [x] Fresh hash-locked app setup passes 398 tests with three optional model checks
  skipped, and the documented launch command serves the app. Core-only checks pass
  392 with four skips. The standalone v0.4 wheel executes a simulated refund outside
  the source checkout. See [release checks](assets/release-checks-v0.4.json).

Both holdouts remain unchanged and have now been observed. Further tuning needs
development data and a new final test set. The matched comparison changes several
pipeline components together, so it cannot isolate a prompt change or demonstrate
a training benefit. v0.4 still drops from 9 correct first answers to 7 accepted
finals. Its 36 generations include 16 repairs, compared with 27 generations and
seven repairs for v0.3. The small assistant-authored/reviewed set has no independent
human annotation and does not establish production accuracy or execution safety.
Current browser and package evidence is summarized in the
[release checks](assets/release-checks-v0.4.json).

## What this portfolio demonstrates

| Capability | What a reviewer can inspect |
| --- | --- |
| Python application design | A small package shared by a CLI and Streamlit interface |
| Structured tool use | Parse, schema checks, grounding, dispatch and visible tool result |
| Failure handling | Clarifications, unsupported actions, invalid outputs and blocked execution |
| Evaluation discipline | Raw predictions, matched comparisons, errors and regressions |
| Reproducibility | Prompt versions, model/data hashes, pinned assets and test commands |
| Engineering communication | Architecture, limitations, walkthrough and evidence links |

A reliable rules demonstration proves the application path for those examples.
It does not prove the LLM makes equally reliable choices. A replay proves that an
output was retained; it does not measure current latency or generate a new answer.

## Research and deployment work that remains separate

- No fine-tuning or adapter-quality comparison has been performed.
- The original 1,250-candidate research benchmark is not fully reviewed or frozen. The smaller portfolio holdout is frozen with assistant review; independent human review remains outstanding.
- Small synthetic development sets cannot establish generalization or production accuracy.
- The model still has documented decision, formatting, reference and reason-code failures.
- Mock orders and INR amounts are fictional. The tools never access customer systems,
  mutate orders, send money or process a real refund.
- Authentication, user authorization, real integrations, operational monitoring and
  a production deployment are outside the present portfolio scope.

Use the [demo script](demo-script.md) to present the working application and the
[interview guide](interview-guide.md) to prepare your explanation. Use
[resume wording](resume-bullets.md) only for contributions you can substantiate.
