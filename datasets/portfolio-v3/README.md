# Portfolio-v3 blind system test

This set contains **40 individually authored fictional customer-support requests**:
16 tool calls, 12 clarifications and 12 no-tool decisions. The difficulty mix was
defined during authoring, before inference: nine easy, 20 medium and 11 hard.
These labels are descriptive assistant judgments, not independently calibrated
difficulty measurements.

The set combines routine support requests with corrections, explicit conversational
references, requested quantities, exact percentage calculations, missing fields,
competing facts, informational questions, unsupported operations and statements
that authorize no action. All four refund reasons appear in tool-call gold.
Numbers and order references are fictional. No customer data or external lookup
is needed to determine the expected decision.

Every task uses the canonical three-tool registry and task schema 3.0.0. Gold
requires the requested action and supplied or exactly derivable arguments. It does
not assume an order-ID format, demo-store membership, refund eligibility policy,
price cap, real payment capability or currency conversion. Execution must remain
disabled when scoring this decision test. Clarification-question prose is not
human graded by the canonical strict-success metric.

Authoring and review are isolated from the revised implementation, prompts and
model outputs. Known broad failure categories and historical benchmark inputs
were available to the author. This is fresh content, not a claim that the
underlying reasoning concepts have never appeared before.

The author and a separate assistant review pass inspect every gold label and its
supporting evidence. This is **assistant review, not independent human annotation**.
An additional reviewer started without parent implementation history and accepted all 40 outcomes; see
[additional-blind-review.json](additional-blind-review.json). The coordinator
performed structural/hash checks and did not supply the semantic verdict.
See [secondary-review.json](secondary-review.json),
[validation.json](validation.json) and the
[semantic ledger](../../docs/portfolio-v3-review.md). The implementers must leave
the holdout and semantic ledger unread until the candidate is frozen.

Before the final run, preserve the exact file and manifest hashes in the evaluation
protocol, plus source, model, backend and generation settings. Run each frozen
system once on all 40 unchanged cases. Record intentional system differences,
particularly if the model or CPU backend changes. Retain original text, every
repair, blocked decisions, errors, latency, gains and regressions. A model choice
must be based on development performance before this test is opened.

Do not use these cases as unit-test fixtures or change prompts/guards after
observing their outputs. A later label correction needs a new data version and
explicit provenance; it must not silently replace the original result. Once this
set is evaluated, it is seen and cannot serve as a fresh final test again.

Normalization checks compare these 40 prompts with 112 earlier smoke, practice,
portfolio-v1 and portfolio-v2 inputs. No exact or reference/number-normalized
template overlaps were found. Such checks cannot establish semantic independence.
The small targeted English-only set does not establish production accuracy,
representative customer traffic, fairness across languages or execution safety.

The manifest and review files define the frozen checkpoint; no model score is
claimed by data validation or the descriptive difficulty mix.

Frozen `holdout.jsonl`: **72,611 bytes**; SHA-256:

`eb0dd97d0a15308415a9537e33020d387801b8b426d78192f6cf2a81fcd900a9`

[manifest.json](manifest.json) records counts, provenance and supporting-file hashes.
