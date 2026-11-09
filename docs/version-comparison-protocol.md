# Frozen v0.3 versus v0.4 comparison

This protocol compares two complete systems on the same 20 new questions. It is
not a prompt ablation or a fine-tuning experiment. Both systems use the unchanged
pretrained Qwen2.5-1.5B-Instruct weights. The candidate changes its prompt, JSON
decoding constraints, grounding checks, and conditions for one bounded repair.

The archived v0.3 system is the unchanged `a6e143a` source. The candidate source
must be final before the first new test generation. Use only development data
for implementation, debugging, and a constrained-decoding smoke test. The fresh
test labels must not enter either system's prompts, code, or repair messages.

## Run

Create an archived source directory from the completed v0.3 commit, or use the
already prepared `/tmp/tunebench-legacy-a6e143a` directory. The runner verifies its
Python source, packaged resources, and project metadata against `git archive`.

```bash
.venv/bin/python -u scripts/compare_portfolio_versions.py \
  --legacy-root /tmp/tunebench-legacy-a6e143a \
  --candidate-root /workspace/TuneBench \
  --data datasets/portfolio-v2/holdout.jsonl \
  --snapshot /workspace/models/Qwen2.5-1.5B-Instruct/989aa7980e4cf806f80c7fef2b1adb7bc71aa306 \
  --output artifacts/portfolio-version-comparison
```

The parent uses only standard-library imports. Separate sequential subprocesses
import each version from its own `src` directory and check the imported package
path. The installed distribution version and imported source package version
are recorded separately, because both workers share one Python environment.

Both workers use CPU float32, four intra-operation threads, one inter-operation
thread, seed 42, greedy decoding, one beam, 256 maximum new tokens, repetition
penalty 1.1, and at most one repair. Offline flags prevent model downloads.
The full effective generation configurations must match. JSON constraints and
the model-independent grounding policy remain explicit system differences.

## Retained evidence

Before generation, `protocol.json` freezes hashes of both source trees, scoring
schemas, the runner, dataset and manifest, model assets and download manifest,
library versions, and shared settings. Dataset copies are retained in the
output directory. Both versions must have the same evaluator and scoring
schemas. Source or runtime changes stop the run.

Each completed request is appended and fsynced to its worker's
`cases.partial.jsonl`. The record includes all original model outputs, parsed
decisions, validation errors, bounded repairs, final accepted decision, and
latency. No tool executes in this comparison; mock execution is tested
separately. All 20 frozen cases stay in both score denominators, including
blocked outputs and runtime failures.

`raw-first.report.json` scores the first original output. `final.report.json`
scores only the accepted final decision; rejected decisions become null.
Neither stage replaces an answer with its reference label. The comparison
records paired strict-success improvements and regressions. Runtime errors
invalidate quality-readiness claims and are reported separately.

## Interrupted runs

Resume only the same output with the same command plus `--resume`. The runner
rechecks every frozen hash and library version. It validates journal order,
raw-to-parsed consistency, bounded repairs, and the durable journal checkpoint.
Completed cases remain byte-for-byte unchanged and are never generated again.
Completed reports are recomputed from their journals before reuse.

An `inflight.json` marker is saved before each request. If execution stops with
that marker still present, the response may have been generated without being
durably saved. The runner refuses to rerun that case. Preserve the incomplete
evidence and report the interruption; do not delete the marker or quietly start
the same benchmark again. A crash between journal and checkpoint writes is
also treated as incomplete evidence rather than silently repaired.

Active latency is the sum of saved per-request times, excluding idle pauses.
Worker events record preserved prefix sizes and hashes. No early stopping,
relabeling, selective exclusions, or test-driven source changes are allowed.
After viewing results, further changes require a new evaluation set.

These are 20 assistant-authored, assistant-reviewed cases, with no independent
human review. Scores describe this small test set and this CPU setup; they do
not establish production reliability, GPU speed, or gains from model training.
