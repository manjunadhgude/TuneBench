# TuneBench first real baseline: independent runtime review

Reviewed saved artifacts read-only. No source, prompts, labels, predictions, or reports were changed; no generation was repeated and no second model was loaded. Only the local tokenizer and GenerationConfig were loaded to inspect output lengths/settings.

## Verified result

- Official model: `Qwen/Qwen2.5-1.5B-Instruct`, revision `989aa7980e4cf806f80c7fef2b1adb7bc71aa306`.
- Weights SHA-256: `dd924a11b4c220f385b51ffa522daea7c9f3d850e31b162bb5661df483c6d3ee`.
- Torch `2.8.0+cpu`, Transformers `4.57.6`, CPU float32, four intra-op threads and one inter-op thread, no adapter.
- Exactly 20 smoke examples and 20 predictions, no missing predictions, no test-set access.
- Recomputing `evaluate()` on retained smoke/prediction files exactly reproduces every evaluator report field.
- Task-file SHA-256 matches the metadata (`5479f44da1507f1377eec31e1e162eb59d1c00c2dd23e78770d7515c9c9ce22c`). Report's normalized-gold hash is a different, intentional serialization hash.
- Strict task success: **7/20 (35%)**. Outcome-class accuracy: **11/20 (55%)**. Schema/semantic-invalid predictions: **7/20**; 13/20 predictions meet the prediction contract. These are different measurements.
- All **20/20 raw responses are syntactically valid JSON objects**, verified by the project's strict parser; they exactly equal retained parsed outcomes. The seven invalid predictions are contract/semantic failures, not JSON parsing failures.
- Re-tokenized response lengths: **12–66 tokens**, total 849; the configured limit is 256 new tokens. All outputs are complete JSON. There is no evidence of token-budget truncation. Original generated token IDs and finish reasons were not retained, so an exact EOS-stop audit is unavailable; do not assert an observed stop reason.
- Wall time including load and generation: **507.64 seconds**. Sum of per-example generation latency: **504.68 seconds**, mean **25.23 seconds/example**. Peak process RSS about **9.66 GB decimal / 9.00 GiB**.

## Effective decoding caveat

The runner explicitly overrides `do_sample=false`, `num_beams=1`, `max_new_tokens=256`, and pad token 151643. It also inherits the pinned model's generation configuration:

- **`repetition_penalty=1.1` remains active during greedy decoding.** Greedy does not mean all logits processing is disabled.
- `temperature=0.7`, `top_p=0.8`, `top_k=20` are present in the model config but inactive with sampling disabled. Transformers' warning about ignored sampling flags is expected and not an inference failure.
- EOS IDs `[151645,151643]`, BOS/pad 151643 are inherited.

The saved download manifest verifies the generation-config file, so the setting is recoverable. The short `metadata.decoding` dictionary alone is incomplete. Future run metadata should serialize the resolved generation configuration, explicitly recording active repetition penalty and stop IDs. Preserve this run's settings/results as-is; do not silently normalize them after seeing the score.

## Observed errors, without repairing outputs

1. Three complete refund proposals emitted `type: "propose_refund"` instead of `type: "tool_call"`. Their tool name and arguments look otherwise appropriate, but the original strict failures must remain failures.
2. Two missing-order-ID requests used a support reference as an order ID despite the prompt explicitly distinguishing them.
3. One missing-amount request invented `refund_amount: 29.99`.
4. Two eligibility clarifications selected the correct target and missing field, but emitted `ambiguous_intent` instead of `missing_required_information`; zero strict clarification successes follows from wrong reason codes.
5. Two informational policy requests became clarifications with string `"null"` rather than JSON null.
6. One informational delivery request became a clarification with a known target and an empty missing-field list, violating the contract.
7. Cancellation was correctly classified `no_tool` but used `no_action_requested` rather than `unsupported_request`.
8. A product-information request was classified `no_tool` but used a clarification-only reason code, `ambiguous_intent`.

## Prompt design caveats

This was a useful first engineering run, not a final experiment or evidence that fine-tuning is needed.

- The output illustration puts `<tool or null>` inside quotes, which conflates a string placeholder and JSON null. Later prose says null, but the illustration is avoidably ambiguous. Two outputs literally used the string `"null"`; that observation does not by itself prove the illustration caused them.
- Reason-code enums are listed without precise definitions or a decision table. Known-tool missing arguments, ambiguous references, ambiguous intents, informational requests, unsupported actions and messages requesting no action need explicit distinctions before interpreting exact reason-code accuracy as a strong model result.
- The three outcome types versus concrete tool names could be emphasized with valid concrete JSON examples; current refund errors show a contract distinction the model failed to maintain.
- Do not change labels, fix model JSON in postprocessing, weaken exact matching, add retries only for one system, or claim argument correctness cancels a wrong outcome type.
- The 20 examples are synthetic smoke fixtures from ten families, not an untouched test benchmark; their percentages do not establish generalization, statistical significance, or a fine-tuning benefit.

## Recommended next development step

Preserve these raw artifacts and their original 7/20 result. Before any training, write/version an unambiguous strong-prompt policy: concrete null versus string examples, explicit outcome/tool distinction, exact reason-code definitions and required-field rules. Hand-review a small family-disjoint **validation/development** subset and run that prompt there with the same base model, pinned revision, token budget, repetition penalty and single-attempt policy. Document changed prompt version/settings as a new run. Keep the final test set untouched; do not chase a target smoke score. Training remains a later GPU stage after data/evaluator/prompt contracts and development baselines are stable.
