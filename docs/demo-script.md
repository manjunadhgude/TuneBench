# A 2–3 minute interview demo

Start with `bash scripts/setup.sh --app` and `bash scripts/start_demo.sh`. Open
port 8501. Quick demo needs no GPU, model, or API key. For live inference, install
the optional CPU model as described in [README](../README.md) before presenting.

| Time | Action | Explain |
| --- | --- | --- |
| 0:00–0:20 | Choose Quick demo; run `Check the status of order TB-1001.` | This first example uses deterministic rules, not an LLM. The shared app pipeline validates a mock lookup. |
| 0:20–0:40 | Run `Check the status of my order.` | Missing required facts trigger clarification. Follow-ups must include the complete request. |
| 0:40–1:00 | Run `Propose a refund of 200 for order TB-1002 because the item arrived damaged.` | A proposal is simulated and checks fictional policy; it never transfers money. |
| 1:00–1:20 | Run `Execute a refund payment of 200 for order TB-1002 now.` | Actual payment is unsupported. Available tools cannot be substituted for a different requested action. |
| 1:20–1:50 | Show a live Qwen trace or clearly labeled saved replay | Live Qwen3 uses JSON constraints, model review, a calculator for proposals, and at most one retry. Replay is historical output without fresh inference. |
| 1:50–2:25 | Open Evaluation | Compare versions on the same questions. Report first and final accuracy, correct tool calls, mistakes, and added generation cost. |
| 2:25–2:45 | Explain one failure and a test | The old 7/20 exposed model and guard weaknesses. The calculator verifies arithmetic, but model review can still choose the wrong facts. |

The preferred live model is Unsloth's Q4_K_M conversion of Qwen3-4B-Instruct-2507
through llama.cpp on CPU. It was not trained by this project. Expect loading and
CPU latency; show the measured timing. A live response is not guaranteed to be
correct. If it is blocked or wrong, show that outcome and its trace.

Use [the latest completed results](../artifacts/semantic-comparison-v7/README.md),
not tuned development scores. The latest test cases were authored/reviewed by the
same implementing assistant after source freeze, with no independent human review.
The newer version uses extra model calls, so total compute is not matched.

Keep [architecture](architecture.md), [interview questions](interview-guide.md),
and [release evidence](assets/release-checks-v0.7.json) nearby. Historical media
and results remain separately labeled. No fine-tuning or production payment
system has been completed.
