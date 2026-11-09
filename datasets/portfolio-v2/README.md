# Portfolio-v2 blind holdout

This frozen set contains 20 new, fictional decision scenarios for one paired
comparison of the v0.3 and v0.4 pipelines. It contains eight tool calls, six
clarifications, and six no-tool decisions. Difficulty is six easy, nine medium,
and five hard cases, based on the reasoning required by each case.

Every task uses schema 3.0.0 and embeds the canonical three-tool registry. All
four allowed refund reasons appear across the tool calls. Facts needed for gold
decisions are supplied in the prompts; no demo business policy, real order data,
order-ID pattern, refund cap, currency conversion, or tool execution is assumed.

Frozen file: `holdout.jsonl`, 36,339 bytes.

SHA-256: `7fa5a23ae5dee8f32b51df5167a07e3b2c56dcafae8ac3ef6d608ac7caabe9be`

`manifest.json` records that hash, counts, families, review status, and limitations.
Both source versions and this exact data must be frozen before inference. Evaluate
all 20 cases once per version, preserving raw outputs and failures under matched
non-pipeline conditions. Do not use holdout cases as implementation or unit-test
fixtures, and do not tune prompts or grounding rules against their predictions.
Any later data or label revision requires a new version and hash.

All 20 scenarios were individually authored and semantically reviewed by the
assistant before portfolio-v2 model inference. The author did not inspect the
v0.4 grounding implementation, v3 prompt instructions, or portfolio-v2 model
predictions. Prior project failure categories were known and informed broad domain
coverage; the cases were not designed against an implementation. This is not human
review or independent human annotation.

The prompts, identifiers, scenario IDs, and descriptive family IDs are new. Exact
normalized prompts and identifier/number-normalized templates were checked against
the available prior smoke, paired-practice, and portfolio-v1 prompt datasets with
no overlap. No prediction file or 1,250-candidate research final-test set was
opened for curation. Broad concepts still recur, so this small curated set does
not establish representative traffic coverage or entirely novel reasoning.

The [semantic review ledger](../../docs/portfolio-v2-review.md) records all 20 gold
decisions and their supporting facts. Pipeline implementers should leave the
holdout and its ledger unread until source freeze. Dataset validation establishes
contract integrity; it does not claim any model performance or factual quality
of generated prose answers. Keep earlier smoke/development/portfolio scores as
separate historical measurements.
