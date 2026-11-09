# TuneBench

**A CPU-friendly GenAI tool-calling workbench with validation, simulated tools, and evaluation.**

TuneBench turns a simulated customer-support request into a tool call, a clarification,
or a no-tool decision. The Streamlit app shows the request, structured output,
validation, execution trace, and result. A separate evaluation framework records
model failures and compares versions without hiding raw outputs.

![TuneBench Playground: backend choice, request and inspectable result](docs/assets/tunebench-playground.png)

[Watch the short demo](docs/assets/tunebench-demo.webm) ·
[Architecture](docs/architecture.md) · [Interview guide](docs/interview-guide.md)

## Start the app

Use Python 3.12 for the tested, hash-locked app setup. These commands were verified
on Linux; Windows users can use WSL. Codespaces and a GPU are not required:

```bash
git clone https://github.com/manjunadhgude/TuneBench.git
cd TuneBench
bash scripts/setup.sh --app
bash scripts/start_demo.sh
```

Use the existing checkout if you already have the repository. Setup creates `.venv`
and installs hash-locked application/development dependencies using uv or pip.
The app starts on port 8501; open it in your development environment's browser.
**Quick demo works without downloading a model or providing an API key.**

In **Playground**, choose **Quick demo**, enter a request, and click **Run request →**.
Try these fictional examples:

- `Check the status of order TB-1001.`
- `Check the status of my order.`
- `Propose a refund of 200 for order TB-1002 because the item arrived damaged.`
- `Execute a refund payment of 200 for order TB-1002 now. Do not create a proposal.`

Requests are stateless. After a clarification, submit the complete request with the
missing information. The **Evaluation** tab presents retained results; **Project**
explains the design and limitations.

## Three modes, clearly labeled

| Mode | What runs |
| --- | --- |
| **Quick demo** | Deterministic Python rules and the guarded execution path. This is not an LLM. |
| **Live local Qwen** | Actual Qwen2.5-1.5B-Instruct generation from an existing verified local snapshot. |
| **Saved model replay** | Previously recorded smoke responses. No new generation or tool execution. |

Live mode can fail or be slow. Replay uses its saved questions, not arbitrary new
input. A fast rules result or recorded response must not be presented as live model
performance.

## What the assistant executes

| Mock tool | Purpose |
| --- | --- |
| `get_order_status` | Read a fictional order's status |
| `check_refund_eligibility` | Check the versioned mock refund policy |
| `propose_refund` | Return an immutable simulated proposal |

Five fictional orders use INR balances and a fixed policy date, **9 November 2026**.
The policy checks a 30-day refund window, nonreceipt conditions, remaining balance
and monetary precision. No tool changes an order, reserves money, contacts a real
customer system, or transfers a payment.

The flow is **request → rules/model → strict parse → schema validation → grounding
checks → clarification, no tool, or mock execution → visible trace**. It checks
supported actions and request-grounded arguments before execution. Model mode uses
`strong-v3` with token-level JSON constraints and permits at most one visible
repair for a parse/schema or request-evidence failure. A failed repair is blocked.
The first output, validation feedback and repair remain visible; no model answer
is silently replaced with the rules baseline.

The guard extracts literal references, explicit corrections, reasons and monetary
evidence. It can derive a requested quantity × unit price or percentage using
Decimal arithmetic. Its language rules remain limited and may reject correct
answers or miss mistakes. JSON constraints also require full postvalidation.
A repaired application result is separate from raw first-attempt model accuracy.

## Measured results

Both versions answered the **same 20 new, frozen fictional questions**, using
unchanged Qwen2.5-1.5B-Instruct weights on CPU. The prompt, JSON constraints,
grounding and repair feedback changed together. This measures complete systems;
it does not isolate a prompt change or show a fine-tuning benefit.

| Decision evaluation | v0.3 | v0.4 |
| --- | ---: | ---: |
| Strictly correct original first answer | 8/20 | 9/20 |
| Schema-valid original first answer | 13/20 | 19/20 |
| Strictly correct accepted final decision | 2/20 | 7/20 |

All 20 questions remain in every denominator, including invalid and blocked
answers. Final decisions include validation and at most one repair; they are
separate from original model accuracy. The final comparison has seven gains and
two regressions. The revised guard accepted no incorrect decisions on these 20
cases, but rejected correct answers too: five correct first answers were lost,
and three errors were repaired. Final success still falls below the revised
model's own raw 9/20 result.

v0.4 used 36 generations, including 16 repairs, versus 27 generations and seven
repairs for v0.3. Active case elapsed time was 1,143.2 versus 877.1 seconds on the
tested CPU. Both runs had zero runtime errors. These are small assistant-authored,
assistant-reviewed data, without independent human annotation. Accuracy remains
limited; this is a portfolio prototype, not a production support assistant.

See the [matched results and raw evidence](artifacts/portfolio-version-comparison/README.md),
[failure analysis](artifacts/portfolio-version-comparison/error-analysis.md),
[computational audit](artifacts/portfolio-version-comparison/independent-audit.json)
and [frozen protocol](docs/version-comparison-protocol.md). Scoring disables tool
execution, so these scores do not measure real transactions or establish that the
execution guard blocks every unsafe request. Further tuning requires development
data and a new final test set.

Earlier results use different questions and remain separate. The original v0.3
portfolio holdout scored 7/20 raw and 3/20 accepted final decisions; its conservative
guard rejected four correct contextual/derived answers. See the
[historical results](artifacts/portfolio-evaluation/README.md) and
[data review](docs/portfolio-data-review.md). The initial real-model smoke scored
7/20; a paired 12-case development prompt experiment changed 2/12 to 5/12, with
four gains and one regression. See the [smoke evidence](artifacts/baseline-smoke/README.md)
and [paired prompt evidence](artifacts/prompt-development-v2/README.md).
Different datasets cannot support a direct before/after accuracy claim.

## Optional: run the actual model

Quick demo needs none of this. The verified CPU model stack uses PyTorch 2.8.0 CPU,
Transformers 4.57.6, Accelerate 1.15.0 and lm-format-enforcer 0.11.3. With uv installed:

```bash
uv pip install --python .venv/bin/python --torch-backend cpu \
  'torch==2.8.0' 'transformers==4.57.6' 'accelerate==1.15.0' 'lm-format-enforcer==0.11.3'
.venv/bin/python scripts/download_smoke_model.py \
  --output ../models/Qwen2.5-1.5B-Instruct/989aa7980e4cf806f80c7fef2b1adb7bc71aa306
```

The downloader verifies pinned upstream file hashes. In **Live local Qwen**, enter
that directory in **Local model directory**. The app verifies existing assets and
never downloads weights implicitly. The public model does not require a paid API.
Allow roughly 3 GB for weights and 10 GB of process memory. Generation can take
roughly 25–60 seconds per attempt on a CPU, plus initial loading. A repair adds
another attempt; hardware, request and output length affect timing. Retained runs provide actual measurements.

See [model setup and evidence](artifacts/baseline-smoke/README.md) for reproduction
and network requirements. No GPU training or trained-adapter evaluation has been
performed. LoRA/QLoRA runners are optional future experiment support, not a completed
fine-tuning result.

## CLI and checks

After setup, run the same application logic without the browser:

```bash
.venv/bin/tunebench orders
.venv/bin/tunebench assist --message 'Check the status of order TB-1001.'
.venv/bin/tunebench evaluate --gold GOLD.jsonl --predictions PREDICTIONS.jsonl \
  --output REPORT.json
bash scripts/check.sh
```

The v0.4 full local suite passes **401 tests**, including contracts,
metrics, grounding, mock tools, CLI and Streamlit behavior. A fresh app-only
installation passes 398 tests with three optional model checks skipped; core-only
passes 392 with four skips. CI installs the app
requirements and runs the CPU checks without model downloads or a GPU. Controlled
gold-derived fixtures test the evaluator; their perfect score is not model accuracy.

## Explore and present the project

| Path | What to inspect |
| --- | --- |
| `app.py` | Streamlit Playground, Evaluation and Project tabs |
| `src/tunebench/` | Assistant, guard, mock tools, inference, contracts and scoring |
| `datasets/portfolio-v1/` | Frozen 40-development / 20-holdout case files and hashes |
| `datasets/portfolio-v2/` | Frozen 20-case matched system comparison, now evaluated |
| `tests/` | Offline unit, integration and UI checks |
| `artifacts/` | Retained inputs, raw outputs, protocols, metrics and error analyses |
| `docs/` | Architecture, walkthrough, interview preparation and research notes |

Use the [2–3 minute walkthrough](docs/demo-script.md),
[interview guide](docs/interview-guide.md), [resume wording](docs/resume-bullets.md),
and [completion/evidence checklist](docs/portfolio-completion.md). Describe only
contributions you understand and can demonstrate, including development assistance.

The original research framework also generates 1,250 synthetic candidate records
and prepares completion-only training data. Those candidates remain unreviewed and
unfrozen, separate from the small portfolio dataset. Human data review, a stronger
baseline, GPU training and a broader evaluation are future research work.
