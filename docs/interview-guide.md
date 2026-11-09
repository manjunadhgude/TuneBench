# Interview guide

## A short introduction

“TuneBench is a CPU-based tool-calling workbench. It converts a customer-support
request into a tool call, clarification, or no action. I integrated structured
local-model generation, model review, arithmetic validation, mock business policy,
and reproducible evaluation. The app lets us inspect every original answer and
retry. It uses fictional data and does not make real payments.”

Adapt that wording to your actual contribution. Explain AI assistance honestly;
only claim work you can explain and demonstrate.

## Why keep the 7/20 result?

It is a real historical failure, on a different 20-question cohort. The early
model made mistakes, and the conservative guard also rejected correct answers.
The stronger CPU model improved a separate 40-case matched comparison from
16/40 to 32/40 accepted final decisions, but the guard remained weak. A further
regex revision produced no overall gain and only 1/16 correct final tool calls
on a harder cohort. That evidence motivated the new review/calculator pipeline.

Show the [latest matched results](../artifacts/semantic-comparison-v7/README.md).
Do not say “accuracy improved from 7/20 to the latest score”: those are different
questions. Explain the same-test baseline, added compute, remaining failures,
and small assistant-authored dataset. A careful diagnosis and honest measurement
are stronger evidence than hiding an early result.

## Concepts to explain without memorizing

- **Tool calling:** the model proposes a named function and arguments; application
  code validates and dispatches it. Here, there are exactly three mock tools.
- **Structured output:** JSON grammar guides generation. Full schema validation
  checks the result. Valid JSON can still name the wrong tool or amount.
- **Clarification:** request missing required facts instead of inventing them.
  An unclear action uses a null target; missing arguments use the chosen tool.
- **Model review:** a second call checks the first decision against customer facts.
  The same model can repeat its own mistakes. It is not a safety guarantee.
- **Calculator:** restricted AST plus Decimal verifies arithmetic independently.
  The model must still choose the correct source numbers and requested scope.
- **Bounded retry:** at most one primary retry; preserve the first answer and
  review. Never replace model output with a gold label or deterministic answer.
- **Execution policy:** fictional store lookup, balance, date window, and monetary
  precision remain deterministic checks before a mock operation.
- **Evaluation:** gold labels are excluded from generation. Score all cases,
  including failures, and distinguish raw-first from accepted-final correctness.

## Common questions

**Why no GPU?** A roughly 2.5 GB Q4_K_M Qwen3 GGUF runs through llama.cpp on CPU.
Live review needs additional context memory; use at least 16 GB RAM. Quick demo
has no model requirement. Quantization and hardware affect quality and latency.

**Did you fine-tune it?** No. These experiments use downloaded pinned weights.
LoRA/QLoRA runners exist as future experiment support; no adapter was trained.

**Why no RAG or vector database?** The task chooses from three tools using facts
already in the message. Retrieval is unnecessary for this bounded task.

**What makes the comparison fair?** Both versions receive the same frozen 40
questions and primary prompt/model. All outputs are retained. The newer pipeline
uses extra review calls, so total compute is not matched and is reported.

**Can the review accept a wrong call?** Yes. It is probabilistic and shares the
primary model's weaknesses. Even a correctly calculated expression can use the
wrong scope. Inspect the actual failures rather than claiming perfect safety.

**Are the tests independent?** The latest cases were written after code freeze,
but by the implementing assistant. No independent blind or human annotation was
performed. This limits the strength of the result.

**What do 553 passing tests establish?** Software behavior under tested scenarios:
contracts, scoring, calculator boundaries, mock policy, CLI and UI. They are not
553 model questions or a production reliability guarantee.

## Practice before applying

Run the demo, explain a calculator boundary test, trace one primary/review/retry
record, and discuss one remaining model failure. Read
[architecture](architecture.md), [demo script](demo-script.md), and
[resume wording](resume-bullets.md). Make a small change yourself and explain it.
