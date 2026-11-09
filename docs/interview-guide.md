# Interview guide

Use this guide to understand and explain the implementation. Replace the example
wording with your own explanation after running the project and tracing the code.
Be clear about assistance used during development and which parts you personally
implemented, reviewed, tested or changed. Do not present generated code as work you
can explain until you have studied it.

## A short introduction

> TuneBench is a Python tool-calling assistant demo and evaluation framework. It
> handles a simulated customer-support request by choosing a tool, asking for
> missing information, or declining an unsupported action. It keeps raw model
> output and evaluates decisions separately from the application's final response.
> I used it to study prompting, validation, failure analysis and reproducible tests.

For an AI/ML role, follow with the real experiments. For a Python/backend role,
follow with contracts, dispatch, validation and tests. For a full-stack role,
show the Streamlit request-to-result flow and then explain the underlying package.

## Questions to be ready for

### Why use tools instead of asking the model to write an answer?

A generated status sentence is not a database lookup. A tool call gives the
application an explicit operation and typed arguments that it can validate and
execute. Here those operations use mock data. In a real system, the application
would also need authorization and transaction-specific controls.

Show `get_order_status` in the tool registry. Trace a request containing an order ID
through parsing, validation, grounding and dispatch. Then remove the ID and explain
why a clarification is preferable to inventing one.

### Does valid JSON mean a correct answer?

No. A response can be parseable JSON but have the wrong outcome type. It can satisfy
the schema but select the wrong tool or invent a valid-looking order ID. It can
choose the right tool but use an incorrect amount. These failures need separate
metrics and semantic checks. A perfect parser score is not a tool-calling accuracy
score.

### What does the grounding guard add?

A schema can require an ID to be a string, but cannot establish that the user
provided that ID. The guard checks supported references and values before tool
execution. Explain the actual implemented checks and their limitations: a small
rule set is not a general natural-language proof system. In v0.4 it can follow
explicit corrections and derive an amount from supplied factors with `Decimal`.
Missing factors still require clarification. Show a blocked example and the
stated reason rather than claiming all hallucinations are prevented.

### What does constrained generation do?

The live v0.4 path uses `strong-v3` plus `lm-format-enforcer` to restrict which
tokens can follow the current JSON prefix. This helps produce the expected decision
shape while keeping model weights unchanged. The library does not enforce every
schema restriction, so full validation still follows generation. Valid structure
also cannot establish that an order ID, action or amount is correct.

### Why provide a rules backend if this is an AI project?

It gives reviewers a fast CPU demo of the application flow and makes deterministic
execution tests possible. It is explicitly labeled as rules, not model inference.
The live Qwen path measures a different component. A high rules-demo success rate
must not be reported as Qwen's model accuracy.

### What are the measured model results?

The first 20-case smoke experiment achieved 7 strict successes. A later, different
12-case development set was used for a paired prompt comparison: legacy `strong`
achieved 2/12 and `strong-v2` achieved 5/12, with four improvements and one regression.
The revised prompt also produced one fewer parseable JSON response. Explain that
these are small development checks, not production accuracy estimates.

Do not compare 7/20 directly with 5/12 as if the same questions were used. Open the
[saved paired report](../artifacts/prompt-development-v2/paired-run/comparison.json)
and [error analysis](../artifacts/prompt-development-v2/error-analysis.md).
The uncertainty interval includes zero, so the result does not establish a general
improvement.

The historical v0.3 portfolio run scored 7/20 raw first-attempt successes and 3/20
accepted final successes. Four correct answers were rejected by the guard. Explain
that this identified a validator problem as well as a model problem. The fresh
v0.3/v0.4 system comparison is pending at this checkpoint; do not assign a new
score until the completed report exists. See the
[v0.3 results](../artifacts/portfolio-evaluation/README.md).

### Why not fine-tune immediately?

Fine-tuning needs trustworthy labels, a meaningful baseline and an evaluator. If
formatting, task definitions or scoring are wrong, training can optimize the wrong
behavior. TuneBench first measures prompts and failures. It includes training-data
preparation and optional LoRA/QLoRA code, but no training run or trained adapter is
claimed.

LoRA learns a small set of adapter parameters while keeping base weights fixed.
QLoRA combines adapters with a quantized base model to reduce training memory.
Neither guarantees better tool selection. Explain these concepts without saying
this project has demonstrated an improvement from training.

### What is completion-only loss?

The model sees the user request and tool descriptions as context. Only the expected
assistant output should contribute supervised loss. The preparation code masks the
prompt with `-100`, includes the assistant completion, masks padding, and rejects
unsafe template boundaries or truncation. Read `tokenize_completion` and its tests
before explaining this in an interview.

### How do you prevent data leakage?

Do not put gold labels, scenario IDs, split names or difficulty labels in prompts.
Keep related scenario families in one split. Use validation data for prompt changes
and preserve the final test for a frozen comparison. Training preparation rejects
test/smoke inputs and cross-partition family leakage. Structural checks cannot prove
semantic independence: different IDs or wording can still express the same template.
The 1,250 generated records remain synthetic candidates, not a reviewed final benchmark.

### Why do retries and output repair matter?

A second generation, JSON repair or rules fallback can change the result and cost.
The early baseline experiments use one attempt, no repair and matched decoding.
The live v0.4 assistant allows at most one repair after schema or explicit
request-evidence validation fails. It supplies errors and extracted request facts,
then asks the model to generate again; it never rewrites the answer into a rules
result. Both attempts stay in the trace. Report raw first-attempt metrics separately
from accepted final success, total generations and latency. A final block does not
make the initial answer correct.

### How do you compare two versions fairly?

Use the same reviewed examples, tool definitions, model revision, decoding budget,
validation and retry policy. For a prompt ablation, intentionally vary the prompt
while holding other conditions fixed. Preserve both prompt versions and their raw
responses. Use paired outcomes to identify improvements and regressions. The report
comparison checks data and protocol metadata and uses family-cluster resampling;
small synthetic families still limit the inference you can draw.

The v0.3/v0.4 comparison deliberately changes several components: prompt,
constraints, evidence checks and repair trigger. Call it a system-version
comparison. Keep the same fresh cases, model weights, CPU settings, maximum token
budget and maximum repair count; document the intentional differences. It cannot
isolate which component caused a gain or show a fine-tuning benefit.

### Why is live inference slow on a CPU?

A 1.5B-parameter model still performs substantial work to process a prompt and
generate tokens. The recorded first smoke run averaged about 25 seconds of generation
per request on its tested CPU configuration; model loading adds startup time. This
is an observation from that run, not a latency promise for every machine. Rules
mode is fast; replay avoids generation but is labeled as recorded. A GPU could
change throughput, but that needs an actual measured run.

### What would you improve next?

Choose one concrete next experiment: broaden and review development cases; improve
an identified decision failure; add a more capable baseline under matched conditions;
or verify a small GPU adapter-training run after the baseline is credible. Explain
how you would measure success and regressions. Avoid listing infrastructure unrelated
to the demonstrated problem.

## Learn the code before presenting it

Work through these exercises and keep your own notes:

1. Run the rules demo and inspect one successful tool result, one clarification,
   one unsupported request and one blocked invalid call.
2. Read the canonical registry and explain every required argument and allowed reason.
3. Follow one request from the UI into the assistant and back into its trace.
4. Read one unit test for a malformed response and predict the expected result before
   running it. Explain why a missing prediction stays in the evaluator denominator.
5. Read one actual failed Qwen response. Identify whether the problem is parsing,
   schema, action selection, an argument, or a reason code.
6. Trace a visible repair: identify the first error, the feedback, the second raw
   output and the accepted or blocked final decision.
7. Make a small change you understand, add a meaningful test, run the checks and
   describe that specific contribution in your own words.
8. Explain how a wheel loads packaged schemas when run outside the source checkout.

Being able to diagnose a limitation and propose a measured next step is more useful
than repeating a high accuracy claim that the evidence does not support.
