# Model experiments

The core environment and smoke tests do not download a model. They verify data,
contracts and scoring. Gold-derived predictions are evaluator fixtures and cannot
measure a baseline's quality.

The candidate is `Qwen/Qwen2.5-1.5B-Instruct` (Apache-2.0). A real run needs access
to Hugging Face model artifacts and several GB of memory/disk. Install the `model`
extra for inference and `training` for LoRA. Install `qlora` only for optional
4-bit training on a supported CUDA GPU. The default CPU installation stays small.
No GPU availability, free remote compute, or trained adapter is assumed.
The current cloud machine has no detected CUDA GPU, and its outbound policy
denies `huggingface.co`; model baselines and training were not run here. Model
downloads need `huggingface.co` and the specific redirected artifact hosts
permitted in environment settings. Recheck the actual download after access is
configured rather than assuming a domain addition guarantees it works.

`tunebench infer` supports minimal and strong prompts. Both use the same tool
definitions, output contract, greedy decoding, token budget, and single-attempt
policy. Inputs contain the user's request and tools; benchmark labels, split,
family, difficulty and provenance are excluded. Raw responses, parse/validation
errors, latency and run metadata are retained. Markdown fences, duplicate JSON
keys, non-finite numbers and trailing text fail parsing instead of being repaired.
Inference backend failures abort the run instead of being counted as model errors.

Develop prompts on validation data. Select the prompt before inspecting final
test results. Use the same prompt, model revision, token budget, tool validation
and retry policy when comparing base and adapted models. The revision resolved
by Transformers is recorded in the run metadata; keep the model cache or pin a
local snapshot for repeat runs. Adapter inference uses the same base model ID
as the training manifest. Report per-family errors and latency alongside accuracy.

Training preparation accepts explicit train and validation partitions and rejects
test/smoke records, duplicate scenario IDs, cross-partition family leakage and
duplicate normalized prompts. It exports chat prompts plus assistant completions
and SHA-256 file hashes. Clarification questions use deterministic wording because
free-text question quality is outside the evaluator's exact-match contract.

LoRA uses completion-only labels: the chat-template prompt and assistant prefix
are masked with `-100`. Only the expected assistant output and its template suffix
contribute loss. Templates whose tokenized prefix differs between prompt-only and
full conversations are rejected. Overlong examples fail rather than truncating
the expected answer. Padding is also masked. These boundaries have offline tests.

The GPU path uses Transformers Trainer and PEFT with rank-16 LoRA on linear layers.
Optional QLoRA uses NF4, double quantization, and a supported bitsandbytes build.
It saves the adapter, tokenizer, validation loss, training metrics, data sizes,
seed, runtime, peak GPU allocation and model revision. Training loss may fluctuate;
successful training is not evidence that tool calling improved. Measure it with
the same deterministic evaluator and untouched final test set.

At this stage CPU tests cover prompt isolation, output capture, data preparation
and loss-mask boundaries. Full model downloads, GPU kernel compatibility, memory
requirements, model baselines and trained-model quality require actual model/GPU
runs. Do not present those checks as completed until run artifacts exist.
