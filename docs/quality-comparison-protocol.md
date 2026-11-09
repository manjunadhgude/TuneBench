# Frozen v0.4 versus v0.5 quality comparison

This experiment compares complete systems on the same 40 new fictional support
requests. The baseline is the unchanged v0.4 source at `7498d78`, running the
previous Qwen2.5-1.5B-Instruct float32 snapshot. The candidate uses the frozen
v0.5 source and Qwen3-4B-Instruct-2507 Q4_K_M through llama.cpp.

Model weights, quantization, inference runtime, prompt, JSON constraints, grounding
and repair behaviour change together. The experiment measures their combined
effect. It does not isolate a model or prompt improvement, demonstrate fine-tuning,
or establish production reliability.

## Before generation

Use development cases for implementation and model selection. Keep the new test
cases and their review ledger away from implementers until the source is final.
The 40-case data must already have its frozen manifest and assistant semantic
review; that review is not independent human annotation.

`scripts/compare_quality_versions.py` verifies the archived baseline source against
`git archive 7498d78`. Both sources must have identical contracts, canonical tool
registry, prediction/task schemas and evaluator. Its parent imports only standard
library modules. Sequential worker processes insert their own source directory
before importing TuneBench and verify the imported package path. The candidate
worker does not initialize Torch or Transformers.

The protocol freezes both source maps, the runner, the data and manifest, both
models' verified assets, and selected installed library versions before any test
generation. The legacy snapshot is checked against its retained pinned download
manifest. The candidate GGUF is checked against its pinned upstream filename,
size and SHA-256; its publisher is Unsloth's conversion of the official Qwen model.
Neither backend downloads weights implicitly. Source, data or recorded-runtime
changes stop the run.

Shared limits are CPU execution with four generation threads, seed 42, greedy
decoding, one beam, at most 256 new tokens, repetition penalty 1.1, and at most one
repair. The legacy backend uses one inter-operation thread; the candidate uses
four batch threads and its recorded GGUF context settings. Native llama.cpp token
and sampling arguments are checked as well as normalized cross-runtime settings.
Different architectures, quantization and libraries make these system conditions,
not an identical-runtime model ablation.

## Run

Prepare the archived v0.4 checkout separately. The current environment already
contains `/tmp/tunebench-legacy-7498d78`. Run the following only after all source
and test-data review is complete, using a fresh output directory:

```bash
.venv/bin/python -u scripts/compare_quality_versions.py \
  --legacy-root /tmp/tunebench-legacy-7498d78 \
  --candidate-root /workspace/TuneBench \
  --data datasets/portfolio-v3/holdout.jsonl \
  --legacy-model-path /workspace/models/Qwen2.5-1.5B-Instruct/989aa7980e4cf806f80c7fef2b1adb7bc71aa306 \
  --candidate-model-path /workspace/models/Qwen3-4B-Instruct-2507-GGUF/a06e946bb6b655725eafa393f4a9745d460374c9/Qwen3-4B-Instruct-2507-Q4_K_M.gguf \
  --output artifacts/quality-comparison-v5
```

Workers run sequentially, candidate first and then the archived baseline. Both
sources and all data are frozen before either worker starts. The order is fixed
before observing test outputs; no decisions or labels pass between workers.
Offline flags prevent automatic Hugging Face downloads.
The installed distribution version and imported source package version are
recorded separately: both workers share a Python environment but import different
source trees. Every task must use the same canonical support tool registry.

## Records and scoring

Each completed request is appended and fsynced to its version's
`cases.partial.jsonl`. Its durable checkpoint records byte count, SHA-256 and case
count. The journal retains the original first answer, every permitted repair,
parsed outcomes, validation diagnostics, accepted final decision and latency.
Application code must not replace model answers with rules or reference labels.

All 40 examples remain in both score denominators, including invalid answers,
blocks and backend errors. The `raw-first.report.json` scores the first generated
answer; `final.report.json` scores only the accepted final decision. A block or
error becomes a null final outcome. Canonical schema validity is distinct from
strict decision correctness and parseable JSON. Clarification wording is checked
for contract validity rather than human-graded helpfulness.

No tool executes during this comparison. Fictional order-book policy, real
transaction success and execution safety are separate application checks. Runtime
errors are counted, reported and invalidate quality-readiness claims. Comparison
output records paired improvements and regressions for both stages, plus schema
validity counts. Request elapsed times include loading and permitted repairs;
their sum excludes idle pauses and is not process CPU-seconds or a controlled
hardware performance benchmark.

## Interrupted runs and review

Resume only the exact same invocation with `--resume`. Frozen inputs and model
hashes are rechecked. Completed journals must be contiguous, unmodified prefixes;
their original raw text must agree with parsed outcomes and accepted decisions.
Completed reports and accounting are recomputed before reuse. No completed case
is generated again.

An `inflight.json` marker is written before every request. If a process stops with
that marker present, generation may have happened without a durable response.
The runner refuses to rerun that case. A truncated journal or journal/checkpoint
mismatch likewise stops rather than silently changing evidence. Preserve such an
incomplete run and report the interruption; do not delete its marker to force a
rerun. Worker event records retain preserved-prefix hashes and interruption times.

After both systems finish, independently reparse the retained raw text, recompute
scores, check false blocks and incorrect accepted decisions, and report regressions
alongside gains. Keep the older results unchanged. Once these outputs are viewed,
the test is seen: further tuning requires development data and a new final test
set. This small assistant-authored sample cannot establish general accuracy or
real-world reliability, even if the observed score improves substantially.
