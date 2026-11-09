# TuneBench

**A CPU tool-calling workbench with a local language model, validated mock tools and reproducible evaluation.**

TuneBench turns a fictional customer-support request into a tool call, a
clarification, or a no-tool decision. Its Streamlit app shows the original model
answer, validation, any repair and the simulated result. The evaluation framework
keeps wrong, invalid and blocked answers in its reports.

![TuneBench Playground: backend choice, request and inspectable result](docs/assets/tunebench-playground.png)

[Demo recording](docs/assets/tunebench-demo.webm) ·
[Architecture](docs/architecture.md) · [Interview guide](docs/interview-guide.md)

The screenshot and recording currently show the retained v0.4 demo; v0.5 browser
verification and replacement media are pending.

## Start the app

Use Python 3.12 for the tested, hash-locked Linux setup. Windows users can use WSL.
Codespaces, a GPU and an API key are not required for the quick demo:

```bash
git clone https://github.com/manjunadhgude/TuneBench.git
cd TuneBench
bash scripts/setup.sh --app
bash scripts/start_demo.sh
```

Use the existing checkout if you already have the repository. Setup creates `.venv`
and installs the locked app/development dependencies. The app starts on port 8501.
In **Playground**, choose **Quick demo**, enter a request and click **Run request →**.

- `Check the status of order TB-1001.`
- `Check the status of my order.`
- `Propose a refund of 200 for order TB-1002 because the item arrived damaged.`
- `Execute a refund payment of 200 for order TB-1002 now. Do not create a proposal.`

Requests are stateless. After a clarification, submit the complete request with
its missing details. **Evaluation** shows saved experiments; **Project** explains
the design and limitations.

## Three modes

| Mode | What runs |
| --- | --- |
| **Quick demo** | Deterministic Python rules and mock execution. This is not an LLM. |
| **Live local Qwen** | Actual CPU generation, preferably Qwen3-4B-Instruct-2507 Q4_K_M through llama.cpp; the verified legacy Qwen2.5 snapshot is also supported. |
| **Saved model replay** | Historical Qwen2.5 smoke responses. No new generation or tool execution. |

The live backend never downloads a model implicitly or falls back to rules.
Replay uses only its recorded questions. A rules result or replay must not be
presented as current model accuracy or live generation.

## Decision and execution

| Mock tool | Purpose |
| --- | --- |
| `get_order_status` | Read a fictional order's status |
| `check_refund_eligibility` | Check the versioned mock refund policy |
| `propose_refund` | Return a nonmutating simulated refund proposal |

Five fictional orders use INR balances and a fixed policy date, **9 November 2026**.
The policy checks a 30-day refund window, delivery conditions, remaining balance
and monetary precision. No tool contacts a customer system, changes an order or
transfers money.

The live v0.5 path is **request → Qwen3/strong-v4 → constrained JSON → complete
schema validation → tool-call grounding → mock execution or non-executing result**.
The guard checks the requested action, references, reasons and monetary evidence,
including exact calculations from supplied quantity/price or percentage/base facts.
A tool call can use at most one visible schema or evidence repair. Failed calls
are blocked; mock store and business-policy checks remain separate execution gates.

For a **schema-valid clarification or no-tool answer**, language-rule disagreements
are advisory. They cannot trigger an evidence retry that turns the answer into an
action. Schema errors can still use the bounded repair. The model generates every
attempt; application code never replaces its answer with a rules result. Advisory
notes and original outputs remain visible in the trace. These policies reduce
unnecessary intervention but do not prove that the model's decision is correct.

## Quality evaluation

The v0.5 system was selected using development data. Its first Qwen3 run scored
37/40 strict successes; after revising public prompt examples it scored 40/40 on
those **same practice cases**, with no repairs. This is tuned development coverage,
not unseen accuracy. [Practice captures](artifacts/quality-development-v5/)
retain the observed result.

The separate comparison runs frozen v0.4 and v0.5 on the **same 40 new fictional
questions**. Its sources, data and model assets were frozen before either run.
The full comparison and independent score audit are in progress; no new held-out
score is claimed at this documentation checkpoint. See the
[comparison protocol](docs/quality-comparison-protocol.md).

Model weights, quantization, runtime, prompt and guard change together. This is a
comparison of complete systems, not a prompt/model ablation or evidence of
fine-tuning. Raw first answers and accepted final decisions must both be reported.
All questions remain in the denominator, including failures. The stratified data
was authored and reviewed by assistants, with separate reviews blinded to the
implementation; it has no independent human annotation. Scoring disables tool
execution, so it does not measure real transaction success or establish production
reliability. Further tuning after test results requires a new final test set.

Report tool-call, clarification and no-tool performance separately. A high overall
score can hide correct tool calls being blocked. Accepted-call correctness, false
blocks and incorrect accepted calls matter alongside the total score.

### Earlier measured result: why v0.5 was needed

On the earlier matched 20-question test, the same Qwen2.5 weights produced:

| Decision evaluation | v0.3 | v0.4 |
| --- | ---: | ---: |
| Strictly correct first answer | 8/20 | 9/20 |
| Schema-valid first answer | 13/20 | 19/20 |
| Strictly correct accepted final decision | 2/20 | **7/20** |

v0.4 lost five correct first answers through guard/repair intervention and repaired
three errors. That weak 7/20 final result motivated the stronger CPU model and
revised guard policy. It remains visible in the
[historical comparison and audit](artifacts/portfolio-version-comparison/README.md).
It must not be compared directly with a score from different questions.

Other historical evidence is separate: the original v0.3 portfolio holdout scored
7/20 raw and 3/20 final; the first smoke scored 7/20; a paired 12-case development
prompt experiment changed 2/12 to 5/12. See the
[portfolio results](artifacts/portfolio-evaluation/README.md),
[smoke evidence](artifacts/baseline-smoke/README.md) and
[paired prompt experiment](artifacts/prompt-development-v2/README.md).

## Optional: run the actual CPU model

The preferred model is the public **Unsloth Q4_K_M GGUF conversion** of the official
`Qwen/Qwen3-4B-Instruct-2507`, licensed Apache-2.0. The GGUF publisher is Unsloth;
this is not an official Qwen GGUF release or a model trained in this project.
The pinned file is about 2.5 GB. The downloader and loader verify its exact size
and SHA-256 before use.

A Linux GCC C/C++ compiler is needed to build the optional CPU binding. With uv:

```bash
CC=/usr/bin/gcc CXX=/usr/bin/g++ CMAKE_BUILD_PARALLEL_LEVEL=4 \
  CMAKE_ARGS='-DCMAKE_C_COMPILER=/usr/bin/gcc -DCMAKE_CXX_COMPILER=/usr/bin/g++ -DGGML_CUDA=OFF -DGGML_NATIVE=ON -DLLAMA_CURL=OFF' \
  uv pip install --python .venv/bin/python 'llama-cpp-python==0.3.36'
.venv/bin/python scripts/download_gguf_model.py \
  --output ../models/Qwen3-4B-Instruct-2507-GGUF/a06e946bb6b655725eafa393f4a9745d460374c9
```

In **Live local Qwen**, enter the downloaded GGUF file or its containing directory
in **Local model path**. The first native-library build can take a few minutes.
Allow additional RAM for context and runtime beyond the weight file; timing and
memory depend on hardware and request length. The backend uses zero GPU layers,
four generation threads, an 8192-token context and at most 256 new tokens per
attempt. It uses `strong-v4`, ChatML and llama.cpp JSON-schema grammar, followed by
complete application validation. No Hugging Face token or paid API is required.

The legacy PyTorch/Qwen2.5 setup remains in the
[original model evidence](artifacts/baseline-smoke/README.md). No GPU training or
trained-adapter evaluation has been performed. Optional LoRA/QLoRA code is future
experiment support.

## CLI and checks

```bash
.venv/bin/tunebench orders
.venv/bin/tunebench assist --message 'Check the status of order TB-1001.'
.venv/bin/tunebench evaluate --gold GOLD.jsonl --predictions PREDICTIONS.jsonl \
  --output REPORT.json
bash scripts/check.sh
```

The current v0.5 local suite passes **469 tests**, lint, formatting and CLI/data
workflows. Core-only checks pass 459 with five optional modules/checks skipped.
Fresh app setup passes 465 tests with four optional checks skipped; its documented
launch serves the app. A standalone v0.5 wheel also runs outside the checkout.
Current browser verification remains pending. See the
[v0.5 release record](docs/assets/release-checks-v0.5.json); historical v0.4 checks
remain in [their retained record](docs/assets/release-checks-v0.4.json).
CI runs CPU checks without model downloads or a GPU. Gold-derived fixtures test
the evaluator; their perfect score is not model accuracy.

## Explore and present

| Path | What to inspect |
| --- | --- |
| `app.py` | Playground, Evaluation and Project tabs |
| `src/tunebench/` | Shared assistant, grounding, mock tools, local backends and scoring |
| `datasets/portfolio-v1/` | Earlier 40-development / 20-holdout data |
| `datasets/portfolio-v2/` | Evaluated earlier 20-case matched comparison |
| `datasets/portfolio-v3/` | Frozen, separately reviewed 40-case comparison |
| `tests/` | Offline unit, integration and UI checks |
| `artifacts/` | Original outputs, protocols, metrics and failures |
| `docs/` | Architecture, walkthrough and interview preparation |

Use the [walkthrough](docs/demo-script.md), [interview guide](docs/interview-guide.md),
[resume wording](docs/resume-bullets.md) and [completion checklist](docs/portfolio-completion.md).
Describe contributions you understand and can demonstrate, including assistance
used during development. The original 1,250-record synthetic research benchmark
remains candidate/unreviewed; it is separate from these portfolio datasets.
