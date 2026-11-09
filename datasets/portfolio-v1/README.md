# Portfolio benchmark v1

This small, fictional benchmark exercises the three canonical TuneBench decisions:
one tool call, a clarification request, or no tool. It supports development and
a frozen portfolio evaluation; it is not a production dataset or a model-training
corpus. No real tools are executed when validating its gold decisions.

| File | Examples | Tool call | Clarification | No tool | Split field |
| --- | ---: | ---: | ---: | ---: | --- |
| development.jsonl | 40 | 14 | 13 | 13 | validation |
| holdout.jsonl | 20 | 8 | 6 | 6 | test |

Every record follows task schema 3.0.0, embeds the same canonical three-tool
registry, and includes a distinct example/scenario ID and manual provenance.
All four allowed refund reasons appear in proposal examples in each partition.
Amounts, identifiers, and facts needed to choose an outcome are in the prompt;
no external database or demo-order lookup is needed to know the gold decision.

Development cases cover explicit tool requests, missing arguments, unresolved
values, information requests, unsupported actions, closing statements, and quoted
malicious instructions. Holdout cases emphasize corrections, contextual references,
arithmetic with supplied values, unresolved corrections/calculations, negated
scope, malicious quoted notes, and withdrawn requests. Prompts and descriptive
family IDs are disjoint across the files. Broad concepts recur, so family-ID
separation does not prove entirely new or independent reasoning patterns.

Difficulty follows the actual scenario: development has 16 easy, 21 medium, and
3 hard cases; holdout has 10 medium and 10 hard cases. These distributions are
intentional coverage choices, not estimates of typical customer traffic.

## Frozen files

The manifest records SHA-256, byte size, counts, families, and limitations for
each data file. Before portfolio inference, the frozen hashes are:

- Development: `4f38c51625766a7fae78f8b8dbb9a9c24e654a31ba3b145600804f97e928759c`
- Holdout: `41bc632a179f769c0b9080f6a54c0952e148cb359cba1885cf263a3dfab80510`

Use development data to select prompts and debug software. Use every holdout
case with the finalized pipeline and preserve all raw outputs, failures, and
inference settings. Never change this holdout or its gold labels to improve a
measured score; publish later revisions as a new dataset version with new hashes.

The original 20 smoke cases and 12 paired-development cases are separate
historical measurements. No exact prompts or records were reused from them or
from the 1,250-example generator's final-test candidates. The author knew prior
project failure categories, so this curated set is targeted rather than a random
sample. No portfolio model outputs were inspected while authoring or reviewing
these scenarios.

## Review and limitations

All 60 cases received an assistant semantic review, recorded individually in
[the review ledger](../../docs/portfolio-data-review.md). This is not human review
or independent human annotation. The same assistant authored and reviewed the
cases. Automated checks validate contracts, hashes, counts, identifier isolation,
exact prompt uniqueness, and selected arithmetic facts. Those checks cannot
certify all gold semantics or representative coverage.

Refund gold follows the canonical argument contract: positive amount and an
allowed reason. It does not enforce a demo price cap, order-ID pattern, refund
policy, or eligibility result. Live demo business rules are a separate layer.
Information-only gold says no available tool should run; it does not claim the
model's eventual prose answer is factually correct.
