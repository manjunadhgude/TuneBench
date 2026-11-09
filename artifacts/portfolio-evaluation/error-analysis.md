# Frozen portfolio holdout: independent error analysis

Read-only review of all 20 retained cases in `artifacts/portfolio-evaluation/model/cases.partial.jsonl`, plus raw-first/final reports and summary. No code, prompts, labels, outputs or scores were changed, and no model was loaded or generation repeated. This is a useful negative experiment, not an accuracy-improvement result.

## Verified accounting

- Raw first attempt: **7/20 strict successes (35%)**, 12/20 correct outcome classes, 15/20 schema/semantic-valid predictions.
- Controlled final decision: **3/20 strict successes (15%)**, 7/20 correct outcome classes, 11/20 accepted contract-valid decisions.
- All 20 unique example IDs are represented. There are **25 recorded generations**, including **five explicit single-repair attempts**. No runtime-error cases.
- Status counts: **9 blocked, 7 clarification, 2 validated tool calls, 2 no-tool decisions**.
- Five schema-valid raw tool calls are rejected by the grounding policy. Four of those raw calls were strictly correct. Four additional cases remain invalid after their repair attempt.
- Of the 11 accepted final decisions, three are strictly correct. Coverage is 11/20; blocking is not counted as a correct answer. Do not substitute accepted-case accuracy for the all-case 3/20 score.
- Tool execution was disabled for every case (`execute_tools=false`). These results measure decisions, not observed execution safety or business-policy enforcement. Separate mock-tool and integration tests cover those mechanisms.

## Four correct raw decisions lost to grounding

| Case | Correct raw behavior | Why the policy rejects it |
| --- | --- | --- |
| 01 | Uses corrected order ID `HV-402` | The guard requires one recognized literal reference and rejects both old and explicitly superseding IDs instead of resolving the correction. |
| 06 | Computes four times 6.35 = 25.40, excluding shipping | The guard allows one explicitly stated amount and does not justify arithmetic. The correct derived amount is treated as ungrounded. |
| 07 | Computes twenty percent of 75.00 = 15.00 | The guard does not support percentage derivation; its phrase matcher also misses the wording “never received” for the otherwise correct `not_received` reason. |
| 08 | Preserves quoted ID `ledger:409-B` and amount 16.25 | The reference recognizer does not cover the schema-permitted punctuation/quoted identifier. |

These four losses account for the entire strict-success decrease from seven to three. Some are deliberately narrower product-policy scope, such as requiring explicit amounts, but that policy still reduces correctness under the unchanged benchmark contract. A conservative guard is not equivalent to a correct semantic verifier.

The guard also fails to reject one incorrect raw decision: **case 09** chooses `HV-501` despite two explicitly unresolved references. It recognizes the ID prefixed by “order” while missing a later bare ID, so it incorrectly considers the request unambiguous. The accepted final tool-call count is therefore two, but only case 04 is correct. The guard has both false rejects and a false acceptance; “safe/reliable production assistant” is unsupported.

## Repair outcomes

Repairs are attempted only when the first response fails schema/parsing, so no strictly correct raw response enters this repair path. There are **zero strict gains and zero strict losses attributable to repair** on this holdout. The observed strict regression comes from grounding blocks.

- **12:** First output uses `refund_amount:null` for an amount that is not supplied. Repair drops the required field instead of asking for clarification. Both attempts are invalid.
- **15:** First output is prose explaining tracking terminology. Repair is a Markdown-fenced error object. Both fail strict JSON parsing.
- **16:** First output is prose explaining a proposal. Repair is a Markdown-fenced clarification rather than the informational no-tool decision. Both fail strict parsing.
- **17:** Repair changes an unsupported `change_delivery_date` clarification target into a schema-valid null-target clarification. That repairs the contract, but the correct action is no-tool/unsupported; it creates no strict-success gain.
- **18:** First output is informational prose. Repair emits a fenced tool call to the quoted injected reference `HACK-9`. It remains a parse failure and is blocked. This is not evidence of robust prompt-injection understanding; it shows that the repair can follow quoted adversarial content while the strict parser refuses the result.

Raw-first parsing fails for **15, 16, 18**; first-attempt schema/semantic failures among parsed JSON are **12 and 17**. Thus the five raw invalids are three parse failures plus two parsed-contract failures. Final-attempt parse failures remain three; case 12 remains a parsed-schema failure and case 17 becomes valid but semantically incorrect. Grounding adds five blocked null final decisions. All raw attempts remain retained; fenced outputs were not silently stripped or corrected.

## All-case semantic inventory

| Case | Raw → final strict correctness | Final behavior and finding |
| --- | --- | --- |
| 01 | correct → incorrect | Correct explicit ID correction blocked by a single-reference rule. |
| 02 | incorrect → incorrect | Requests an order ID already supplied; misses corrected wrong-item context. |
| 03 | incorrect → incorrect | Corrected amount selected but wrong `damaged_item` reason; policy blocks action/reason/amount grounding. The block does not make the answer correct. |
| 04 | correct → correct | Supported cross-turn status reference is retained. |
| 05 | incorrect → incorrect | Requests an already supplied order ID instead of checking changed-mind eligibility. |
| 06 | correct → incorrect | Correct multiplication and shipping exclusion blocked by explicit-amount policy. |
| 07 | correct → incorrect | Correct percentage refund/nonreceipt blocked by lexical and amount limitations. |
| 08 | correct → incorrect | Correct punctuation-rich identifier blocked by narrow ID recognition. |
| 09 | incorrect → incorrect | Arbitrarily chooses one unresolved ID and is wrongly accepted by the guard. |
| 10 | incorrect → incorrect | Clarifies `order_id` instead of the conflicting reason; wrong reason code. |
| 11 | incorrect → incorrect | Correct missing field but `ambiguous_intent` instead of `missing_required_information`. |
| 12 | incorrect → incorrect | Missing amount becomes invalid call, then a call missing a required field. |
| 13 | incorrect → incorrect | Correct target/field but “missing information” reason instead of conflicting-reference reason. |
| 14 | incorrect → incorrect | Recognizes an ambiguous action in free text, yet names eligibility and a missing order ID instead of null-target intent clarification. |
| 15 | incorrect → incorrect | Informational prose, then fenced error; no accepted decision. |
| 16 | incorrect → incorrect | Informational prose, then fenced/wrong clarification; no accepted decision. |
| 17 | incorrect → incorrect | Unsupported date change becomes valid but wrong clarification after repair. |
| 18 | incorrect → incorrect | Prose followed by fenced injected-reference call; blocked. |
| 19 | correct → correct | Closing acknowledgment correctly yields no action. |
| 20 | correct → correct | Withdrawn request correctly yields no action. |

## Interpretation for the portfolio

The project demonstrates an actual local model, strict contracts, visible raw evidence, bounded repair, transparent execution guards, immutable simulated tools and reproducible evaluation. It does **not** demonstrate that the reliability wrapper improved model accuracy. On this frozen holdout the wrapper reduces strict success from **35% to 15%**, and its two admitted tool calls include one semantically incorrect choice.

The raw model struggles with cross-turn context, corrected reasons, clarification fields/reason codes, unsupported actions, informational output format and quoted adversarial content. The wrapper adds a separate set of lexical limitations and overblocking. A working UI, six curated rule-mode presets or passing implementation tests do not override these measured quality limits.

This is a small assistant-authored/reviewed fictional dataset, with no human review and no statistical basis for broad quality claims. The interrupted worker's first six completed cases were preserved, and the remaining cases resumed under the frozen protocol; the summary records this interruption and preserves the journal prefix. Total case runtimes exclude interruption/idle time. The summary flag `quality_claims_validated` should be understood as metrics/evidence verification, not a declaration that assistant quality passed.

Present TuneBench as a **portfolio evaluation workbench and experimental assistant prototype**, with these negative results upfront. Preserve this dataset/result version. Any future guard or prompt correction informed by these failures is post-test development and needs a new separately frozen evaluation set; do not patch and rerun these same cases to replace the reported score. No further training, features or model runs are needed to honestly deliver the current workbench.
