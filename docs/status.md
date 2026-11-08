# Implementation and research status

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
3. Enable public Hugging Face model access and verify model revision/license/runtime.
   The actual network probe was denied by the cloud proxy; secret credentials were
   neither requested nor needed for the public model.
4. Run and inspect minimal/strong baselines using train/validation during development.
5. Obtain a CUDA GPU, test the real training stack, train an adapter, and evaluate with
   the matched strong-prompt and inference policy.
6. Run the final paired comparison once, inspect regressions, and report quality,
   latency, memory, and measured training cost. No positive or negative training
   conclusion can be drawn from synthetic fixture scores.

The offline tests verify code paths with controlled generation and tokenizer test
doubles. They do not establish that the optional Hugging Face backend or a real GPU
training run succeeds. No model or adapter was downloaded, trained, or fabricated.

## Continuing development

Run `bash scripts/setup.sh`, then `bash scripts/check.sh`. Keep progress in tracked
source/docs rather than relying on an untracked Codespace or external chat. Inspect
the Git diff before committing, then push reviewed source changes to preserve progress
beyond the local development session.
