# Implementation and research status

## Portfolio v0.4 checkpoint

The current source extends the CPU tool-calling workbench with `strong-v3`,
optional `lm-format-enforcer` JSON-constrained generation, evidence checks for
references/corrections and exact derived amounts, and at most one visible repair
for a schema or explicit request-evidence failure. Complete post-generation
validation remains required. The model generates every attempt; application code
never rewrites its answer into a rules result.

The app still offers clearly labeled deterministic rules, actual local Qwen and
saved replay modes. Three nonmutating mock tools provide fictional order lookup,
refund eligibility and refund proposals. No real payment or customer system is
connected, and no GPU or paid API is needed for the fast rules demo.

The fresh matched v0.3/v0.4 20-case model comparison and final v0.4 release checks
are pending at this documentation checkpoint. No new quality score or current
browser-verification claim is made here. See the
[completion checklist](portfolio-completion.md) for the evidence required before
marking the revised portfolio checkpoint complete.

## Historical portfolio v0.3 evidence

The preceding checkpoint included the guarded assistant, Streamlit workbench,
frozen 40-development/20-holdout dataset, browser-tested flows, demo recording
and interview documentation. Its full app suite passed 274 tests.

On that holdout, raw Qwen first attempts were strictly correct on **7/20**;
accepted final decisions were correct on **3/20**. Conservative guards rejected
four correct contextual or derived answers and still accepted one incorrect
ambiguous-reference decision. This motivated the revised evidence checks. The
old cases and results remain unchanged and must not be called unseen again.
See the [complete v0.3 results](../artifacts/portfolio-evaluation/README.md).

Earlier experiments remain separate: the initial smoke run scored **7/20**,
and a paired 12-case prompt-development run changed **2/12 to 5/12**, with four
gains and one regression. Different datasets cannot support a direct before/after
accuracy claim. None of these runs establishes production reliability or a
fine-tuning benefit.

## Implemented foundation

- Installable Python package, CLI, portable packaged contracts and wheel resources.
- Explicit tool-call, clarification and no-tool contracts for three mock tools.
- Strict parsing, deterministic scoring, per-example diagnostics and paired reports.
- Versioned prompts and actual optional Transformers CPU inference with raw output.
- Synthetic candidate generation, provenance, manifests, checksums and structural
  family/scenario/ID leakage checks.
- Train/validation export, completion-only token masking and optional GPU LoRA/QLoRA
  runners; these are training support, not evidence that a model was trained.
- Offline tests, dependency locks, setup/check scripts, CI and a Streamlit interface.

The revised system comparison changes prompt, constraints, guard and repair
trigger together. Both versions must use the same fresh cases, pinned model,
CPU settings, token budget and maximum repair count. Report raw first-attempt
quality separately from final accepted decisions. It is a system-version
comparison, not a prompt-only ablation.

## Research work outside the portfolio checkpoint

1. Independently review labels, semantic overlap, template diversity and difficulty.
   Portfolio data is assistant-authored/reviewed; it is not independently human
   annotated. Structural leakage checks cannot establish semantic independence.
2. Review and freeze the larger research benchmark. Its 1,250 synthetic records
   remain candidate/unreviewed/unfrozen; this is separate from portfolio snapshots.
3. Establish a credible baseline on development data and preserve fresh final test
   data for frozen comparisons. Inspect errors and regressions as well as gains.
4. Obtain and test a CUDA training environment only if pursuing the separate
   fine-tuning experiment; train an adapter and measure it under matched conditions.
5. Report quality, latency, memory and actual training cost. No adapter has been
   produced, and no positive or negative training conclusion is supported yet.

Authentication, real integrations, operational monitoring and production deployment
are outside the present fictional customer-support simulation.

## Origin and continuing development

The implementation follows the user-supplied TuneBench review conversation and
P4 post-analysis plan. Embedded shell commands were treated as historical source
material, not executed as instructions. The original remote `main` contained only
the initial README/.gitignore commit
`33ef493fbd715c8fe778f50b375849648364e20d`; the available history indicated later
Codespaces files were untracked. This is a reconstructed and extended
implementation, not recovery of the old Codespace.

Keep current progress in tracked source, docs and raw evidence. Run
`bash scripts/setup.sh --app`, then `bash scripts/check.sh`, inspect the diff and
preserve reviewed changes in Git. Historical validation files and test counts do
not establish that the latest code has passed. Use the
[interview guide](interview-guide.md) and [demo script](demo-script.md) to study and
present only behavior and contributions you can explain.
