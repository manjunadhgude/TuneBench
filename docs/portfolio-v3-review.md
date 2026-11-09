# Portfolio-v3 semantic review

This ledger concerns 40 fictional decision tasks authored before the final model run.
The author did not inspect the revised implementation, prompts or model outputs.
Both author review and a separate blind assistant pass accept all 40 gold outcomes.
No material semantic correction was required. This is assistant review, not human annotation.
The [per-example second-pass findings](../datasets/portfolio-v3/secondary-review.json)
record the scope and limitations of that review.

The predefined composition is 16 tool calls, 12 clarifications and 12 no-tool decisions,
with nine easy, 20 medium and 11 hard descriptive difficulty labels.

All required facts must come from each prompt. Gold specifies a canonical decision,
not an order status, refund-eligibility answer, policy judgment or real transaction.
Clarification-question prose is omitted from gold and is not human graded.

| Example | Difficulty | Gold | Supporting evidence |
| --- | --- | --- | --- |
| portfolio-v3-holdout-01 | medium | `{"type":"tool_call","tool_name":"check_refund_eligibility","arguments":{"order_id":"OR-2950","reason":"wrong_item"}}` | The delivered item differs from the ordered product; the order identifier and eligibility request are explicit. |
| portfolio-v3-holdout-02 | medium | `{"type":"clarification","target_tool_name":"propose_refund","missing_fields":["reason"],"reason_code":"missing_required_information"}` | An order and positive amount are supplied, but the customer has intentionally not supplied a refund reason. |
| portfolio-v3-holdout-03 | hard | `{"type":"no_tool","reason_code":"no_action_requested"}` | The latest customer turn retracts the earlier lookup; this is neither an active lookup nor a request to cancel the purchase. |
| portfolio-v3-holdout-04 | hard | `{"type":"clarification","target_tool_name":null,"missing_fields":[],"reason_code":"ambiguous_intent"}` | The customer has not selected an action between two supported services; null target and no guessed missing fields are appropriate. |
| portfolio-v3-holdout-05 | medium | `{"type":"clarification","target_tool_name":"check_refund_eligibility","missing_fields":["reason"],"reason_code":"ambiguous_reference"}` | The requested eligibility check and order are known, while damaged_item versus changed_mind is explicitly unresolved. |
| portfolio-v3-holdout-06 | hard | `{"type":"tool_call","tool_name":"propose_refund","arguments":{"order_id":"SM-412","refund_amount":47.2,"reason":"changed_mind"}}` | The customer explicitly supersedes both the old reference and old amount; the current changed-mind proposal is fully specified. |
| portfolio-v3-holdout-07 | medium | `{"type":"no_tool","reason_code":"unsupported_request"}` | The requested address mutation is unsupported; a status lookup is explicitly excluded and no real address data is needed. |
| portfolio-v3-holdout-08 | medium | `{"type":"no_tool","reason_code":"unsupported_request"}` | The user requires a real transfer, which propose_refund cannot perform; do not substitute a proposal despite complete-looking arguments. |
| portfolio-v3-holdout-09 | medium | `{"type":"clarification","target_tool_name":"propose_refund","missing_fields":["refund_amount"],"reason_code":"missing_required_information"}` | The proposal action, damaged-item reason and ID are known, but no positive requested amount or computable basis is supplied. |
| portfolio-v3-holdout-10 | easy | `{"type":"no_tool","reason_code":"no_action_requested"}` | This is a closing acknowledgment without a question or requested operation. |
| portfolio-v3-holdout-11 | hard | `{"type":"no_tool","reason_code":"no_action_requested"}` | The apparent instruction is explicitly quoted historical untrusted data; the actual current statement authorizes no tool action. |
| portfolio-v3-holdout-12 | medium | `{"type":"tool_call","tool_name":"check_refund_eligibility","arguments":{"order_id":"NX-7506","reason":"not_received"}}` | An explicit nonreceipt fact supports not_received; no actual delivery status or policy outcome must be invented. |
| portfolio-v3-holdout-13 | easy | `{"type":"tool_call","tool_name":"check_refund_eligibility","arguments":{"order_id":"JAR-6904","reason":"damaged_item"}}` | Broken lid supports damaged_item; the requested action is eligibility checking rather than proposing or paying a refund. |
| portfolio-v3-holdout-14 | hard | `{"type":"no_tool","reason_code":"unsupported_request"}` | Account-wide export is unavailable; the incidental reference does not change the requested unsupported action. |
| portfolio-v3-holdout-15 | hard | `{"type":"tool_call","tool_name":"check_refund_eligibility","arguments":{"order_id":"BL-6308","reason":"changed_mind"}}` | The customer retracts the suspected defect and positively supplies changed_mind as the current refund reason. |
| portfolio-v3-holdout-16 | medium | `{"type":"clarification","target_tool_name":"check_refund_eligibility","missing_fields":["order_id"],"reason_code":"missing_required_information"}` | Nonreceipt and eligibility intent are explicit; the order reference is the sole missing argument. |
| portfolio-v3-holdout-17 | easy | `{"type":"no_tool","reason_code":"informational_request"}` | This requests a general definition rather than an order-specific operation. |
| portfolio-v3-holdout-18 | medium | `{"type":"tool_call","tool_name":"propose_refund","arguments":{"order_id":"DM-5529","refund_amount":16.75,"reason":"changed_mind"}}` | A supported proposal is positively authorized while payment is separately prohibited; changed_mind and amount are explicit. |
| portfolio-v3-holdout-19 | easy | `{"type":"clarification","target_tool_name":"get_order_status","missing_fields":["order_id"],"reason_code":"missing_required_information"}` | Tracking is clear but its required order_id is absent; no reference should be guessed. |
| portfolio-v3-holdout-20 | hard | `{"type":"no_tool","reason_code":"informational_request"}` | An explicit explanatory question about hypothetical arithmetic is informational; there is no authorized order-specific tool action. |
| portfolio-v3-holdout-21 | medium | `{"type":"no_tool","reason_code":"informational_request"}` | This asks about two concepts and does not request either action. |
| portfolio-v3-holdout-22 | medium | `{"type":"no_tool","reason_code":"informational_request"}` | The requested deliverable is an explanation of a supplied status word; mentioning an order ID does not authorize retrieval. |
| portfolio-v3-holdout-23 | hard | `{"type":"tool_call","tool_name":"propose_refund","arguments":{"order_id":"PK-3864","refund_amount":60,"reason":"not_received"}}` | The explicit earlier item-price base is 240.00; 25 percent is 60.00 and nonreceipt supplies the reason. |
| portfolio-v3-holdout-24 | easy | `{"type":"clarification","target_tool_name":"check_refund_eligibility","missing_fields":["reason"],"reason_code":"missing_required_information"}` | The eligibility target and order are known; the required refund reason alone is absent. |
| portfolio-v3-holdout-25 | medium | `{"type":"clarification","target_tool_name":"propose_refund","missing_fields":["reason","refund_amount"],"reason_code":"missing_required_information"}` | The proposal target and ID are known, while exactly reason and refund_amount remain unresolved. |
| portfolio-v3-holdout-26 | easy | `{"type":"no_tool","reason_code":"unsupported_request"}` | Cancellation is an immediate requested action absent from all three available tools. |
| portfolio-v3-holdout-27 | easy | `{"type":"tool_call","tool_name":"get_order_status","arguments":{"order_id":"REC-801"}}` | A current status lookup is requested and the only required order reference is explicit. |
| portfolio-v3-holdout-28 | hard | `{"type":"tool_call","tool_name":"get_order_status","arguments":{"order_id":"FC/2751"}}` | The current request refers back to one unambiguous purchase reference supplied in the conversation; no field is missing. |
| portfolio-v3-holdout-29 | medium | `{"type":"no_tool","reason_code":"no_action_requested"}` | The customer supplies a background fact and explicitly requests no new action or explanation. |
| portfolio-v3-holdout-30 | medium | `{"type":"tool_call","tool_name":"propose_refund","arguments":{"order_id":"FL-8642","refund_amount":43.8,"reason":"wrong_item"}}` | All three wrong items are covered and the supplied unit price gives three times 14.60 equals 43.80; fees are explicitly excluded. |
| portfolio-v3-holdout-31 | hard | `{"type":"clarification","target_tool_name":"propose_refund","missing_fields":["refund_amount"],"reason_code":"ambiguous_reference"}` | The order, proposal action and damaged reason are settled; two unconfirmed amount candidates require ambiguity clarification. |
| portfolio-v3-holdout-32 | medium | `{"type":"tool_call","tool_name":"get_order_status","arguments":{"order_id":"web/876A"}}` | The support-case identifier is explicitly a different role; the receipt reference is the requested order identifier. |
| portfolio-v3-holdout-33 | medium | `{"type":"tool_call","tool_name":"get_order_status","arguments":{"order_id":"CL-4812"}}` | The customer authoritatively replaces the old order reference with CL-4812 and requests tracking. |
| portfolio-v3-holdout-34 | easy | `{"type":"tool_call","tool_name":"propose_refund","arguments":{"order_id":"BK-9416","refund_amount":28.4,"reason":"damaged_item"}}` | The proposal action, order reference, positive exact amount and torn-binding damage are all supplied. |
| portfolio-v3-holdout-35 | medium | `{"type":"clarification","target_tool_name":"propose_refund","missing_fields":["order_id"],"reason_code":"missing_required_information"}` | The amount and wrong-item reason are explicit; only the required order identifier is missing. |
| portfolio-v3-holdout-36 | medium | `{"type":"clarification","target_tool_name":"get_order_status","missing_fields":["order_id"],"reason_code":"ambiguous_reference"}` | One status lookup is intended, but two authoritative candidate references remain unresolved; the action is not ambiguous. |
| portfolio-v3-holdout-37 | hard | `{"type":"tool_call","tool_name":"propose_refund","arguments":{"order_id":"CU-1837","refund_amount":19.5,"reason":"damaged_item"}}` | The authorized subset is two damaged cups, not all five; two times 9.75 equals 19.50 exactly. |
| portfolio-v3-holdout-38 | medium | `{"type":"clarification","target_tool_name":"check_refund_eligibility","missing_fields":["order_id","reason"],"reason_code":"missing_required_information"}` | Both required eligibility fields are absent; a proposal amount is irrelevant to this tool. |
| portfolio-v3-holdout-39 | easy | `{"type":"tool_call","tool_name":"propose_refund","arguments":{"order_id":"AP-2703","refund_amount":44.9,"reason":"wrong_item"}}` | An explicit proposal amount and wrong-item fact are available; this does not request a real payment. |
| portfolio-v3-holdout-40 | medium | `{"type":"tool_call","tool_name":"propose_refund","arguments":{"order_id":"NP-8426","refund_amount":72,"reason":"not_received"}}` | The requested proposal amount is 72 rather than the background total; the nonreceipt reason is explicit. |

## Frozen file

`holdout.jsonl`: 72,611 bytes, 40 records.

SHA-256: `eb0dd97d0a15308415a9537e33020d387801b8b426d78192f6cf2a81fcd900a9`

## Limitations

The same assistant system authored and reviewed these targeted English-language cases.
A separate assistant pass can catch inconsistencies but does not supply independent human
annotation. Historical input examples were used for structural novelty checks; broad
reasoning concepts recur. Exact hashes and every original result must be retained after
inference. The set must remain unread by implementers until source freeze and must not
be used for test-driven changes afterward.

## Additional pre-inference review

A separate assistant reviewer started without inherited parent implementation or
prompt history and independently accepted all 40 gold outcomes against the
canonical contracts. It inspected no revised implementation or model outputs and
performed no inference. No scenario or gold label changed. The coordinator had
implementation context and performed structural/hash checks only; this is not a
claim of independent human annotation. See
[additional-blind-review.json](../datasets/portfolio-v3/additional-blind-review.json).
