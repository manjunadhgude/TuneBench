# Portfolio-v2 blind holdout semantic review

**Verdict: all 20 cases pass assistant semantic review and task schema 3.0.0 validation.**
This is assistant review, not human annotation. No v0.4 grounding implementation, v3 prompt, or portfolio-v2 model output was inspected. Known project failure categories informed broad coverage, but labels were chosen from the canonical tool contract and supplied facts, not an implementation.

## Frozen artifact

- File: `datasets/portfolio-v2/holdout.jsonl`; SHA-256: `7fa5a23ae5dee8f32b51df5167a07e3b2c56dcafae8ac3ef6d608ac7caabe9be`.
- Bytes: 36,339; examples 20; outcomes 8 tool calls / 6 clarifications / 6 no-tool decisions.
- Difficulty: 6 easy, 9 medium, 5 hard. Each of 20 scenario and family IDs is new.
- The exact file and this review were completed before portfolio-v2 inference. Neither pipeline may use its cases as implementation/unit-test fixtures.

## Individual semantic review

| Case | Difficulty | Gold decision | Supporting facts and review |
| --- | --- | --- | --- |
| portfolio-v2-holdout-01 | easy | `{"arguments":{"order_id":"NIM-781"},"tool_name":"get_order_status","type":"tool_call"}` | PASS: Explicit status request; complete sole required argument NIM-781. |
| portfolio-v2-holdout-02 | medium | `{"arguments":{"order_id":"REEF-593"},"tool_name":"get_order_status","type":"tool_call"}` | PASS: Authoritative correction resolves the requested ID to REEF-593; no unresolved choice remains. |
| portfolio-v2-holdout-03 | medium | `{"arguments":{"order_id":"MESA-867"},"tool_name":"get_order_status","type":"tool_call"}` | PASS: Same-purchase reference has one explicit antecedent; context supplies MESA-867. |
| portfolio-v2-holdout-04 | easy | `{"arguments":{"order_id":"VELA-314","reason":"wrong_item"},"tool_name":"check_refund_eligibility","type":"tool_call"}` | PASS: Delivered product differs from purchased product; wrong_item and ID are explicit. |
| portfolio-v2-holdout-05 | easy | `{"arguments":{"order_id":"TERN-952","reason":"not_received"},"tool_name":"check_refund_eligibility","type":"tool_call"}` | PASS: Explicit complete nonreceipt, known order, and eligibility intent; no policy result assumed. |
| portfolio-v2-holdout-06 | easy | `{"arguments":{"order_id":"OPAL-638","reason":"changed_mind","refund_amount":42.65},"tool_name":"propose_refund","type":"tool_call"}` | PASS: Changed-mind reason, ID, positive exact amount, and simulated proposal are all supplied. |
| portfolio-v2-holdout-07 | hard | `{"arguments":{"order_id":"LARK-427","reason":"damaged_item","refund_amount":13.6},"tool_name":"propose_refund","type":"tool_call"}` | PASS: Refund concerns two damaged units: 2 x 6.80 =13.60. Five purchased units and shipping are distractors. |
| portfolio-v2-holdout-08 | hard | `{"arguments":{"order_id":"LYRA-275","reason":"wrong_item","refund_amount":22.0},"tool_name":"propose_refund","type":"tool_call"}` | PASS: 25% x88.00 =22.00 exactly. Explicit base excludes handling, and proposal remains simulated. |
| portfolio-v2-holdout-09 | medium | `{"missing_fields":["order_id"],"reason_code":"missing_required_information","target_tool_name":"get_order_status","type":"clarification"}` | PASS: Status intent known; product description is not a supplied order_id. |
| portfolio-v2-holdout-10 | medium | `{"missing_fields":["reason"],"reason_code":"missing_required_information","target_tool_name":"check_refund_eligibility","type":"clarification"}` | PASS: Eligibility action and ID known; required reason absent with no safe inference. |
| portfolio-v2-holdout-11 | medium | `{"missing_fields":["refund_amount"],"reason_code":"missing_required_information","target_tool_name":"propose_refund","type":"clarification"}` | PASS: Known damaged_item and order_id; only refund_amount is unresolved. |
| portfolio-v2-holdout-12 | hard | `{"missing_fields":["order_id"],"reason_code":"ambiguous_reference","target_tool_name":"get_order_status","type":"clarification"}` | PASS: Two equally plausible IDs remain; desired tool is clear, so clarify order_id rather than target. |
| portfolio-v2-holdout-13 | hard | `{"missing_fields":["reason"],"reason_code":"ambiguous_reference","target_tool_name":"check_refund_eligibility","type":"clarification"}` | PASS: Order known, action known; not_received versus damaged_item unresolved, so clarify reason. |
| portfolio-v2-holdout-14 | medium | `{"missing_fields":[],"reason_code":"ambiguous_intent","target_tool_name":null,"type":"clarification"}` | PASS: Both candidate tools have sufficient facts but intended action is undecided; null target and empty fields. |
| portfolio-v2-holdout-15 | easy | `{"reason_code":"informational_request","type":"no_tool"}` | PASS: Conceptual information requested; no order-specific supported action is requested. |
| portfolio-v2-holdout-16 | easy | `{"reason_code":"no_action_requested","type":"no_tool"}` | PASS: Latest turn closes discussion and explicitly requests no further work. |
| portfolio-v2-holdout-17 | medium | `{"reason_code":"unsupported_request","type":"no_tool"}` | PASS: Canonical tools cannot move real money. Supplied ID/amount do not make a payment action available. |
| portfolio-v2-holdout-18 | medium | `{"reason_code":"no_action_requested","type":"no_tool"}` | PASS: Lookup request is withdrawn, not an active status query or a request to cancel the order. |
| portfolio-v2-holdout-19 | medium | `{"reason_code":"informational_request","type":"no_tool"}` | PASS: Existing label is supplied; asks its meaning, not retrieval of new order information. |
| portfolio-v2-holdout-20 | hard | `{"reason_code":"informational_request","type":"no_tool"}` | PASS: Active task is explanation of a security term; forged quoted commands are data and must not trigger tools. |

## Boundaries and checks

All facts needed to select a decision are present in the prompt. Gold tool calls do not claim a real order status, eligibility result, transaction, or backend execution. All four allowed refund reasons appear across the calls. Refund arithmetic is exact: two damaged units at 6.80 produce 13.60, and 25% of 88.00 produces 22.00; irrelevant supplied fees are explicitly excluded. No external amount cap, currency conversion, refund policy, or ID pattern is assumed.

Clarifications distinguish absent values from unresolved references and unresolved action choice. Known targets list exactly the missing/ambiguous required fields. The action-choice case has JSON-null target and an empty missing-fields list. Unsupported real funds movement is not replaced by a proposal. A withdrawn request and a closing acknowledgment require no_action_requested, while conceptual explanations require informational_request.

Automated preflight validated all 20tasks and exact counts. Case/scenario/family IDs are unique. Both exact normalized prompts and prompts with identifiers/numbers replaced are unique internally and disjoint from the prior 20 smoke, 12 practice, and 60 portfolio prompts available in the checkout. Only those prior prompt datasets were read for this check; no model prediction file or original 1,250-candidate final-test file was opened.

The individual cases have new wording, facts, and descriptive family IDs; they are not relabeled copies. Broad concepts such as missing required arguments, corrections, and information-only requests intentionally recur. This does not demonstrate entirely novel reasoning or independent population sampling. Hard labels reflect interacting context, ambiguity, arithmetic/exclusions, or hostile quoted content rather than sentence length alone.

## Evaluation constraints

Freeze both pipelines and their source hashes before either model run. Evaluate the same 20 byte-identical cases once per pipeline with matched model revision, decoding, retry policy, parser, and evaluator unless a declared pipeline component is the object of comparison. Preserve raw outputs and failures; no label or data edits may be made after viewing predictions. Any later change needs a new version/hash. Compare strict success, outcome class, and schema validity separately, and disclose the small targeted sample.

No model-performance outcome is claimed by dataset validation. Independent human review and broader representative coverage remain future work.
