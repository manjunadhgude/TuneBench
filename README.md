# TuneBench

**A CPU-based GenAI tool-calling workbench with model review, refund arithmetic checks, and reproducible evaluation.**

A fictional customer-support request becomes a tool call, a clarification, or a
no-tool decision. The app shows the original model output, validation, any retry,
and the simulated result. No GPU, paid API, or real customer account is needed.

![TuneBench Playground](docs/assets/tunebench-playground.png)

[Demo recording](docs/assets/tunebench-demo.webm) · [Architecture](docs/architecture.md) ·
[Interview guide](docs/interview-guide.md)

The recording shows v0.7. The v0.7.1 patch changes decision review policy; its
live regression evidence is recorded separately below.

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
| Quick demo | Deterministic Python rules; instant, no LLM |
| Live local Qwen | Verified Qwen3-4B-Instruct-2507 Q4_K_M on CPU; legacy Qwen2.5 also supported |
| Saved model replay | Historical Qwen2.5 answers to fixed inputs; no new generation or execution |

## How a live request works

1. Qwen generates one of three structured decisions using a JSON grammar.
2. Python strictly parses the output and checks its complete JSON Schema.
3. Valid no-tool and clarification decisions finish immediately, without review
   or retry. For Qwen3 tool calls, the same model separately reviews the call
   against the customer message. This review is probabilistic and can make mistakes.
4. Refund proposals additionally require a bounded arithmetic expression. A Python
   AST interpreter computes it using Decimal and compares it with the proposed
   amount. It accepts only supplied numeric operands and restricted operators;
   the model still has to select the correct facts and scope.
5. A schema error or rejected tool call can receive one primary retry. Every primary answer and
   review remains visible; application code never substitutes a rules answer.
6. Accepted tool calls pass the fictional store's policy checks before simulation.

The three tools retrieve order status, check refund eligibility, and prepare a
simulated refund proposal. Five demo orders use INR balances, a 30-day policy,
and a fixed policy date of **9 November 2026**. Proposals never change balances
or transfer money. Unknown orders and invalid policy requests are blocked.

Qwen3 can use at most two primary generations and two review generations per
request. The reviewer uses the same pinned weights in a separate cached session.
It adds CPU latency and memory. The legacy model and quick rules mode retain their
older evidence guards. A schema-valid decision is not necessarily correct.

## Current focused reliability fix: v0.7.1

A valid no-tool or clarification answer is now terminal. A mistaken reviewer can
no longer reject that answer and induce a retry into a tool call. Tool-call review,
refund arithmetic, full schema checks, and mock business policy remain in place.
This does not guarantee that the model's initial decision is correct.

The original false escalation is covered by a regression test using its preserved
raw response and review. New targeted CPU model checks are documented in
[terminal reliability evidence](artifacts/terminal-reliability-v071/README.md).
The 40-case v0.7 scores below remain historical; they have not been relabeled as
v0.7.1 accuracy. The focused change adds no new application features.

## Measured results

On the recorded v0.6/v0.7 matched 40-question test, accepted final correctness changed from **23/40 to 30/40**, and correct final tool calls from **3/16 to 15/16**. Original first answers scored 34/40 and 34/40 respectively.

That historical comparison is recorded in
[semantic comparison](artifacts/semantic-comparison-v7/README.md), including all
40 first answers, reviews, retries and final outcomes. It compares the same
Qwen3 primary model and prompt, with and without the new review pipeline.
Total compute is **not matched**: v0.7 adds review calls.

The model and implementation were frozen before the new 40 questions were
written and run. The implementing assistant also authored/reviewed these
fictional cases; there was no independent blind or human annotation. This is
small portfolio evidence, not a production accuracy estimate. All failed and
blocked cases stay in the denominator. Tool execution is disabled during scoring.

Earlier measured comparisons remain visible:

| Separate test cohort | Versions | First answers correct | Accepted final correct |
| --- | --- | --- | --- |
| 20 questions | v0.3 → v0.4 | 8 → 9 | 2 → **7** |
| 40 questions, portfolio-v3 | v0.4 → v0.5 | 21 → 37 | 16 → 32 |
| 40 harder questions, portfolio-v4 | v0.5 → v0.6 | 33 → 33 | 22 → 22 |

The **7/20 result is retained**, together with its failure analysis. The stronger
CPU model improved a separate matched system comparison, but the regex guard
still rejected too many correct tool calls. On portfolio-v4, only 1/16 expected
tool calls survived correctly in either version. That failure motivated semantic
review and arithmetic validation. Different cohorts cannot support a direct
7/20-to-new-score improvement claim.

[Original 20-case comparison](artifacts/portfolio-version-comparison/README.md) ·
[Stronger-model comparison](artifacts/quality-comparison-v5/README.md) ·
[Unsuccessful guard revision](artifacts/guard-comparison-v6/README.md)

Development captures, including the 35/40 exploration on already observed cases,
are labeled as development and kept separate. No fine-tuning was performed.

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
Use a machine with at least 16 GB RAM for live primary generation plus semantic
review. The quick demo needs no model. Timing depends on hardware and request length. The backend uses zero GPU layers,
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
bash scripts/check.sh
```

The completed source checks pass **559 tests**, lint, formatting, CLI execution,
synthetic-data auditing, and completion-only training export. Unit tests check
software behavior; their count is not model accuracy. See the
[v0.7 release evidence](docs/assets/release-checks-v0.7.1.json) for package and browser checks.
CI runs without model downloads or a GPU. Native llama.cpp inference is optional.

## Explore the project

| Path | Contents |
| --- | --- |
| `app.py` | Playground, Evaluation, and Project tabs |
| `src/tunebench/assistant.py` | Shared decision, review, retry, and mock dispatch pipeline |
| `src/tunebench/semantic_guard.py` | Model judgement, preserved raw review, runtime identity |
| `src/tunebench/safe_calculator.py` | Restricted AST/Decimal arithmetic; no Python eval |
| `datasets/portfolio-v5/` | Frozen new cases, author rationale, hashes and limitations |
| `artifacts/` | Original outputs, protocols, failures, scores, computational audits |
| `tests/` | Offline contracts, scoring, tools, CLI, and UI checks |

Use the [demo walkthrough](docs/demo-script.md), [resume wording](docs/resume-bullets.md),
and [completion record](docs/portfolio-completion.md). Present contributions you
understand and can demonstrate, including development assistance.

The original research framework includes unreviewed synthetic candidates and
optional LoRA/QLoRA runners. Those are future experiments; no adapter was trained.
Human evaluation, broad adversarial testing, real integrations, monitoring, and
production deployment remain outside this portfolio simulation.
