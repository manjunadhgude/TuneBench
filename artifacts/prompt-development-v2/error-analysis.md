# Paired prompt-development v2: independent error review

**Verdict:** accept the saved result as an engineering development measurement.
I found no gold-label or data defect requiring a change, and no scoring defect
explaining the remaining failures. Strong-v2 improves strict success from 2/12
to 5/12 on this frozen practice set, with four improved cases and one regression.
This is a small, targeted development signal, not proof of generalization.

Read-only review of the two saved prediction/report files and the frozen gold
records under `artifacts/prompt-development-v2/paired-run`. No inference or
evaluation reruns; no source, prompt, or label changes. The paired-run gold file
and original practice file both retain SHA-256
`d6b7055c302cc74d414a560d9d622385dd3cb3b6902f8ed1890a80e90387bb2d`.

## Seven remaining strong-v2 failures

| Case | Observed output | Failure and gold review |
| --- | --- | --- |
| dv2-02 (the sole regression) | JSON object with `type="check_refund_eligibility"`, no `tool_name`; arguments correctly contain cedar-318 and wrong_item. | Schema/serialization failure: tool identity is put in the outcome-type field, and a required field is absent. The old prompt emitted the exact correct tool-call object. The red-bowl/blue-saucepan facts clearly support wrong-item eligibility, so the gold is sound. It is a contract regression, not an argument-understanding regression. |
| dv2-03 | Schema-valid clarification asking for `order_id`, reason `missing_required_information`. | Wrong action caused by missed included context. Order quartz-592 is explicitly stated in the earlier message; nonreceipt is explicit; the current message requests eligibility for that same problem. Both required arguments are available. Gold tool call is supported. |
| dv2-05 | `get_order_status` call with empty-string `order_id`. | Wrong outcome plus invalid required argument. The prompt explicitly says no order reference is supplied. Clarification is required; an empty value does not satisfy the tool schema. This failure persists unchanged from old strong. |
| dv2-08 | Schema-valid clarification targeting eligibility, missing `order_id`, asking the user to provide the ID “for order willow-357.” | Wrong clarification target, missing field, and reason. The ID is already present in both prompt and generated question. User has not selected between status and eligibility, so the unresolved issue is which supported action is wanted. Gold JSON-null target, empty fields, and ambiguous_intent remain appropriate. The model partly recovers the clarification class but not its meaning. |
| dv2-09 | Free-text explanation of “return window,” not JSON. | JSON parse failure / output-contract failure. The user requests general terminology; gold no_tool/informational_request is appropriate. A direct explanation may serve a normal conversation, but it is not a usable record for this JSON-output benchmark. Old strong also failed this case, using a schema-invalid clarification. |
| dv2-10 | Free-text sentence: “It means your order is currently being prepared and will be delivered soon.” | JSON parse failure / output-contract failure. Existing status is provided and no new lookup is requested, so gold no_tool/informational_request is sound. The explanation's factual quality is outside this evaluator; it should not receive an unmeasured semantic-success claim. Old strong also returned prose and failed. |
| dv2-11 | Calls `propose_refund` with reason `payment_card_issue` and extra `proposal_only=true`. | Wrong action plus tool-argument schema failures. The user demands actual money movement and explicitly rejects a simulated proposal. No real-payment tool exists. The model invents an enum value and argument to force an unsupported request into the available proposal tool. Gold no_tool/unsupported_request is correct. The supplied ID/amount are not hallucinated; the reason/property are. |

The five invalid strong-v2 records comprise two raw-JSON parse failures (dv2-09,
10), one invalid outcome structure (02), and two tool-argument/schema failures
(05,11). The other two failed records (03,08) pass schema validation but have the
wrong semantic decision/details. Schema validity alone therefore cannot certify
correct behavior.

## Improvements and unchanged success

| Case | What improved |
| --- | --- |
| dv2-04 | Refund arithmetic and arguments were already correct; strong-v2 fixes the invalid old `type="propose_refund"` tag to `type="tool_call"`. |
| dv2-06 | Both runs ask for the correct missing reason; strong-v2 corrects ambiguous_intent to missing_required_information. |
| dv2-07 | Replaces an unsupported invented amount of 50.0 with the required missing-amount clarification. This is a substantive decision improvement. |
| dv2-12 | Corrects no_tool's reason from informational_request to no_action_requested for a closing acknowledgment. |

Case dv2-01 remains successful in both runs. Four gains minus one regression
produce the net three-case improvement. Outcome-class accuracy rises from 4/12
to 6/12, while invalid records decrease from 6/12 to 5/12. These metrics describe
different aspects: dv2-08 earns class credit for choosing clarification but fails
strict success because its target/fields/reason are wrong.

## Acceptance limits

The matched cases support retaining strong-v2 as a promising development
candidate, with explicit regression/failure evidence preserved. They do not show
that the prompt is reliable yet: seven of twelve tasks still fail, and correct
JSON/tool formatting can regress on an otherwise easy eligibility case. The
saved descriptive bootstrap interval for the strict paired difference includes
zero (approximately -8.3 to +58.3 percentage points), so a strong statistical
improvement claim is unsupported.

No repair should be applied to the frozen gold or raw outputs to increase the
score. Future prompt or decoding experiments require their own saved versions,
paired conditions, and fresh development checks. These twelve practice records
and the original twenty smoke records are distinct; the first 7/20 baseline
remains a separate historical result.
