# Resume and portfolio wording

**TuneBench — CPU tool-calling assistant and evaluation workbench**
Python, Streamlit, JSON Schema, llama.cpp, Qwen3, Decimal, pytest.

Choose two or three bullets you can demonstrate. Adapt verbs to your actual
contribution and disclose development assistance when asked.

- Integrated a quantized local Qwen3 model with structured tool decisions, full
  schema validation, bounded model review/retry, and inspectable raw traces.
- Added restricted AST/Decimal refund arithmetic and three nonmutating mock tools
  with deterministic order, balance, date-window, and precision checks.
- Built paired evaluation with frozen model/source/data hashes, durable raw-output
  journals, per-outcome metrics, and separate first-answer/final decision scores.
- Exposed rules demo, live CPU inference, historical replay, and measured results
  in a Streamlit interface; verified contracts, CLI, mock tools, and UI behavior.

For a measured bullet, quote the actual same-cohort counts and limitations from
[the latest report](../artifacts/semantic-comparison-v7/README.md). Do not mix
scores from different test sets. The earlier 7/20 result remains historical
failure evidence, not a hidden result. Model review adds compute and latency.

For software tests, the completed source suite passes 553 checks. Link the
[release record](assets/release-checks-v0.7.json) and re-run checks before applying.
Test count is not model accuracy. Perfect gold-derived evaluator fixtures are
software tests only.

Do not claim fine-tuning, a trained LoRA adapter, independent human evaluation,
production reliability, real refunds, or independent authorship of work you do
not understand. The model was downloaded; optional training support has not been
run. “Integrated and tested an AI-assisted implementation” is accurate when that
matches your contribution.
