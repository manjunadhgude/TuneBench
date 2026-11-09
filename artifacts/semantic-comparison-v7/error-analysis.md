# Remaining failures on the frozen test

No labels or implementation were changed after observing these outputs. A blocked decision counts as a failure even when it prevented execution.

## v0.7: 10 final failures

### portfolio-v5-holdout-40

Yesterday a representative proposed INR 60 for damaged order NP-902. I am telling you what happened, without requesting another check or proposal.

Expected: `{"reason_code": "no_action_requested", "type": "no_tool"}`

Accepted: `{"type": "tool_call", "tool_name": "propose_refund", "arguments": {"order_id": "NP-902", "refund_amount": 60, "reason": "damaged_item"}}` · status: `validated`

Review for primary attempt 1: **contradicted** — Customer explicitly states a representative proposed INR 60 for a damaged order, indicating a clear request for refund action. The no_tool decision ignores this active request.

Review for primary attempt 2: **supported** — Customer confirms a prior proposal of INR 60 for damaged item in order NP-902 and states no further check or proposal is requested. The reason 'damaged_item' matches the stated event, and the amount aligns with the proposed value.

### portfolio-v5-holdout-22

I received a wrong item in order XD-357. Its list price is INR 300; the overall basket discount was INR 60, with no allocation by item. Propose the net price I paid for this item.

Expected: `{"missing_fields": ["refund_amount"], "reason_code": "missing_required_information", "target_tool_name": "propose_refund", "type": "clarification"}`

Accepted: `null` · status: `blocked`

- Semantic review: The customer specifies a wrong item but does not explicitly state the reason code or provide clarity on whether this qualifies for refund eligibility. The missing 'reason' field and ambiguous reference prevent qualification of refund eligibility.

Review for primary attempt 1: **contradicted** — The customer specifies a wrong item and requests the net price paid, which requires calculating the item's price after discount. This involves order details and pricing logic, not an unsupported action.

Review for primary attempt 2: **contradicted** — The customer specifies a wrong item but does not explicitly state the reason code or provide clarity on whether this qualifies for refund eligibility. The missing 'reason' field and ambiguous reference prevent qualification of refund eligibility.

### portfolio-v5-holdout-36

For order JK-568, transfer INR 175 back to my bank now. I am requesting the actual payment, not a simulated proposal.

Expected: `{"reason_code": "unsupported_request", "type": "no_tool"}`

Accepted: `null` · status: `blocked`

- Semantic review: The customer explicitly requests actual payment transfer, which is not supported as no tool exists for real refunds or payments. Only simulated proposals are allowed via propose_refund.

Review for primary attempt 1: **contradicted** — The customer explicitly requests actual payment transfer, which is not supported as no tool exists for real payments or order modifications. Only simulated proposals are allowed via propose_refund.

Review for primary attempt 2: **contradicted** — The customer explicitly requests actual payment transfer, which is not supported as no tool exists for real refunds or payments. Only simulated proposals are allowed via propose_refund.

### portfolio-v5-holdout-27

I changed my mind about order DA-913. Please prepare a refund proposal for INR 0; I have not supplied a valid positive replacement amount.

Expected: `{"missing_fields": ["refund_amount"], "reason_code": "missing_required_information", "target_tool_name": "propose_refund", "type": "clarification"}`

Accepted: `null` · status: `blocked`

- outcome.arguments/refund_amount: 0 is less than or equal to the minimum of 0

Review for primary attempt 1: **contradicted** — Customer explicitly states a refund of INR 0 and confirms no positive replacement amount is supplied. The proposed clarification asks for the refund amount, which is already specified in the message.

### portfolio-v5-holdout-19

Please prepare a refund proposal for order VB-135. I will explain the problem and tell you the amount after you ask.

Expected: `{"missing_fields": ["reason", "refund_amount"], "reason_code": "missing_required_information", "target_tool_name": "propose_refund", "type": "clarification"}`

Accepted: `{"type": "clarification", "target_tool_name": "propose_refund", "missing_fields": ["refund_amount"], "reason_code": "missing_required_information", "question": "What amount should I use for the refund proposal?"}` · status: `clarification`

Review for primary attempt 1: **supported** — The customer has not specified a refund amount or provided enough detail to determine one, and the proposed action requests missing required information.

### portfolio-v5-holdout-23

Order YE-468 has three cracked mugs. Propose their combined item price, excluding delivery. I only know delivery cost INR 55; I have not supplied any mug price.

Expected: `{"missing_fields": ["refund_amount"], "reason_code": "missing_required_information", "target_tool_name": "propose_refund", "type": "clarification"}`

Accepted: `null` · status: `blocked`

- Semantic review: Customer mentions cracked mugs (damaged_item) but provides no mug prices or refund amount. Proposal requests missing data without a valid calculation or price source.

Review for primary attempt 1: **contradicted** — Customer mentions cracked mugs (damaged_item) but provides no mug prices or refund amount. Proposal requests missing data without grounding in supplied facts.

Review for primary attempt 2: **contradicted** — Customer mentions cracked mugs (damaged_item) but provides no mug prices or refund amount. Proposal requests missing data without a valid calculation or price source.

### portfolio-v5-holdout-28

Please check refund eligibility for order EB-124. My reason is that the purchase earned fewer reward points than I expected. Nothing is damaged, missing, wrong or unwanted.

Expected: `{"missing_fields": ["reason"], "reason_code": "missing_required_information", "target_tool_name": "check_refund_eligibility", "type": "clarification"}`

Accepted: `{"type": "clarification", "target_tool_name": "check_refund_eligibility", "missing_fields": ["reason"], "reason_code": "ambiguous_reference", "question": "What is the correct reason for refund eligibility? The only valid reasons are damaged_item, wrong_item, not_received, or changed_mind."}` · status: `clarification`

Review for primary attempt 1: **supported** — The customer's stated reason 'earned fewer reward points than expected' is not a valid refund reason per policy; only damaged_item, wrong_item, not_received, or changed_mind are eligible. The proposed clarification correctly identifies the missing/ambiguous reference to a valid reason.

### portfolio-v5-holdout-35

Order HJ-457 is the wrong size. Exchange it for size 10, please; I do not want a refund or an eligibility check.

Expected: `{"reason_code": "unsupported_request", "type": "no_tool"}`

Accepted: `null` · status: `blocked`

- Semantic review: Customer requests an exchange, not a refund or eligibility check. Exchanges are unsupported as no tool exists for them. The proposed no_tool is incorrect because the request clearly demands action (exchange), which cannot be fulfilled.

Review for primary attempt 1: **contradicted** — Customer requests an exchange, not a refund or eligibility check. Exchanges are unsupported as no tool exists for them. The proposed no_tool is incorrect because the request clearly demands action (exchange), which cannot be fulfilled.

Review for primary attempt 2: **contradicted** — Customer requests an exchange, not a refund or eligibility check. Exchanges are unsupported as no tool exists for them. The proposed no_tool is incorrect because the request clearly demands action (exchange), which cannot be fulfilled.

### portfolio-v5-holdout-21

The item line for order WC-246 totals INR 132 for identical pens, but the invoice does not say how many pens were in the pack. One never arrived. Propose the price of just that missing pen.

Expected: `{"missing_fields": ["refund_amount"], "reason_code": "missing_required_information", "target_tool_name": "propose_refund", "type": "clarification"}`

Accepted: `null` · status: `blocked`

- Semantic review: The customer states one pen never arrived (not_received), but requests only the price of a single missing pen, not the full INR 132. The proposed refund amount does not calculate the unit price from the total.

- Calculator: Calculation uses an unsupported or unsupplied number

Review for primary attempt 1: **contradicted** — The customer specifies a missing pen from an order with total INR 132 for identical pens, implying the price per pen can be derived. The refund amount is not explicitly stated but logically follows from dividing the total by the number of pens (unspecified). A calculation is needed to derive the per-pen price.

Review for primary attempt 2: **contradicted** — The customer states one pen never arrived (not_received), but requests only the price of a single missing pen, not the full INR 132. The proposed refund amount does not calculate the unit price from the total.

Calculator: Calculation uses an unsupported or unsupplied number

### portfolio-v5-holdout-12

For order NF-479, propose the paid value of these damaged goods only: two plates at INR 31.50 each and one cup at INR 18.75. Three intact cups at the same price stay with me.

Expected: `{"arguments": {"order_id": "NF-479", "reason": "damaged_item", "refund_amount": 81.75}, "tool_name": "propose_refund", "type": "tool_call"}`

Accepted: `{"type": "clarification", "target_tool_name": "propose_refund", "missing_fields": ["refund_amount"], "reason_code": "missing_required_information", "question": "What should the refund amount be based on the damaged goods?"}` · status: `clarification`

Review for primary attempt 1: **supported** — The customer specifies damaged goods (two plates and one cup) with exact prices, enabling a clear refund calculation. The missing field is the refund amount, which can be derived from the stated values.

## v0.6: 17 final failures

### portfolio-v5-holdout-14

Order RH-691 was a set of five identical coasters for INR 82.50 in total. One coaster did not arrive. Propose the equal share of the total for that missing coaster only.

Expected: `{"arguments": {"order_id": "RH-691", "reason": "not_received", "refund_amount": 16.5}, "tool_name": "propose_refund", "type": "tool_call"}`

Accepted: `null` · status: `blocked`

- refund_amount must match explicit or exactly derived monetary evidence

### portfolio-v5-holdout-10

Order LD-257 contains a lamp priced at INR 680 and a separate refundable deposit of INR 90. The lamp is broken. Propose only its stated price, excluding the deposit.

Expected: `{"arguments": {"order_id": "LD-257", "reason": "damaged_item", "refund_amount": 680}, "tool_name": "propose_refund", "type": "tool_call"}`

Accepted: `null` · status: `blocked`

- refund_amount must match explicit or exactly derived monetary evidence

### portfolio-v5-holdout-22

I received a wrong item in order XD-357. Its list price is INR 300; the overall basket discount was INR 60, with no allocation by item. Propose the net price I paid for this item.

Expected: `{"missing_fields": ["refund_amount"], "reason_code": "missing_required_information", "target_tool_name": "propose_refund", "type": "clarification"}`

Accepted: `{"type": "no_tool", "reason_code": "unsupported_request"}` · status: `no_tool`

### portfolio-v5-holdout-02

Purchases in chronological order: ID elm/19, a kettle; ID oak/24, a flask; ID ash/27, a pan. Please look up delivery status for my most recent purchase.

Expected: `{"arguments": {"order_id": "ash/27"}, "tool_name": "get_order_status", "type": "tool_call"}`

Accepted: `null` · status: `blocked`

- order_id must match the resolved literal order reference

### portfolio-v5-holdout-04

I placed order QL-810 for a 250 rupee bag and order QL-811 for a 480 rupee bag. Fetch the delivery status of the less expensive bag.

Expected: `{"arguments": {"order_id": "QL-810"}, "tool_name": "get_order_status", "type": "tool_call"}`

Accepted: `{"type": "clarification", "target_tool_name": "get_order_status", "missing_fields": ["order_id"], "reason_code": "ambiguous_reference", "question": "Should I retrieve the status for order QL-810 or QL-811?"}` · status: `clarification`

### portfolio-v5-holdout-03

A forwarded note says "check order AG-220". That was from a different customer. My own order is BH-331; please retrieve its status.

Expected: `{"arguments": {"order_id": "BH-331"}, "tool_name": "get_order_status", "type": "tool_call"}`

Accepted: `null` · status: `blocked`

- order_id must match the resolved literal order reference

### portfolio-v5-holdout-07

Order HM-864 was intended as a gift, but I decided to keep it. Wait, my final decision is that I no longer want it after all. Check whether I can get a refund.

Expected: `{"arguments": {"order_id": "HM-864", "reason": "changed_mind"}, "tool_name": "check_refund_eligibility", "type": "tool_call"}`

Accepted: `{"type": "clarification", "target_tool_name": "check_refund_eligibility", "missing_fields": ["order_id"], "reason_code": "missing_required_information", "question": "What is the order ID you would like to check for refund eligibility?"}` · status: `clarification`

### portfolio-v5-holdout-16

For damaged order TK-813, my first email asked for INR 92 based on an estimate. The invoice now confirms INR 86.40. Ignore that earlier estimate and propose the invoice amount instead.

Expected: `{"arguments": {"order_id": "TK-813", "reason": "damaged_item", "refund_amount": 86.4}, "tool_name": "propose_refund", "type": "tool_call"}`

Accepted: `null` · status: `blocked`

- refund_amount must match explicit or exactly derived monetary evidence

### portfolio-v5-holdout-06

Order GR-751: I selected size 9 but the supplied shoes are size 7. Please check refund eligibility for the size mismatch.

Expected: `{"arguments": {"order_id": "GR-751", "reason": "wrong_item"}, "tool_name": "check_refund_eligibility", "type": "tool_call"}`

Accepted: `{"type": "clarification", "target_tool_name": "check_refund_eligibility", "missing_fields": ["reason"], "reason_code": "missing_required_information", "question": "What is the correct reason for refund eligibility?"}` · status: `clarification`

### portfolio-v5-holdout-08

The carrier marked order JV-903 delivered, but nothing arrived at my address. Ticket CS-882 is my support ticket. Check refund eligibility for the missing delivery.

Expected: `{"arguments": {"order_id": "JV-903", "reason": "not_received"}, "tool_name": "check_refund_eligibility", "type": "tool_call"}`

Accepted: `{"type": "clarification", "target_tool_name": "check_refund_eligibility", "missing_fields": ["reason"], "reason_code": "missing_required_information", "question": "What is the reason for the refund eligibility check?"}` · status: `clarification`

### portfolio-v5-holdout-19

Please prepare a refund proposal for order VB-135. I will explain the problem and tell you the amount after you ask.

Expected: `{"missing_fields": ["reason", "refund_amount"], "reason_code": "missing_required_information", "target_tool_name": "propose_refund", "type": "clarification"}`

Accepted: `{"type": "clarification", "target_tool_name": "propose_refund", "missing_fields": ["refund_amount"], "reason_code": "missing_required_information", "question": "What amount should I use for the refund proposal?"}` · status: `clarification`

### portfolio-v5-holdout-23

Order YE-468 has three cracked mugs. Propose their combined item price, excluding delivery. I only know delivery cost INR 55; I have not supplied any mug price.

Expected: `{"missing_fields": ["refund_amount"], "reason_code": "missing_required_information", "target_tool_name": "propose_refund", "type": "clarification"}`

Accepted: `{"type": "clarification", "target_tool_name": "propose_refund", "missing_fields": ["refund_amount", "reason"], "reason_code": "missing_required_information", "question": "What is the price of each mug and what is the reason for the refund?"}` · status: `clarification`

### portfolio-v5-holdout-05

The seam of the backpack in order FC-620 has split open. Check whether this qualifies for a refund; I am not asking you to propose an amount.

Expected: `{"arguments": {"order_id": "FC-620", "reason": "damaged_item"}, "tool_name": "check_refund_eligibility", "type": "tool_call"}`

Accepted: `null` · status: `blocked`

- reason is not supported by the resolved request evidence

### portfolio-v5-holdout-28

Please check refund eligibility for order EB-124. My reason is that the purchase earned fewer reward points than I expected. Nothing is damaged, missing, wrong or unwanted.

Expected: `{"missing_fields": ["reason"], "reason_code": "missing_required_information", "target_tool_name": "check_refund_eligibility", "type": "clarification"}`

Accepted: `{"type": "clarification", "target_tool_name": "check_refund_eligibility", "missing_fields": ["reason"], "reason_code": "ambiguous_reference", "question": "What is the correct reason for refund eligibility? The only valid reasons are damaged_item, wrong_item, not_received, or changed_mind."}` · status: `clarification`

### portfolio-v5-holdout-13

Order PG-580 contains a wrong-colour scarf. Its listed price was INR 240, reduced by an INR 35 item discount; I paid the difference. Propose exactly the discounted price for that scarf.

Expected: `{"arguments": {"order_id": "PG-580", "reason": "wrong_item", "refund_amount": 205}, "tool_name": "propose_refund", "type": "tool_call"}`

Accepted: `{"type": "clarification", "target_tool_name": "propose_refund", "missing_fields": ["order_id", "refund_amount", "reason"], "reason_code": "missing_required_information", "question": "What is the correct order ID and refund amount for the wrong-colour scarf?"}` · status: `clarification`

### portfolio-v5-holdout-11

The item in order ME-368 cost INR 360. It arrived with a crack; I want a proposal for 25 percent of that item price. The INR 40 postage is excluded.

Expected: `{"arguments": {"order_id": "ME-368", "reason": "damaged_item", "refund_amount": 90}, "tool_name": "propose_refund", "type": "tool_call"}`

Accepted: `{"type": "clarification", "target_tool_name": "propose_refund", "missing_fields": ["refund_amount"], "reason_code": "missing_required_information", "question": "What is the exact refund amount you would like to propose based on 25 percent of the item price (INR 360)?"}` · status: `clarification`

### portfolio-v5-holdout-12

For order NF-479, propose the paid value of these damaged goods only: two plates at INR 31.50 each and one cup at INR 18.75. Three intact cups at the same price stay with me.

Expected: `{"arguments": {"order_id": "NF-479", "reason": "damaged_item", "refund_amount": 81.75}, "tool_name": "propose_refund", "type": "tool_call"}`

Accepted: `{"type": "clarification", "target_tool_name": "propose_refund", "missing_fields": ["refund_amount"], "reason_code": "missing_required_information", "question": "What should the refund amount be based on the damaged goods?"}` · status: `clarification`
