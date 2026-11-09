# Development integration smoke

These four public development requests checked actual local Qwen generation with
the first strong-v3 prompt and JSON token constraints. This is not a held-out
quality estimate. All outputs, validation failures and repairs are retained.

The status lookup passed. The model invented an amount when none was supplied
and substituted a proposal for an actual-payment request; validation blocked both.
It correctly generated the quantity-derived amount of INR 50, but the initial
guard also treated the count of two units as a requested monetary amount and
blocked it. A generic regression test and evidence-role fix addressed that bug.

Development continued afterward: a missing-amount prompt example was added and
the three affected public requests were checked again in
[the final development smoke](../development-v3-smoke-final/). Its actual-payment
and missing-amount failures remained blocked; the derived INR 50 call passed.
No original capture was changed. Prompt hashes and model metadata identify the
captured requests. Code was subsequently frozen before the separate matched test.

These cases deliberately repeat known development concepts. Do not combine them
with test results, call them unseen, or claim that successful formatting implies
correct decision making. The model weights were unchanged; no training occurred.
