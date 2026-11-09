# Interview guide

Study and run the implementation before presenting it. Describe your actual
contribution, including assistance used during development. Use the examples below
as prompts for an explanation in your own words.

## A short introduction

> TuneBench is a Python tool-calling workbench and evaluation framework. A local
> CPU language model chooses a mock support tool, requests missing information or
> decides that no tool should run. The application validates decisions and keeps
> original answers separate from repairs and simulated execution. I used measured
> failures to improve model selection and validation behavior.

For a GenAI role, explain the model, constraints and evaluation. For a Python role,
trace the shared package, contracts and dispatch. Show the working flow before
listing infrastructure.

## How should I explain the earlier 7/20 result?

Keep it visible and explain what it revealed. On the earlier matched 20-case
experiment, v0.4 had 9 correct first answers but only 7 correct accepted finals.
The small model made decision errors, and the guard/repair path also lost five
correct first answers while repairing three mistakes. Valid JSON alone did not
solve the problem. See the
[original outputs and error analysis](../artifacts/portfolio-version-comparison/README.md).

v0.5 addresses both components: a newer Qwen3-4B model running as a CPU Q4_K_M
GGUF, a revised prompt, and a guard that no longer uses heuristic disagreement to
retry schema-valid non-executing answers into actions. Actual tool calls still
need evidence. Those are engineering changes, not an excuse for the weak result.
They must earn a better result on a fresh test.

The revised model scored 37/40, then 40/40 after prompt examples changed, on the
same development questions. That is tuned practice coverage and must not be
quoted as unseen accuracy. Both systems were then frozen for a separate 40-case
comparison. The full comparison and independent audit are still running at this
checkpoint; quote new test numbers only after the completed audited report exists.

## Questions to be ready for

### Why use tools instead of asking the model for a status sentence?

A generated sentence is not a database lookup. A tool call names an operation and
provides typed arguments that application code can validate and dispatch. Here
those operations read fictional data or return simulated proposals. The model
cannot directly execute payments or access customer accounts.

Trace `Check the status of order TB-1001.` through the registry, parser, evidence
checks and dispatcher. Remove the ID and explain why clarification is appropriate.

### Does valid JSON mean a correct decision?

No. JSON can be parseable but violate a schema. A schema-valid call can still use
the wrong tool, reference, reason or amount. The evaluator measures those failures
separately and also reports strict success. A perfect formatting result is not a
model-accuracy result.

### What does the guard check, and why are some checks advisory?

For an actual tool call, it checks the requested action and argument evidence in
the request. It can follow explicit corrections, product-role contrasts and exact
calculations from supplied factors using `Decimal`. These are bounded language
rules; they cannot prove that every utterance was understood.

A schema-valid no-tool or clarification answer executes nothing. In v0.5, heuristic
disagreement with such an answer is advisory and cannot trigger an evidence retry
into an action. That avoids the earlier failure where a correct non-action answer
was changed into a wrong decision. It can still accept a wrong refusal or
clarification, so the evaluator must count those as quality errors. Schema errors
can still use the bounded repair.

### What does constrained generation do?

The preferred backend uses `strong-v4` and llama.cpp JSON-schema grammar to restrict
possible next tokens. Complete parsing and validation still follow generation.
Constraints guide structure; they do not establish that the model selected the
right action or facts. The legacy Qwen2.5 profile instead uses `strong-v3` and
lm-format-enforcer; its results retain their own version and runtime identity.

### Why use a quantized CPU model?

The selected file is Unsloth's Q4_K_M conversion of official
Qwen3-4B-Instruct-2507. It uses roughly four-bit blocks, with some tensors at higher
precision, reducing weight storage relative to float32. Its actual file is about
2.5 GB. Total process memory also includes context and runtime allocations.

Quantization does not guarantee unchanged accuracy or a fixed speedup. The model,
quantization and runtime must be measured together. This project uses the existing
conversion; it did not train or fine-tune those weights. The loader verifies the
pinned revision, file size and SHA-256 before loading, with zero GPU layers.

### Why provide a rules backend?

It demonstrates the application quickly without a model download and makes
execution tests deterministic. The UI labels it as rules, not an LLM. Saved replay
is also distinct: it shows an immutable historical response without generating a
new answer. Neither is a substitute for measuring actual model decisions.

### What is the current quality evidence?

The 40-case v0.4/v0.5 comparison and independent computational audit are in
progress at this checkpoint. The same new cases are used for both versions, with
CPU execution, four generation threads, seed 42, greedy decoding, at most 256 new
tokens and at most one repair. Model, quantization, runtime, prompt and guard change
together. This is a system comparison, not an isolated model/prompt ablation.

The cases are fictional and stratified, authored/reviewed by assistants, including
separate reviews blinded to implementation. They have no independent human
annotation. All cases remain in each denominator, including invalid, blocked and
failed outputs. Scoring disables tool execution. Clarification wording is checked
for contract validity, not human-graded helpfulness. Small results cannot establish
production reliability or real execution safety.

The older 20-case table remains visible: raw strict 8/20 → 9/20, schema-valid
13/20 → 19/20, final strict 2/20 → 7/20 for v0.3/v0.4. Other historical data include
an initial 7/20 smoke and a separate 12-case prompt-development comparison of 2/12
and 5/12. Different question sets cannot support a direct before/after claim.
See the [quality protocol](quality-comparison-protocol.md) and
[historical comparison](../artifacts/portfolio-version-comparison/README.md).

### Why report performance by decision type?

A total score can look good when no-tool and clarification cases pass while valid
requested tool calls are blocked. Report raw and accepted-final correctness for
each expected outcome separately, plus false blocks and incorrect accepted calls.
A functioning support assistant needs useful tool execution as well as safe
non-execution; overall accuracy alone can hide this weakness.

### How do you prevent leakage or misleading repair scores?

Prompt builders expose only the request and tool definitions, never the gold,
case ID, split or difficulty. Development examples can guide changes; a final
comparison freezes code, model assets, data and budgets before generation. New
results make that test seen, so later tuning requires a new final test set.
Structural non-overlap checks do not prove semantic independence.

The original first answer is saved before any feedback. A repair can use validation
errors and facts extracted from the request, never the answer key. The model must
generate again; code does not rewrite its output into a rules answer. Raw-first
and accepted-final scores are separate. Durable journals preserve completed cases,
and ambiguous interrupted generations are not silently rerun.

### Why not fine-tune immediately?

Reliable labels, a baseline and a sound evaluator come first. Training can optimize
the wrong behavior if task definitions or scoring are wrong. TuneBench includes
completion-only training export and optional LoRA/QLoRA runners, but no training
run or trained adapter is claimed.

LoRA learns a small set of adapters while keeping base weights fixed. QLoRA combines
adapters with a quantized base to reduce training memory. Completion-only loss
masks prompt and padding tokens with `-100`, so only expected output contributes
to supervised loss. Read the preparation code and tests before explaining it.

### Why is there no RAG or vector database?

This task chooses actions against a small tool registry and reads structured mock
orders. Retrieval of policy documents would be a different component to measure.
Adding RAG would not by itself fix wrong tool selection or invented arguments.

### What do the software checks prove?

The full local v0.5 suite passes 469 checks; fresh app setup passes 465 with four
optional checks skipped, and core-only passes 459 with five skips. These verify
contracts, scoring, parsing, guards, mock tools, CLI and UI behavior under tested
conditions. They are not 469 successful real-model conversations. Standalone-wheel
and launch checks are recorded; current v0.5 browser evidence is still pending.

## Learn the code before presenting

1. Run one successful tool request, one clarification, one unsupported request and
   one blocked unknown demo order. Explain the backend label in each result.
2. Read the tool registry and explain every required argument and allowed reason.
3. Trace a live request through `assistant.py`, the selected local backend,
   validation, grounding and mock dispatch.
4. Inspect a real failed output and classify its error before opening the score.
5. Trace one visible repair and explain why the original score remains unchanged.
6. Read a no-tool advisory test and explain why it does not trigger an action.
7. Run a meaningful test, make a small change you understand and explain your own
   contribution clearly, including development assistance.
8. Show how packaged resources load when the wheel runs outside the source checkout.

A useful interview explanation connects a measured failure, a concrete change and
a fair verification. It does not hide failures or claim results from training that
never happened.
