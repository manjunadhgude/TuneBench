# Candidate dataset design

TuneBench generates synthetic, deterministic candidates, beginning with 20 smoke
examples (10 tool calls, 5 clarifications, and 5 no-tool decisions). Smoke families
use a separate namespace and are for pipeline debugging, not scientific evaluation.

The larger candidate set implements the revised 30-family blueprint from the
uploaded project history: 10 non-overlapping families per split, 1,000 training,
125 validation, and 125 test candidates. All three tools appear in call and
clarification cases in each split. The test candidates have 125 distinct scenario
IDs. They remain candidates until independently reviewed and frozen by a later
research decision. Generating candidates does not make the test set a tuning set.

| Split | Tool call | Clarification | No tool | Total |
| --- | ---: | ---: | ---: | ---: |
| Train | 500 | 250 | 250 | 1,000 |
| Validation | 63 | 31 | 31 | 125 |
| Test candidate | 62 | 31 | 32 | 125 |

`generate_smoke(seed=42)` returns records. `generate_dataset(seed=42)` returns a
mapping of split names to records. Both reuse the canonical registry and validate
every output against schema 3.0.0 plus semantic tool rules. Money is generated as
integer cents before conversion; derived refunds use the exact supplied quantity
and unit price. Refund proposals are simulated and execute no transactions.

The seed, family, generator version, and example index determine every fact and
identifier. Timestamps and fabricated human-review claims are omitted. Scenario
IDs hash the complete prompt and expected outcome; they identify generated
fact patterns, not independently certified business scenarios.

## Difficulty differs from the proposed quota

The earlier proposed 30/45/25 difficulty matrix conflicts with several final
family definitions. Missing required information requires at least one inference;
unresolved competing references cannot honestly be labeled easy. Rather than
randomly labeling easy prompts hard to satisfy a quota, the generator assigns
difficulty from each template's reasoning:

- Easy: an explicit complete request or a straightforward information question.
- Medium: one missing field, a resolved distractor/reference, or a tool boundary.
- Hard: unresolved competing references, cross-turn reason resolution, or arithmetic.

The audit reports the proposed target and whether it was met. Exact split,
outcome, and family quotas are implemented. The difficulty proportions remain a
research-design issue requiring new templates and review; they are not presented
as satisfied. This is a deliberate correction to the plan.

## Quality gates and limitations

`audit_dataset(splits)` rejects invalid records, empty inputs, duplicate example
IDs, normalized duplicate prompts, family or scenario leakage across splits,
mixed outcomes within a family, and more than two examples per scenario. Test
sets with at least 50 examples must contain at least 50 distinct scenario IDs.
Reports include actual distributions, family coverage, and repeated normalized
template groups.

The near-duplicate signal replaces identifiers and numeric values; it is a review
aid, not a semantic duplicate detector. Many generated examples vary business
facts within a limited template inventory. A structural audit cannot certify
label correctness, true difficulty, semantic family independence, or population
representativeness. Review gold labels and template diversity independently,
especially the hard and held-out families. Report family-level performance and
avoid treating 125 scenarios as 125 independent reasoning patterns.

Never use the test candidates to refine prompts or choose checkpoints. Validate
and improve prompts on smoke/validation data, freeze the experiment settings,
then independently review and freeze the final test data with content hashes.
Generation and audit commands do not perform that freeze or claim model quality.
