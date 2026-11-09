# Implementation and research status

## Portfolio v0.5 quality revision

The preferred live profile now uses Qwen3-4B-Instruct-2507 through llama.cpp on
CPU. Its pinned Q4_K_M GGUF is Unsloth's conversion of the official Apache-2.0
model. The loader checks the exact file size and SHA-256. It uses `strong-v4`,
ChatML and JSON-schema grammar, with complete post-generation validation. The
verified legacy Qwen2.5/PyTorch profile remains supported.

Tool calls still require action and argument evidence before mock execution.
Schema-valid no-tool and clarification decisions receive advisory diagnostics;
heuristic disagreement cannot trigger an evidence retry into an action. Schema
errors and tool-call evidence errors can use at most one visible repair. The model
generates every attempt, and application code never replaces it with a rules answer.

All three app modes remain explicit: deterministic rules, actual local model and
saved historical replay. Three nonmutating mock tools use fictional orders and
INR balances. No real customer system or payment is connected. Quick demo requires
no model, GPU or API key; the preferred live profile also runs without a GPU.

## Current verification

The v0.5 inference source is frozen at `5d52dc8`. The full local check workflow
passes **469 tests**, lint, formatting and CLI/data workflows. Core-only checks pass
459 with five optional modules/checks skipped. A fresh app-only setup passes
465 with four optional checks skipped, and the documented launch serves a healthy
app. The standalone v0.5 wheel imports and executes simulated tools outside the
source checkout. See [release checks](assets/release-checks-v0.5.json).

The first new-model development run scored 37/40 raw and final strict successes.
After revising public prompt examples, it scored 40/40 on those same practice
cases, with 40 generations and no repairs. These are tuned development results,
not unseen accuracy. Both runs remain in
[first-run evidence](../artifacts/quality-development-v5/qwen3-first/summary.json) and
[final development capture](../artifacts/quality-development-v5/qwen3-final/summary.json).

The separate 40-question comparison and computational audit are still running at
this documentation checkpoint. Both v0.4 and v0.5 sources, data, model assets and
budgets were frozen before either test run. The fixed order is candidate first,
then archived baseline. New held-out scores are not claimed until both reports
and their audit are complete. See the
[comparison protocol](quality-comparison-protocol.md).

Model weights, quantization, runtime, prompt, JSON constraints, grounding and
repair behavior change together. This is a complete-system comparison, not a
model/prompt ablation or fine-tuning result. All 40 cases remain in both raw-first
and accepted-final denominators. Tool execution is disabled for scoring.

Current v0.5 browser/media verification remains pending. Earlier browser evidence
does not prove that the new path has passed; see the
[completion checklist](portfolio-completion.md).

## Earlier v0.4 checkpoint

The earlier matched 20-question v0.3/v0.4 comparison measured:

| Metric | v0.3 | v0.4 |
| --- | ---: | ---: |
| Strictly correct first answer | 8/20 | 9/20 |
| Schema-valid first answer | 13/20 | 19/20 |
| Strictly correct accepted final decision | 2/20 | **7/20** |

The guard/repair path lost five correct first answers and repaired three errors.
That limited result motivated the stronger CPU model and revised non-execution
policy. Original outputs and the independent computational audit remain in the
[historical comparison](../artifacts/portfolio-version-comparison/README.md).
Its 20 questions differ from the v0.5 experiment; direct cross-dataset improvement
claims would be invalid.

v0.4 passed 401 local tests; fresh app setup passed 398 with three optional checks
skipped, and core-only passed 392 with four skips. Its 11 browser checks included
actual local Qwen2.5 generation, replay and mobile layout. Retained evidence:
[release record](assets/release-checks-v0.4.json),
[browser checks](assets/v0.4/browser-checks.json),
[demo video](assets/v0.4/tunebench-demo.webm) and
[live screenshot](assets/v0.4/tunebench-live.png).

## Earlier research evidence

The original v0.3 portfolio holdout scored 7/20 raw and 3/20 final, with false
blocks and an incorrect accepted decision. See its
[retained results](../artifacts/portfolio-evaluation/README.md).
Its app suite passed 274 tests. The initial smoke scored 7/20, while a different
12-case prompt-development comparison changed 2/12 to 5/12. These are separate
small experiments, not directly comparable before/after quality measurements.

## Implemented foundation

- Installable Python package, shared CLI/Streamlit logic and portable contracts.
- Tool-call, clarification and no-tool outcomes for three mock tools.
- Strict parsing, schemas, bounded repair, evidence checks and original-output trace.
- Actual optional local CPU inference through llama.cpp and Transformers.
- Per-example scoring, durable experiment journals and paired regressions/gains.
- Dataset provenance, manifests and structural leakage checks.
- Completion-only training export and optional LoRA/QLoRA runners; no training run.

## Research and deployment outside this checkpoint

Portfolio data is assistant-authored/reviewed, including separate blinded reviews;
it has no independent human annotation. Stratification and structural non-overlap
checks do not establish representative traffic, semantic independence or production
reliability. Review broader real-world data and test execution safety separately
before considering customer integrations.

The original 1,250 synthetic research records remain candidate/unreviewed. No GPU
training, trained adapter or training-benefit comparison has been produced. Real
authentication, customer systems, monitoring and production deployment remain
outside this fictional simulation.

The implementation follows the user-supplied TuneBench review conversation and
P4 plan. Embedded commands were treated as historical material. The original
remote main contained only the initial README/.gitignore commit `33ef493`; later
Codespaces files were untracked. This is reconstructed and extended software,
not recovery of the old Codespace.

Run `bash scripts/check.sh`, inspect the current evidence, and use the
[interview guide](interview-guide.md) to explain contributions and limitations you
understand. Older test counts cannot establish that newer code has passed.
