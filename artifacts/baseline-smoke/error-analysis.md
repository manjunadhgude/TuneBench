# First Qwen baseline: independent failure audit

**Verdict:** the observed 7/20 strict task successes (35%) and 11/20 outcome classifications (55%) agree with the saved raw generations and reviewed gold labels. I found no evaluator bug explaining the failures. These are output-contract and instruction-following failures, with a prompt-format caveat described below.

Read-only audit of `artifacts/baseline-smoke/strong/{smoke.jsonl,strong.predictions.jsonl,report.json}` and the current inference prompt/evaluator source. No model or evaluation reruns; no source, prompt, or label changes. The artifact's 20 gold records match the reviewed seed-42 smoke set (JSONL SHA-256 `5479f44da1507f1377eec31e1e162eb59d1c00c2dd23e78770d7515c9c9ce22c`).

## Counts and interpretation

- All 20 raw outputs parse as JSON objects, and every parsed object equals its stored `outcome`: **zero JSON-syntax/parse failures**.
- There are 20 predictions for 20 matching IDs; no missing records.
- **Seven schema-invalid predictions**: three invalid outcome tags, two string-null targets, one known clarification target with empty missing fields, and one invalid no-tool reason enum.
- **Nine wrong outcome classifications**, including the three unrecognized outcome tags. Seven schema-invalid records overlap with the failure groups below; do not add error counters as disjoint totals.
- **Thirteen strict failures**: nine wrong classifications plus four records whose class is correct but required details/reason codes fail.
- The seven strict successes are four status lookups and three eligibility checks; their tool names and supplied arguments are correct.

## All thirteen failed examples

| Example(s) | Saved prediction problem | Error type | Why the gold/report are justified |
| --- | --- | --- | --- |
| SM_REFUND_EXPLICIT-0000 / -0001 / -0002 | Uses `type="propose_refund"` instead of `type="tool_call"`. The `tool_name`, order IDs, damaged-item reasons, and amounts (112.78 / 55.26 / 35.74) are otherwise exact. | JSON valid; schema invalid; unrecognized class. No fabricated arguments in these three. | The contract uses the outcome tag `tool_call`; tool identity belongs in `tool_name`. A schema-compliant downstream consumer cannot accept the invented outcome tag. Rejecting these is correct. |
| SM_STATUS_MISSING_ID-0000 / -0001 | Calls `get_order_status` with `order_id="support reference Y528225"` / `"support reference F658944"`. | Schema valid, wrong outcome; unsupported argument provenance. | Prompts explicitly say these support references are not order IDs. The correct action is clarification for `order_id`. This is misuse of a supplied reference, rather than inventing a completely new token. A nonempty-string tool schema cannot establish whether it came from the right source. |
| SM_ELIGIBILITY_MISSING_REASON-0000 / -0001 | Correct clarification target, correct `missing_fields=["reason"]`, and useful question, but `reason_code="ambiguous_intent"`. | Schema valid; correct class/target/fields; wrong reason code. | The requested operation is explicit and only a required argument is absent, so gold `missing_required_information` is appropriate. Strict task success intentionally includes the reason code; field-level credit is retained separately. |
| SM_REFUND_MISSING_AMOUNT-0000 | Calls `propose_refund` with an invented `refund_amount=29.99`. | Schema valid, wrong outcome; hallucinated required value. | No amount is supplied, and the prompt explicitly disallows inferring it. Order ID and reason are known; only `refund_amount` should be requested through clarification. |
| SM_POLICY_EXPLANATION-0000 / -0001 | Returns clarification with `target_tool_name="null"` (a string), empty missing fields, and `ambiguous_intent`; questions repeat the user's general-policy request. | JSON valid; schema invalid; wrong class; string-null contract error. | User asks for general information and explicitly excludes an order check; gold is `no_tool/informational_request`. Even changing the string to JSON null would leave the wrong class. |
| SM_DELIVERY_ETA-0000 | Returns clarification targeting `get_order_status` with `missing_fields=[]`, asking for order-specific delivery details. | JSON valid; schema invalid; wrong class. | A known clarification target requires at least one missing field. More fundamentally, the user requests general delivery ranges and excludes order lookup; gold `no_tool/informational_request` is supported. |
| SM_UNSUPPORTED_CANCEL-0000 | Correct `type="no_tool"`, but `reason_code="no_action_requested"`. | Schema valid; correct class, wrong reason code. | An action is requested—cancellation—but no listed tool supports it. Gold `unsupported_request` is correct. |
| SM_PRODUCT_QUESTION-0000 | Correct `type="no_tool"`, but `reason_code="ambiguous_intent"`. | JSON valid; schema invalid; correct class, wrong reason enum/code. | `ambiguous_intent` is a clarification reason, not a no-tool reason. The request is a clear general product question; `informational_request` is correct. |

## Evaluator check and prompt caveat

The report deliberately separates outcome classification from prediction validity and strict success. For example, the invalid product-question record still gets outcome-class credit because `type="no_tool"` is recognizable; it fails strict success because its reason is invalid. The refund records use an unrecognized type, so their class is `invalid`. This explains the reported metrics consistently.

The conditional argument metric of 100% (7/7) is not an overall argument-reliability result: it only covers gold tool-call examples that selected a recognizable correct tool. It excludes all three invalid-tag refund outputs and does not assess the hallucinated amount in a gold clarification case. The 35% strict score is the useful complete-task figure for this run.

A prompt-format caveat merits recording before interpreting these as pure model reasoning failures: `OUTPUT_CONTRACT` depicts a clarification target as `"target_tool_name":"<tool or null>"`, a quoted placeholder, while prose later says to use a null target for ambiguous intent. The placeholder can encourage literal string `"null"`; two predictions show exactly that. This does not make their gold labels or schema rejection wrong, and those same examples also choose the wrong outcome. Cause is not established without a controlled later experiment.

Similarly, the prompt lists valid reason-code enums but does not give complete explicit definitions/examples for their distinctions. The two otherwise useful missing-reason clarifications fail on that code mapping. Treat the strict score as performance under this exact saved prompt, not as a general upper bound for Qwen or proof that fine-tuning is needed. No prompt changes or reruns were made in this audit.

These are deliberately easy, templated smoke cases; they cannot establish full-benchmark generalization. The immediate evidence is that real inference, parsing, validation, scoring, and raw-output preservation worked, while this first prompt/model combination did not yet reliably follow the output/abstention contract.
