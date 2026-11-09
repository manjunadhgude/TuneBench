# Error analysis for the frozen system comparison

All judgments below use the unchanged frozen reference labels. This is computational failure analysis, not independent human validation of the labels. Neither source nor data was changed after observing these test outputs.

## Paired strict-success changes

**Original first answers:** 3 gains, 2 regressions; 6 correct in both and 9 incorrect in both.

Gains: `portfolio-v2-holdout-07`, `portfolio-v2-holdout-08`, `portfolio-v2-holdout-16`.

Regressions: `portfolio-v2-holdout-05`, `portfolio-v2-holdout-11`.

**Accepted final decisions:** 7 gains, 2 regressions; 0 correct in both and 11 incorrect in both.

Gains: `portfolio-v2-holdout-01`, `portfolio-v2-holdout-02`, `portfolio-v2-holdout-03`, `portfolio-v2-holdout-05`, `portfolio-v2-holdout-06`, `portfolio-v2-holdout-15`, `portfolio-v2-holdout-20`.

Regressions: `portfolio-v2-holdout-11`, `portfolio-v2-holdout-18`.

## Guard and repair effects

| System | Correct first answer later rejected | Correct last answer rejected | Incorrect accepted decision | Repairs improving final strict success |
| --- | ---: | ---: | ---: | ---: |
| v0.3 | 6 | 7 | 3 | 0 |
| v0.4 | 5 | 3 | 0 | 3 |

A correct generated answer that the guard rejects is a validator false block relative to these labels. An incorrect accepted decision is a decision error; execution was disabled, so it does not by itself establish a real transaction or unsafe execution.

**v0.3:**

Correct last answers rejected: `portfolio-v2-holdout-01`, `portfolio-v2-holdout-02`, `portfolio-v2-holdout-03`, `portfolio-v2-holdout-04`, `portfolio-v2-holdout-05`, `portfolio-v2-holdout-06`, `portfolio-v2-holdout-07`.
Incorrect accepted decisions: `portfolio-v2-holdout-12`, `portfolio-v2-holdout-13`, `portfolio-v2-holdout-16`.
Repairs improving accepted final success: none.

**v0.4:**

Correct last answers rejected: `portfolio-v2-holdout-04`, `portfolio-v2-holdout-07`, `portfolio-v2-holdout-08`.
Incorrect accepted decisions: none.
Repairs improving accepted final success: `portfolio-v2-holdout-05`, `portfolio-v2-holdout-15`, `portfolio-v2-holdout-20`.

v0.4 still reduces its own 9/20 raw score to 7/20 final successes: five correct first answers are lost and three initial errors are repaired. Cases 04, 07 and 08 retain a correct last answer but are blocked by evidence extraction. Case 04 describes receiving a different product using the actual product names; the reason parser misses that relation. Case 07 requires following a requested subset across sentences, and case 08 refers back to a previously stated percentage base. These are remaining limits of the evidence rules.

In cases 16 and 18, the model's first no-action decision is correct. The guard misreads the closing/withdrawal text as an ambiguous action and requests a repair. The model then generates an incorrect clarification, which is also blocked. These two cases are repair regressions caused by an incorrect validation trigger, not improvements from adding a retry.

All 20 v0.4 first outputs are JSON objects, but only 19 satisfy the canonical contract. Case 11 returns a zero refund amount, violating the positive-amount bound. This demonstrates why complete schema validation remains necessary after token constraints.

## Remaining v0.4 final failures

| Case | Final status | What the last generated answer got wrong | Validation result |
| --- | --- | --- | --- |
| `portfolio-v2-holdout-04` | blocked | Correct decision was rejected by the guard. | reason is not supported by the resolved request evidence |
| `portfolio-v2-holdout-07` | blocked | Correct decision was rejected by the guard. | refund_amount must match explicit or exactly derived monetary evidence |
| `portfolio-v2-holdout-08` | blocked | Correct decision was rejected by the guard. | refund_amount must match explicit or exactly derived monetary evidence |
| `portfolio-v2-holdout-09` | blocked | Expected clarification; generated tool_call. | order_id must match the resolved literal order reference |
| `portfolio-v2-holdout-10` | blocked | Expected clarification; generated tool_call. | reason is not supported by the resolved request evidence |
| `portfolio-v2-holdout-11` | blocked | Expected clarification; generated tool_call. | refund_amount must match explicit or exactly derived monetary evidence |
| `portfolio-v2-holdout-12` | blocked | Expected clarification; generated tool_call. | order_id must match the resolved literal order reference |
| `portfolio-v2-holdout-13` | blocked | Expected clarification; generated tool_call. | reason is not supported by the resolved request evidence |
| `portfolio-v2-holdout-14` | blocked | target_tool_name: expected None, generated 'get_order_status'; missing_fields: expected [], generated ['order_id']; reason_code: expected 'ambiguous_intent', generated 'ambiguous_reference' | The action is unresolved; a particular target tool is not supported; Unresolved action choice requires the ambiguous_intent reason |
| `portfolio-v2-holdout-16` | blocked | Expected no_tool; generated clarification. | The action is unresolved; a particular target tool is not supported; Unresolved action choice requires the ambiguous_intent reason |
| `portfolio-v2-holdout-17` | blocked | Expected no_tool; generated tool_call. | Requested action does not support this tool; no action substitution; reason is not supported by the resolved request evidence; refund_amount must match explicit or exactly derived monetary evidence |
| `portfolio-v2-holdout-18` | blocked | Expected no_tool; generated clarification. | The action is unresolved; a particular target tool is not supported; Unresolved action choice requires the ambiguous_intent reason |
| `portfolio-v2-holdout-19` | blocked | reason_code: expected 'informational_request', generated 'no_action_requested' | No-tool reason does not match the requested action evidence |

The full raw first answer, repair, parsed decisions and validation messages remain in each journal. The audit also records every case’s expected, first, last and accepted outcome. Format validity and guard acceptance do not establish semantic correctness.

This set is now spent for final testing. Future work should use broader reviewed development examples, a stronger baseline if appropriate, and a new frozen final set. The comparison changes several components together and cannot attribute gains to a single prompt or constraint, nor support a fine-tuning claim.
