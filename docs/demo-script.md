# A 2–3 minute portfolio walkthrough

Present the fast rules path first. It demonstrates the application without waiting
for model generation. Keep the backend label and trace visible so the audience can
see which component produced each decision.

## Before presenting

From the repository root, install the app dependencies and launch the interface:

```bash
bash scripts/setup.sh --app
bash scripts/start_demo.sh
```

Open the shared browser provided by your development environment. The app starts
on port 8501 by default. Start it before recording and keep the automated check
result available in another terminal.
Do not download model weights during the short walkthrough. Live Qwen is optional
and requires the local snapshot and model dependencies; recorded output can be
shown without implying that it was generated live.

Use the five fictional demo orders and the fixed mock policy shown in the app.
All monetary values in this demo are INR. A refund proposal is a simulation and
does not change the order or transfer money.

## Main walkthrough

| Time | Action | Suggested narration |
| --- | --- | --- |
| 0:00–0:15 | Open **Playground** and choose **Quick demo** in **Run mode**. | “TuneBench combines a tool-calling assistant demo with a reproducible evaluation framework. This first run uses deterministic Python rules, not an LLM.” |
| 0:15–0:35 | Enter `Check the status of order TB-1001.` in **Your request** and click **Run request →**. Open the result and trace. | “The request becomes a structured decision. The application validates it, checks that the reference is grounded in the request, and calls a mock status tool.” |
| 0:35–0:55 | Submit `Check the status of my order.` | “The order reference is missing, so the assistant asks for clarification instead of inventing an ID. No tool executes.” |
| 0:55–1:20 | Submit `Propose a refund of 200 for order TB-1002 because the item arrived damaged.` | “This is a simulated proposal. The tool checks the order, reason and remaining refundable amount. It returns a reproducible result without changing the order or making a payment.” |
| 1:20–1:35 | Submit `Execute a refund payment of 200 for order TB-1002 now. Do not create a proposal.` | “Actual payment execution is outside the registered tools. The assistant must not substitute a proposal and present it as a completed payment.” |
| 1:35–2:00 | Expand a trace showing decision, validation, execution and timing. | “The result is inspectable. Raw generated text, validation failures, any visible repair attempt, and the final application result are separate stages.” |
| 2:00–2:30 | Open **Evaluation** and show the retained experiment results. | “I also measured the actual Qwen model. The first smoke run scored 7/20 strict successes. On a different 12-case paired development set, a prompt revision changed 2/12 to 5/12, with four gains and one regression. These small sets do not establish general accuracy.” |
| 2:30–2:45 | End on the architecture or tests. | “The portfolio demonstrates structured tool use, failure handling, tests and honest evaluation. Fine-tuning support is implemented, but no model training has been performed.” |

The assistant evaluates one request at a time. After a clarification, submit the
complete request including the missing details; displayed history is not persistent
model memory. **Start with an example** can fill a preset into the editable request.

If an example behaves differently, show the actual result and investigate it. Do
not relabel a failed request or switch backends without telling the audience.

## Optional live-model segment

Choose **Live local Qwen** in **Run mode** and submit one short supported request such as
`Check the status of order TB-1001.` Make the live-model label visible. Explain that
this loads and runs the actual local model; generation can take tens of seconds on
a CPU, in addition to startup. Show the measured duration from that run rather than
promising a fixed latency. If the output is blocked, explain the failed check.

In v0.4, explain that `strong-v3` and JSON token constraints guide output structure;
full schema and request-evidence checks still run afterward. These changes do not
train or fine-tune the model.

A repair attempt, when enabled, is limited to one and visible. It can follow a
schema failure or an explicit request-evidence mismatch. Preserve the first output,
show the feedback and explain why another attempt was made. The application does
not rewrite the model answer. A corrected final application response does not
raise the historical one-attempt model score.

The fresh v0.3/v0.4 comparison is pending at this checkpoint. Use completed retained
reports for numbers, and name the data and version shown. Do not present older
scores as results from the revised live pipeline.

For a strict 3-minute recording, put live generation in a separate clip or choose
**Saved model replay**, select an existing smoke question, and click **View recorded
response**. Replay uses immutable historical inputs, does not accept a new request,
and does not execute a tool. State that it is not a new inference run and its
source timing is historical.

## Evidence to keep beside the demo

- [Architecture diagram](architecture.md).
- [Initial real-model smoke results](../artifacts/baseline-smoke/README.md).
- [Paired prompt experiment and regressions](../artifacts/prompt-development-v2/README.md).
- [Historical v0.3 portfolio results](../artifacts/portfolio-evaluation/README.md).
- Latest completed automated check output; do not substitute an older count.
- Screenshot or video with backend identity and at least one visible decision trace.

Gold-derived evaluator fixtures are useful for explaining the scoring pipeline,
but their 20/20 controlled result is not model performance.

## Suggested media captions

Use these captions only for media that actually shows the corresponding behavior:

- **Rules demonstration:** “Deterministic Python backend: validated mock order lookup
  and execution trace; no model inference.”
- **Clarification:** “Missing order reference: the assistant requests information and
  does not execute a tool.”
- **Refund proposal:** “Simulated INR refund proposal with policy checks; no order
  mutation or real payment.”
- **Live model:** “Actual local Qwen generation on CPU; raw output and measured timing
  are visible.”
- **Replay:** “Recorded Qwen output from a retained experiment; replay does not run
  inference again.”

Save shareable media under `docs/assets/` with descriptive filenames. Keep terminal
paths, personal data and unrelated windows out of the recording. Root-level setup
instructions remain the source for exact commands and optional dependencies.
