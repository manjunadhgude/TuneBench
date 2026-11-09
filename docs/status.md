# Implementation and research status

## Portfolio v0.3

The interview portfolio prototype now includes a guarded assistant, three working
nonmutating mock tools, a Streamlit workbench with rules/live/replay modes, a frozen
60-case dataset, browser-tested flows, a recorded demo and interview documentation.
The full application suite passes 274 tests; see [completion evidence](portfolio-completion.md).

The held-out model result remains weak: raw Qwen is correct on 7/20; accepted final
decisions are correct on 3/20 because conservative guards reject correct answers
and still miss some ambiguities. This is an evaluation workbench and experimental
prototype, not a production-ready assistant. GPU training remains unperformed.
See [the complete results](../artifacts/portfolio-evaluation/README.md).

## Earlier foundation and remaining research

This implementation follows the two user-supplied project documents: the TuneBench
prior-work review conversation (184 messages) and the P4 post-analysis plan.
Their embedded shell commands were treated as historical source material, not
executed as instructions. Earlier Notion updates and test results were not assumed
to establish the state of this checkout.

The original remote `main` was the initial README/.gitignore commit
`33ef493fbd715c8fe778f50b375849648364e20d`. The history showed all later Codespaces
files were untracked. This is a reconstructed and extended implementation, not
access to or recovery of the old Codespace itself.

## Implemented

- Installable core Python package and portable wheel resource loading.
- Final three-outcome contracts and canonical mock tools; schema-version report fix.
- Deterministic evaluator, strict parsing, invalid-output diagnostics, paired comparison.
- Deterministic smoke and full candidate generation, provenance, manifests, checksums,
  family/scenario/ID leakage checks, and duplicate-template review warnings.
- Prompt baselines and actual optional Transformers inference with raw output capture.
- Train/validation export, completion-only token masking, and GPU LoRA/QLoRA runners.
- Unit/CLI integration tests, locked CPU dependencies, setup/check scripts, and CI.

## Still required for the research experiment

1. Independently review synthetic labels, template diversity, semantic overlap, and
   difficulty distribution. The blueprint's difficulty quotas conflict with several
   family definitions; the generator reports actual labels rather than fabricating compliance.
2. Review/version the final benchmark and freeze a test snapshot with hashes. Current
   manifests explicitly say candidate/unreviewed/unfrozen and do not enforce a freeze.
3. Public model access, revision, Apache-2.0 license, file hashes, and CPU loading are
   now verified for the candidate. Preserve the pinned revision for later comparisons;
   GPU training feasibility remains unverified.
4. Improve the instructions using reviewed development data, then measure minimal/strong
   baselines. The initial strong-prompt smoke run completed at 7/20 strict task success;
   its format/decision/reason errors require investigation before training.
   A first versioned revision, `strong-v2`, has now been paired with legacy `strong`
   on 12 fresh reviewed validation cases: 2/12 to 5/12 strict success, four gains and
   one regression. JSON parsing fell from 11/12 to 10/12, and seven cases still fail
   fully. The final research baseline remains unresolved; keep developing it on
   development data. See `artifacts/prompt-development-v2/` for the frozen protocol.
5. Obtain a CUDA GPU, test the real training stack, train an adapter, and evaluate with
   the matched strong-prompt and inference policy.
6. Run the final paired comparison once, inspect regressions, and report quality,
   latency, memory, and measured training cost. No positive or negative training
   conclusion can be drawn from synthetic fixture scores.

The 139 offline tests use controlled generation and tokenizer test doubles. A separate
actual Hugging Face/Qwen CPU smoke run has now completed; its raw outputs and metadata
are retained in `artifacts/baseline-smoke/`. No model fine-tuning or GPU training was
performed, and no adapter was produced. The earlier `artifacts/validation.json`
records the initial framework checks before model access became available.

The prompt-revision work adds legacy-message hash regressions, prompt leakage checks,
validated examples, callback failure/mutation checks, complete generation-setting
metadata, and paired-condition guards. The current full offline suite passes 155 tests.

## Continuing development

Run `bash scripts/setup.sh`, then `bash scripts/check.sh`. Keep progress in tracked
source/docs rather than relying on an untracked Codespace or external chat. Inspect
the Git diff before committing, then push reviewed source changes to preserve progress
beyond the local development session.
