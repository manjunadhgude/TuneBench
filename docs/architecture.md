# TuneBench architecture

TuneBench has two connected uses: demonstrate how a tool-calling assistant handles
one request, and measure how reliably a model makes that decision. The assistant
is a small customer-support simulation. The experiment framework preserves raw
model mistakes so that an attractive demo cannot silently inflate research scores.

## A request through the assistant

```mermaid
flowchart TD
    UI[Streamlit: request and explicit backend selection] --> Router{Backend}
    Router --> Rules[Rules: deterministic Python, no LLM]
    Router --> Qwen[Live Qwen: strong-v3 and JSON-constrained generation]
    Router --> Replay[Replay: previously recorded response]
    Rules --> Raw[Raw response and backend identity]
    Qwen --> Raw
    Replay --> Raw
    Raw --> Parse[Strict JSON parse]
    Parse --> Validate[Output schema and tool argument validation]
    Validate --> Ground[Grounding guard: check values against request]
    Ground --> Decision{Accepted decision?}
    Validate -->|model failure and repair budget remains| Repair[One visible repair with validation feedback]
    Ground -->|evidence failure and repair budget remains| Repair
    Repair --> Qwen
    Decision --> Clarify[Clarification: ask for unresolved information]
    Decision --> None[No tool: explain supported scope]
    Decision --> Execute[Execute one nonmutating mock tool]
    Execute --> Result[Simulated result and execution trace]
    Clarify --> Trace[Visible decision and validation trace]
    None --> Trace
    Result --> Trace
    Decision -->|invalid or unsupported values| Block[Block execution; show validation or guard errors]
    Block --> Trace
```

“Tool calling” means selecting a named function and structured arguments, then
letting application code validate and dispatch the call. The model itself cannot
access orders or execute payments. Only the three registered mock operations are
available:

| Tool | Required arguments | Demonstrated behavior |
| --- | --- | --- |
| `get_order_status` | `order_id` | Read a simulated order's status |
| `check_refund_eligibility` | `order_id`, `reason` | Apply the mock eligibility policy |
| `propose_refund` | `order_id`, `refund_amount`, `reason` | Return a simulated proposal without transferring money |

Schema validation checks shape, known fields, argument types and allowed values.
The grounding guard adds checks that a schema cannot express, such as whether a
proposed order reference or amount is supported by the request. These checks are
bounded engineering rules. They do not establish that every possible natural-language
request is understood correctly. Unknown orders and unsupported actions must be
visible outcomes, rather than successful-looking fabricated results.

The rules backend makes the UI quick to demonstrate on a CPU without downloading a
model. It is not an LLM baseline. Live Qwen uses actual model generation and can be
slow or wrong. Replay presents retained output without generating it again; it is
recorded evidence, not a new inference request. The backend identity belongs beside
the result, not only in developer logs. The UI names these modes **Quick demo**,
**Live local Qwen**, and **Saved model replay**. Replay exposes only its saved
questions and responses and does not execute a tool. The interactive assistant is
stateless: a clarified follow-up must include the complete request.

## A separate measurement path

```mermaid
flowchart LR
    Data[Reviewed tasks: requests, tools and gold labels] --> Inputs[Prompt builder: request and tools only]
    Inputs --> Model[Versioned prompt and pinned model]
    Model --> Predictions[Raw text, parsed prediction and run metadata]
    Predictions --> Score[Deterministic evaluator]
    Data -->|gold used only for scoring| Score
    Score --> Report[Per-example report and error analysis]
    Report --> Compare[Paired comparison with family-cluster bootstrap]
    Train[Train partition only] --> Supervision[Chat prompt plus expected completion]
    Supervision --> Optional[Optional GPU LoRA or QLoRA]
    Optional --> Adapter[Adapter for a separately measured run]
```

Gold labels, family IDs, split names and difficulty labels are excluded from model
prompts. Dataset generation and scoring are independent of model inference. This
lets tests inject known predictions without downloading weights, while actual
model runs retain their own evidence.

The evaluator reports several dimensions because they answer different questions:
JSON parsing, schema validity, outcome choice, tool selection, argument correctness,
clarification fields, no-tool decisions, and strict end-to-end task success. Correct
tool selection can receive independent credit even when the arguments are wrong.
Strict task success still fails that example. Missing or invalid predictions remain
in the denominator and diagnostics.

## Raw model output versus the assistant's final response

Keep these three objects distinct:

1. **Raw output:** the exact text returned by a model or recorded backend.
2. **Parsed decision:** the structured object obtained by strict parsing and validation.
3. **Application result:** the clarification, blocked request, or mock-tool result shown
   after application checks.

In v0.4 the live backend uses `strong-v3` and optional `lm-format-enforcer` token
constraints to guide generation toward the decision JSON schema. The package
reuses tokenizer data but creates a fresh constraint parser for each generation.
Constraints improve output structure; the library does not enforce every numeric
or array restriction. Strict parsing and complete post-generation validation
therefore remain required.

If an assistant flow offers a repair or fallback, retain the first response and label
that intervention. A repaired final answer does not retroactively make the original
model prediction correct. The retained baseline and paired prompt experiments use
one attempt per question, with no repair or retry. Their original reports must not
be replaced by assistant-demo outcomes.

## Why these components

| Choice | Reason and trade-off |
| --- | --- |
| Python package with CLI | Run data, scoring and tests without depending on a web session |
| JSON Schema, constrained generation and semantic checks | Guide JSON structure, validate the complete contract, then check request evidence |
| Streamlit | Provide a small inspectable portfolio interface without a separate frontend build |
| Mock tools | Demonstrate execution and policy handling with reproducible local data |
| Optional model dependencies | Keep the core install light; make real inference an explicit operation |
| Versioned prompts and run metadata | Make changes and comparisons reviewable |
| Completion-only training preparation | Teach expected assistant output while masking prompt tokens |

There is no vector database or RAG pipeline because this task is action selection
against a small tool registry. There is no production deployment claim: authentication,
real customer systems, financial transactions, broad adversarial evaluation and
operational monitoring are outside this portfolio scope.

## Evidence and limitations

The first real Qwen CPU smoke run scored **7/20** strict successes. On a separate
12-case paired development set, legacy `strong` scored **2/12** and `strong-v2`
scored **5/12**, including four improvements and one regression. Those are small,
constructed sets; they do not establish general accuracy or a training benefit.
No LoRA/QLoRA training or trained-adapter evaluation has been performed.

The historical v0.3 portfolio holdout scored **7/20** raw first-attempt strict
successes and **3/20** accepted final successes. Its guard rejected four correct
contextual or derived answers, which motivated the v0.4 changes. These results
remain [retained evidence](../artifacts/portfolio-evaluation/README.md); they are
not measurements of the revised implementation. The fresh v0.3/v0.4 comparison
has not completed at this checkpoint.

See the [initial experiment](../artifacts/baseline-smoke/README.md),
[paired prompt experiment](../artifacts/prompt-development-v2/README.md),
[dataset notes](dataset.md), and [implementation status](status.md).

## Interactive policy boundaries

The bundled mock store contains five fictional orders (`TB-1001`–`TB-1005`) and
uses a fixed policy date, **9 November 2026**, so results are reproducible. Amounts
are INR, represented with decimal handling in the tool layer. Delivered damaged,
wrong-item or changed-mind requests are evaluated against an inclusive 30-day
window; a not-received request requires a shipped order past its expected date.
A delivered-order dispute is not treated as proof of nonreceipt. A proposal cannot
exceed the remaining refundable amount and does not mutate that amount.

The v0.4 evidence extractor checks the requested action, literal order references,
reason evidence and monetary values. It handles explicit corrections and context
within one submitted request, including quoted or punctuation-rich references.
It can derive a refund from supplied quantity and unit price or a supplied
percentage and base using `Decimal`; absent or conflicting inputs require
clarification. It does not look up benchmark labels or silently replace the model's
decision with a rules answer. Execution separately requires a known demo order and
passes through the mock tool's independent policy checks.

These are bounded language rules, so both false acceptance and false rejection
remain possible. A correct calculation is not permission for a real payment;
`propose_refund` always returns a simulation. Requests remain stateless across UI
submissions, even when the text of one submission contains earlier context.

The assistant API is `respond(message, backend="rules", ...)`. It returns a status
(`executed`, `clarification`, `no_tool`, `blocked` or `error`), backend identity,
raw attempts, accepted outcome, validation errors, optional tool result, user-facing
message and elapsed time. The model backend loads a local snapshot lazily; it does
not silently download weights or fall back to rules. It allows at most one visible
repair attempt for a parse/schema error or an explicit request-evidence mismatch.
Evidence repair feeds back extracted request facts, not gold labels. Both raw
attempts and their schema/grounding errors remain available. The model must generate
the corrected answer itself; application code never rewrites its output. A failed
final decision is blocked. Store lookup and business-policy failures are separate
execution gates and do not trigger generation retries.

The v0.3 and v0.4 comparison changes the prompt, generation constraints, guard and
repair trigger together. It is a system-version comparison, not a prompt-only
ablation or evidence of model training. The same fresh questions and pinned model
are used for both versions; raw first-attempt and accepted final scores must both
be reported. That new comparison is pending at this documentation checkpoint.
Earlier one-attempt research evidence remains unchanged.
