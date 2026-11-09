# Portfolio completion and evidence

TuneBench demonstrates a request-to-result simulation and measures local-model
decisions. Software checks, model quality and production readiness are separate
claims. No trained adapter or real payment system is presented as completed work.

## Current v0.5 verification

- [x] Preferred CPU Qwen3-4B-Instruct-2507 Q4_K_M backend, pinned size/SHA verification,
  explicit model identity, optional dependency and no implicit downloads.
- [x] `strong-v4`, JSON grammar and complete schema validation preserve original outputs.
- [x] Actual tool calls require evidence; schema-valid no-tool/clarification language
  diagnostics are advisory and cannot trigger an evidence retry into action.
- [x] At most one visible schema/tool-call evidence repair; application code does not
  rewrite the model answer into a rules decision.
- [x] Actual development capture: 37/40 before prompt revision and 40/40 afterward
  on the same practice cases. This is tuned development coverage, not unseen quality.
- [x] Both system sources, models and the separate 40-case data frozen before test
  generation; [protocol](quality-comparison-protocol.md) records the method.
- [x] Full v0.5 workflow passes 469 tests, lint, formatting and CLI/data checks.
- [x] Fresh hash-locked app setup passes 465 tests with four optional checks skipped;
  its documented launch serves the app. Core-only checks pass 459 with five skips.
- [x] Standalone v0.5 wheel imports and executes simulated tools outside the checkout.
  See [release checks](assets/release-checks-v0.5.json).
- [ ] Complete both 40-case test runs and independent computational score audit,
  retaining original first answers, accepted finals, failures, regressions and cost.
- [ ] Recheck current browser flows, including real Qwen3 generation and mobile layout,
  and retain current screenshots/recording.

The preferred model is Unsloth's third-party quantization of official Qwen weights.
Using it is model selection and runtime integration, not fine-tuning performed by
this project. The new comparison changes model, quantization, runtime, prompt and
guard together, so it cannot attribute a gain to one component.

## Earlier checkpoints remain visible

The v0.3/v0.4 matched 20-question comparison measured raw strict success 8/20 →
9/20, schema validity 13/20 → 19/20 and accepted final success 2/20 → **7/20**.
v0.4 lost five correct first answers and repaired three errors. These results
motivated the revised model and guard and remain in the
[historical report and audit](../artifacts/portfolio-version-comparison/README.md).
They cannot be directly compared with results from the new 40 questions.

v0.4 passed 401 local tests, fresh app 398 with three optional skips, and core-only
392 with four skips. Its browser checks covered the rules lookup, clarification,
proposal, unsupported payment, unknown order, blank input, replay, evaluation,
project page, mobile layout and real Qwen2.5 request. Historical evidence:
[release record](assets/release-checks-v0.4.json),
[browser checks](assets/v0.4/browser-checks.json),
[video](assets/v0.4/tunebench-demo.webm) and
[live screenshot](assets/v0.4/tunebench-live.png).

The original v0.3 checkpoint passed 274 full tests, with 268 and the optional UI
module skipped in core-only setup. Its 20-case portfolio evaluation scored 7/20
raw and 3/20 accepted final. See
[results](../artifacts/portfolio-evaluation/README.md),
[browser checks](assets/v0.3/browser-checks.json) and
[recording](assets/v0.3/tunebench-demo.webm).
Earlier smoke and prompt-development experiments remain separate measurements.

## What this portfolio demonstrates

| Capability | Inspectable evidence |
| --- | --- |
| Python application design | Shared package behind CLI and Streamlit |
| Local model integration | Verified quantized CPU backend and recorded runtime settings |
| Tool use and failure handling | Typed decisions, clarification, bounded repair and guarded mock dispatch |
| Evaluation discipline | Raw/final scores, invalid outputs, paired gains/regressions and audit |
| Reproducibility | Frozen source/model/data hashes, original captures and durable journals |
| Engineering explanation | Architecture, walkthrough, limitations and interview guide |

A reliable rules example proves that application path for that example, not LLM
accuracy. Replay proves an output was retained, not that fresh inference occurred.
A schema-valid decision can still be semantically wrong.

## Separate research and deployment work

- Portfolio cases are fictional, stratified and assistant-authored/reviewed; separate
  blinded assistant review is not independent human annotation or production sampling.
- Small test sets cannot establish generalization or guarantee execution safety.
- The 1,250-candidate research benchmark is not fully reviewed/frozen.
- No model fine-tuning or adapter-quality comparison has been performed.
- Mock tools never access customer systems, mutate an order or transfer money.
- Real authorization, integrations, operational monitoring and production deployment
  remain outside this portfolio simulation.

Use the [demo script](demo-script.md), [interview guide](interview-guide.md) and
[resume wording](resume-bullets.md) for behavior and contributions you can explain.
