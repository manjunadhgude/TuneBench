# Independent runtime review: paired strong versus strong-v2

Read-only review of `artifacts/prompt-development-v2/paired-run`. No source, labels, prompts, predictions or reports were changed. No generation was repeated; only the local tokenizer was loaded for token counts.

## Verified controls and scope

Both runs contain the same 12 ordered validation examples, one example in each of 12 families, with four tool-call, four clarification and four no-tool gold labels. The protocol was frozen before generation. The task-file SHA-256 is `d6b7055c302cc74d414a560d9d622385dd3cb3b6902f8ed1890a80e90387bb2d`; both runs reference protocol SHA-256 `0112e69f12ecf766b8429218a55993c05146ed5a0c03357fe7f9fc183d8ef79d`.

`assert_prompt_comparison_conditions()` passes on retained metadata. Manual verification additionally confirms seed 42 in both runs. Non-prompt settings match: official model/revision and all model/tokenizer asset hashes, adapter null, Torch 2.8.0+cpu, Transformers 4.57.6, CPU float32, four intra-op/one inter-op threads, same full resolved generation configuration and no retries. The active greedy configuration includes `repetition_penalty=1.1`, one beam, 256 new-token limit, and the same EOS/pad IDs. Sampling temperature/top-p/top-k are recorded but inactive. The declared prompt versions and hashes differ as intended; legacy style is recorded as strong-v1, revised style as strong-v2. No final test or fine-tuning is involved.

## Results preserved without reinterpretation

| Measurement | strong | strong-v2 |
| --- | ---: | ---: |
| Strict task successes | 2/12 | 5/12 |
| Correct outcome class | 4/12 | 6/12 |
| Syntactically valid JSON objects | 11/12 | 10/12 |
| Parse failures/plain-prose outputs | 1 | 2 |
| Schema/semantic-invalid among parsed JSON | 5 | 3 |
| Total invalid predictions | 6 | 5 |
| Fully valid prediction contract | 6/12 | 7/12 |
| Re-tokenized response length | 12–63 tokens | 13–73 tokens |
| Sum of response tokens | 474 | 470 |
| Sum of generation latency | 293.42 s | 348.30 s |
| Mean generation latency | 24.45 s | 29.02 s |
| Wall time including loading | 295.90 s | 349.37 s |

The candidate gains four strict successes (`dv2-04`, `dv2-06`, `dv2-07`, `dv2-12`) and loses one (`dv2-02`), for a net gain of three on these 12 examples (+25 percentage points). Seven examples are strict ties. The saved descriptive family bootstrap interval for the accuracy difference is approximately -8.3 to +58.3 percentage points; it includes zero and does not establish a reliable general advantage.

## Parsing and truncation audit

Old strong emits prose for `dv2-10`. Revised strong-v2 emits prose for both `dv2-09` and `dv2-10`; these are genuine JSON parse failures, not merely schema-invalid JSON. Therefore it would be inaccurate to say that the revised prompt uniformly improved formatting reliability: JSON syntax success actually decreases from 11 to 10 here, even though total contract-valid predictions increase from six to seven.

The local pinned tokenizer gives at most 63 response tokens for legacy strong and 73 for strong-v2, well below the common 256-token cap. Parsed outputs are complete JSON; prose outputs are complete sentences/paragraphs. There is no evidence that the observed failures result from token-budget truncation. The runner did not retain original generated token IDs or finish reasons, so an exact stop-reason claim cannot be made from these artifacts alone.

## Regression and remaining failures

The only strict regression, `dv2-02`, was previously a valid and correct `check_refund_eligibility` call. Revised strong-v2 instead emits `type: "check_refund_eligibility"` and omits `tool_name`, breaking the contract. Do not repair or score this as correct after generation.

The revised prompt fixes a refund-proposal outcome-type error, two missing-information clarification cases, and the closing-acknowledgment reason code. It still mishandles contextual order references, missing order IDs, ambiguous action choice, informational outputs, and a request for actual payment. Better instructions did not eliminate unsupported-action substitution or invented/empty arguments.

## Interpretation and limits

The supported conclusion is: **on one frozen 12-example development comparison, revised instructions increased strict successes from two to five, with one regression and additional plain-prose output.** This is an early prompt-development result, not final quality, significance, production readiness, or a fine-tuning benefit. The earlier 20-example smoke set has different examples and outcome proportions; do not compare its percentage directly with these scores.

Timing is descriptive. Legacy strong always ran first, revised strong-v2 second, the system prompts differ in length, and there were no counterbalanced/repeated timing runs. Do not claim a measured causal speed advantage/disadvantage from this single pair. `process_peak_rss_bytes_so_far` is cumulative within the process and cannot be interpreted as independently measured per-prompt peak memory.

Preserve both raw runs and the frozen protocol. A next step is a reviewed, broader development dataset and error taxonomy before training, without editing these labels or retroactively changing the score. Keep the final test set untouched and use an explicitly new version/run for any later prompt revision.
