# Fresh paired prompt-development set v2

Verdict: **12/12 scenarios pass semantic review for a paired development experiment.**
The exact dataset was completed and its SHA-256 recorded before either old-strong
or strong-v2 inference on these scenarios. This review did not use strong-v2
instructions or model outputs. No labels, prompts, or source files were changed
in response to a generation.

Frozen practice artifact: `artifacts/prompt-development-v2/development.jsonl`

- SHA-256: `d6b7055c302cc74d414a560d9d622385dd3cb3b6902f8ed1890a80e90387bb2d`
- Bytes: 20,968; UTF-8 JSONL, sorted keys, compact JSON, one final newline per record.
- Task schema: 3.0.0, canonical three-tool definitions embedded in every task.
- Split: `validation`; 12 distinct `DV2_*` family IDs and 12 distinct scenario IDs.
- Outcomes: 4 tool calls, 4 clarifications, 4 no-tool decisions.
- Difficulty: 3 easy, 8 medium, 1 hard, assigned from actual reasoning.
- Provenance: manually authored and semantically reviewed practice cases.

These development families are outside the original 30-family dataset taxonomy.
They do not replace the 1,250-example candidate allocation. No final-test records
were generated, opened, copied, or used to build them. They are targeted practice
for known failure categories, not a representative or untouched scientific test.

## Semantic review before inference

| ID | Family suffix | Correct outcome | Review of the necessary facts and boundaries |
| --- | --- | --- | --- |
| dv2-01 | STATUS_SELECTION | `get_order_status(order_id="linen-684")` | Two IDs are supplied; curtains explicitly identify linen-684. The kettle order maple-271 must be ignored. A single reference-selection step makes this medium. |
| dv2-02 | WRONG_ITEM_ELIGIBILITY | `check_refund_eligibility(order_id="cedar-318", reason="wrong_item")` | Red bowl ordered, blue saucepan delivered; wrong-item reason and requested eligibility check are explicit. No eligibility result itself is assumed. Easy. |
| dv2-03 | NOT_RECEIVED_CONTEXT | `check_refund_eligibility(order_id="quartz-592", reason="not_received")` | Earlier message gives order and complete nonreceipt; current message asks for the corresponding eligibility check. All context is included. Medium. |
| dv2-04 | DERIVED_REFUND | `propose_refund(order_id="fern-463", reason="damaged_item", refund_amount=25.2)` | Three damaged units at 8.40 each yield exactly 25.20. Shipping 2.50 is explicitly excluded. Only a simulated proposal is requested. Arithmetic plus exclusion makes this hard. No currency conversion or unknown order total is required. |
| dv2-05 | MISSING_ORDER_ID | Clarify `get_order_status`, missing `["order_id"]`, reason `missing_required_information` | Operation is clear; the sole required argument is absent. Product description cannot identify an order through any available tool. Medium. |
| dv2-06 | MISSING_REFUND_REASON | Clarify `check_refund_eligibility`, missing `["reason"]`, reason `missing_required_information` | Order birch-746 is known; no refund reason is supplied. There is no basis to infer changed mind, damage, wrong item, or nonreceipt. Medium. |
| dv2-07 | MISSING_PROPOSAL_AMOUNT | Clarify `propose_refund`, missing `["refund_amount"]`, reason `missing_required_information` | Order moss-829 and wrong-item reason are known. Requested amount is unresolved; no amount or order total is present. Target/action is unambiguous. Medium. |
| dv2-08 | UNDECIDED_ACTION | Clarify with JSON-null target, `missing_fields=[]`, reason `ambiguous_intent` | User actively asks for help with order willow-357, but explicitly has not selected between two supported actions: status retrieval and damaged-item eligibility. The issue is the desired action, not a missing argument for an already chosen tool. This is not a closing acknowledgment or unsupported request. Medium. |
| dv2-09 | POLICY_TERMINOLOGY | `no_tool`, reason `informational_request` | A general definition of return-window terminology is requested, explicitly not an order inspection. No available tool is needed. Easy. |
| dv2-10 | KNOWN_DELIVERY_EXPLANATION | `no_tool`, reason `informational_request` | Existing status is already supplied; user asks only for its meaning and excludes retrieval. Distinguishing explanation from a new lookup is one boundary decision. Medium. |
| dv2-11 | ACTUAL_PAYMENT_UNSUPPORTED | `no_tool`, reason `unsupported_request` | User requests real money movement and says a simulated proposal is insufficient. Order brook-915 and amount 46.70 do not make a real-refund operation available. `no_action_requested` would be wrong because an action is explicitly requested. Medium. |
| dv2-12 | CLOSING_ACKNOWLEDGMENT | `no_tool`, reason `no_action_requested` | Included conversation already answers the earlier question. The current turn only thanks the assistant and explicitly declines further information/action. It is not a new informational request. Easy. |

Gold clarification outcomes omit a free-form `question` because that field belongs
to prediction records, not the task's gold-outcome schema. Their intended question
is determined by the missing field or undecided action; no exact wording is scored.

## Structural and duplicate checks

All 12 tasks passed the current `validate_task` schema and tool-semantic checks.
`audit_dataset({"validation": records})` passed its structural gates and reported
12 distinct scenarios and zero repeated normalized-template groups. The audit's
built-in `candidate_unreviewed` status and full-dataset difficulty target are
fixed generic annotations; this document separately records the manual review,
and the full 125-example allocation is not applicable to this practice subset.

There are no repeated example IDs, family IDs, scenario IDs, or exact normalized
prompts, either internally or against the original 20 smoke examples. The two
eligibility calls exercise different reasons and context structures; the two
informational no-tool cases distinguish terminology from explaining already-known
data. The three missing-field clarifications intentionally cover different tools
and arguments. They share a task pattern with prior smoke cases, as expected for
development, but use fresh wording and facts. Structural checks do not establish
semantic independence from the entire task domain.

## Frozen paired comparison rules

Use the identical bytes and all 12 IDs for old strong and strong-v2. Keep the same
verified Qwen revision, tokenizer/chat-template behavior, device/dtype, greedy
decoding, token limit, seed, validation, retry policy, parser, and evaluator. Preserve
raw generations and metadata for both runs. The primary comparison is strict task
success; report outcome classification and schema validity separately. Compare
per-example outcomes rather than treating the two runs as independent samples.

The original 7/20 first-baseline score remains a separate historical result. A
score on these 12 new cases is not directly comparable to 7/20 as a before/after
estimate, and any apparent paired gain is a small development signal rather than
proof of generalization. Do not change this file or its labels after either run;
record future revisions as a new version and hash.
