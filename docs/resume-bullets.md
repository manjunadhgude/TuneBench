# Resume and portfolio wording

Choose bullets that describe work you understand and can demonstrate. Adapt the
verbs to your actual contribution, and disclose development assistance when asked.
Do not imply independent authorship of components you have not studied or modified.

## Suggested project description

**TuneBench — Tool-calling assistant and evaluation framework**
Python, JSON Schema, Streamlit, pytest, Hugging Face Transformers,
lm-format-enforcer; optional PEFT/LoRA training support.

A customer-support simulation with explicit tool-call, clarification and no-tool
outcomes, an inspectable execution trace, and reproducible model evaluation.

## Select two or three bullets

- Implemented a Python tool-calling workflow with structured output validation,
  request-grounding checks, and three nonmutating mock customer-support tools;
  exposed decisions and execution traces in a Streamlit demo.
- Integrated JSON-constrained local model generation with complete schema checks,
  request-evidence validation and at most one visible repair, preserving the model's
  original output and distinguishing raw accuracy from accepted final decisions.
- Built deterministic evaluation for outcome choice, tool selection, arguments,
  clarification and strict task success, retaining malformed and missing responses
  in per-example diagnostics.
- Added versioned prompts and a reproducible paired Qwen2.5-1.5B-Instruct CPU
  experiment with saved raw outputs, inference settings, regression analysis and
  family-cluster confidence intervals.
- Developed synthetic-data generation and cross-split leakage checks, portable
  packaged contracts, and offline unit/CLI integration tests.
- Prepared completion-only training data and optional LoRA/QLoRA runners, with
  explicit separation between implemented training support and unperformed GPU runs.

If your contribution was integration and learning rather than writing a component
from scratch, use wording such as “Integrated and tested” or “Extended an
AI-assisted implementation with …”, followed by a concrete change you made.

## Optional measured detail

Use a number only with its scope and linked evidence. A measured statement is:

> Compared two Qwen CPU system versions on the same 20 frozen fictional cases:
> strict first-answer success changed from 8/20 to 9/20, schema validity from 13/20
> to 19/20, and accepted final success from 2/20 to 7/20; retained raw responses,
> regressions and an independent computational score audit.

Evidence: [matched system comparison](../artifacts/portfolio-version-comparison/README.md).
This changes several pipeline components together with unchanged model weights;
it is not a prompt-only result or fine-tuning benefit. v0.4 still falls from 9/20
raw successes to 7/20 accepted finals, and the small assistant-authored set does not
establish general improvement or production accuracy.

Older evidence remains separate: the [paired prompt experiment](../artifacts/prompt-development-v2/README.md)
changed 2/12 to 5/12 on development cases, with four gains and one regression. The
[7/20 smoke result](../artifacts/baseline-smoke/README.md) used different questions.
Do not describe 20/20 gold-derived evaluator fixtures as model accuracy or compare
scores across different datasets as a matched improvement.

For a test count, quote the exact count from the latest completed check run and
link its evidence. Re-run `bash scripts/check.sh` before submitting the project;
do not copy an old count from a chat or use a placeholder as a measured result.

## Claims this evidence does not support

Do not write “fine-tuned Qwen”, “improved accuracy with LoRA”, “production-ready
refund agent”, “deployed payment automation”, or “high-accuracy AI assistant”.
There has been no model fine-tuning, no real payment integration, and no production
reliability study. Describe the working portfolio implementation and the actual
experiments instead.

Link the repository, the [architecture](architecture.md), the
[demo walkthrough](demo-script.md), and the measured experiment reports in a
portfolio entry. A clear failure analysis is useful engineering evidence.
