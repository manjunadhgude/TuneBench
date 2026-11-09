# Frozen v0.6 versus v0.7 semantic review comparison

This comparison tests a new decision pipeline with the **same primary Qwen3
weights, prompt, JSON grammar, and decoding**. It is not matched total compute:
v0.7 adds up to two semantic-review calls and checks proposal arithmetic.

## Freeze and authorship

Baseline inference is archived from `5559e30`. Candidate inference and the runner
were frozen at `eb4e227`, before the 40 portfolio-v5 questions were authored.
Dataset commit `e020ef8` adds those frozen questions without changing inference.
The same implementing assistant authored and reviewed the cases. There was no
independent blind review or human annotation. Source-before-data ordering limits
post-test tuning; it does not remove author bias or prove representative coverage.

The dataset contains 16 tool calls, 12 clarifications and 12 no-tool outcomes.
The manifest records all hashes, difficulty labels and exact prompt-overlap checks.
Reasoning cases include reference selection, requested refund scope, discounts,
fractions, and missing operands. Labels and prose rationales are frozen before
any generation. No label or source changes are allowed after observing outputs.

The primary sees only customer text and tool definitions. The reviewer sees only
customer text and the proposed decision. Case IDs, splits, difficulty, rationale,
and gold labels stay outside both prompts.

## Execution and preservation

`scripts/compare_semantic_versions.py` uses a standard-library parent and isolated
sequential workers. Candidate runs first, then baseline. It checks archived
baseline source, shared primary modules, model identity and SHA, first-request
prompt hashes, selected library versions, data hashes, and runner hash. Every
case is journaled durably with a checkpoint and an inflight marker. An uncertain
crash cannot silently rerun a generation. Resume accepts only verified completed
prefixes. Tools are disabled for decision scoring.

Both versions use four CPU generation threads, seed 42, greedy decoding, an
8192-token primary context, up to 256 generated tokens, and at most one primary
retry. The reviewer uses the same GGUF in a separate session, 4096-token context,
four threads, and at most 256 generated tokens. All primary/review outputs and
review usage are retained. Total generations and recorded elapsed time include
the extra review work. They are not a controlled standalone model-speed benchmark.

## Reproduce on already observed cases

The original output is immutable. A rerun uses a **new output directory** and is
reproduction, not another unseen test. Use Python 3.12 and the documented optional
CPU model installation. Set the GGUF path to an existing verified local file.
For the exact archived source/configuration, prepare separate directories:

```bash
mkdir -p /tmp/tunebench-v6-frozen /tmp/tunebench-v7-frozen
git archive 5559e30 | tar -x -C /tmp/tunebench-v6-frozen
git archive e020ef8 | tar -x -C /tmp/tunebench-v7-frozen
export TUNEBENCH_GGUF=/path/to/Qwen3-4B-Instruct-2507-Q4_K_M.gguf
.venv/bin/python /tmp/tunebench-v7-frozen/scripts/compare_semantic_versions.py \
  --legacy-root /tmp/tunebench-v6-frozen \
  --candidate-root /tmp/tunebench-v7-frozen \
  --data /tmp/tunebench-v7-frozen/datasets/portfolio-v5/holdout.jsonl \
  --legacy-model-path "$TUNEBENCH_GGUF" \
  --candidate-model-path "$TUNEBENCH_GGUF" \
  --output /tmp/tunebench-semantic-reproduction
```

Keep the current repository as the working directory so the runner can verify
its archived baseline with Git. The final release adds documentation, UI cost
presentation, and a lint-cache exclusion; use the archived candidate above for
the frozen comparison rather than silently treating every later file as frozen.

## Scoring and audit

Report original first-answer and accepted-final strict success separately. Every
case remains in both denominators, including invalid, blocked and failed results.
Break down tool calls, clarifications, and no-tool decisions. Count incorrect
accepted calls, correct first answers lost, repaired errors, and generation cost.
Clarification wording is contract-checked, not independently human-graded.

A separate computational audit reparses original text, recomputes canonical scores,
checks review records and Decimal calculations, and verifies freeze hashes. It is
performed by the same assistant and is not external independent validation.
A same-model reviewer can share the primary model's errors. Number presence and
correct arithmetic do not prove the expression selected the right facts.

The result measures small synthetic decision accuracy, not production traffic,
real transaction success, or comprehensive execution safety. Further tuning needs
development data and another untouched test cohort. No weights were trained.
