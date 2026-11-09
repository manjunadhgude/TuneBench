# A 2–3 minute portfolio walkthrough

Start with the fast rules path and keep the backend label visible. It demonstrates
the application while reserving live model generation for a clearly labeled segment.

## Before presenting

From the repository root:

```bash
bash scripts/setup.sh --app
bash scripts/start_demo.sh
```

Open the app in your development environment's browser; it starts on port 8501.
For live Qwen3, complete the optional CPU model installation and verified GGUF
download in [README](../README.md) beforehand. Enter the file or its directory in
**Local model path**. Do not spend the walkthrough downloading weights.

Use the five fictional orders and fixed mock policy shown in the app. Amounts are
INR, and proposals never change an order or transfer money. Keep the completed
check output and experiment report available beside the demo.

## Main walkthrough

| Time | Action | Suggested narration |
| --- | --- | --- |
| 0:00–0:15 | Open **Playground** and choose **Quick demo**. | “TuneBench combines a tool-calling workbench with reproducible evaluation. This first run is deterministic Python, not an LLM.” |
| 0:15–0:35 | Run `Check the status of order TB-1001.` and inspect its trace. | “The decision names a tool and arguments. Application code validates the reference and dispatches a mock lookup.” |
| 0:35–0:55 | Run `Check the status of my order.` | “The reference is missing, so clarification is needed. No tool executes.” |
| 0:55–1:20 | Run `Propose a refund of 200 for order TB-1002 because the item arrived damaged.` | “The tool checks the fictional policy and remaining balance, then returns a simulated proposal without making a payment.” |
| 1:20–1:35 | Run `Execute a refund payment of 200 for order TB-1002 now. Do not create a proposal.` | “Real payment is unavailable. A proposal cannot be substituted for the requested operation.” |
| 1:35–2:00 | Open **Raw responses & validation trace**. | “Original text, schema/evidence checks, any repair and the final result stay separate. A valid non-executing answer receives advisory language diagnostics rather than an evidence retry into action.” |
| 2:00–2:30 | Open **Evaluation** and the latest completed matched report. | “Both versions must answer the same frozen questions. I report raw and accepted-final success, invalid outputs, regressions and generation cost. The earlier 7/20 result remains visible; I do not compare it directly with a score from different questions.” |
| 2:30–2:45 | End on architecture or tests. | “The project demonstrates local model integration, structured tool use, failure handling and measured improvement. No model fine-tuning has been performed.” |

The separate v0.4/v0.5 40-case comparison and score audit are still running at
this checkpoint. Until complete, use only clearly labeled historical results for
numbers. Practice 40/40 is tuned development coverage, not unseen accuracy.

After a clarification, submit the complete request including missing details.
Displayed history is not persistent model memory. **Start with an example** fills
an editable preset. If an example behaves differently, show its actual outcome;
do not relabel it or switch backends without saying so.

## Optional live-model segment

Choose **Live local Qwen** and run `Check the status of order TB-1001.` Show the
actual model identity and measured timing in the trace. The preferred profile is
Qwen3-4B-Instruct-2507 Q4_K_M through llama.cpp on CPU. Unsloth supplied the pinned
quantization of the official model; the project did not train it.

Explain that `strong-v4` and JSON grammar guide structure, then application checks
validate the decision. Real tool calls still need evidence. A schema-valid
clarification or no-tool answer cannot be retried into action because a heuristic
disagrees. At most one schema/tool-call evidence repair is allowed, and every
original attempt remains visible. A repaired final result does not improve the
first-answer score retroactively.

Timing depends on hardware, loading and output length. Show the observed duration
rather than promising a fixed CPU latency. If the call is blocked, show the failed
check. For a strict short recording, use a separate live clip or **Saved model
replay**; explicitly say replay is historical Qwen2.5 output, performs no new
generation and does not execute a tool.

## Evidence beside the demo

- [Architecture](architecture.md) and [quality comparison protocol](quality-comparison-protocol.md).
- Latest completed check output and [v0.5 release record](assets/release-checks-v0.5.json).
- [Earlier 7/20 final result and failure analysis](../artifacts/portfolio-version-comparison/README.md).
- Current screenshot/recording with backend identity and a visible decision trace,
  once the current browser check is complete.
- Historical media remains under [v0.4](assets/v0.4/browser-checks.json) and
  [v0.3](assets/v0.3/browser-checks.json), with its original version identity.

Gold-derived evaluator fixtures are useful for demonstrating accounting. Their
perfect score is not model accuracy. Assistant-reviewed fictional tests do not
establish production reliability or real transaction safety.
