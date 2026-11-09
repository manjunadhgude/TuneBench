# CPU model candidates for the next development experiment

Metadata and access were checked on 9 November 2026. This is a selection note,
not a TuneBench accuracy result. No model weights were downloaded and no runtime
packages were installed while preparing this note. A candidate must earn its
place through development evaluation before a new final test is opened.

## Recommended first candidate

Use **Qwen3-4B-Instruct-2507**, quantized to a local GGUF file, through a CPU
llama.cpp backend. The official model card describes this as an updated 4.0B
parameter, non-thinking instruction model with improvements in instruction
following, reasoning and tool use. Those are upstream claims, not measured
TuneBench improvements.

The public Unsloth conversion provides a smaller download and lower weight-memory
requirement than running the 4B model as float32. It is a third-party conversion,
not an official Qwen GGUF release. Metadata declares the official Qwen model as
its base and Apache-2.0 as its license.

| Item | Verified value |
| --- | --- |
| Official base | `Qwen/Qwen3-4B-Instruct-2507` |
| Base revision inspected | `cdbee75f17c01a7cc42f958dc650907174af0554` |
| GGUF repository | `unsloth/Qwen3-4B-Instruct-2507-GGUF` |
| GGUF revision | `a06e946bb6b655725eafa393f4a9745d460374c9` |
| Access | Public, ungated; no Hugging Face token required |
| License metadata | Apache-2.0; conversion links the official base license |
| First file | `Qwen3-4B-Instruct-2507-Q4_K_M.gguf` |
| Exact bytes | `2497281120` |
| Upstream LFS SHA-256 | `3605803b982cb64aead44f6c1b2ae36e3acdb41d8e46c8a94c6533bc4c67e597` |

The pinned file's HEAD request returned HTTP 200, with Content-Length matching
the metadata, through the already allowed `us.aws.cdn.hf.co` destination. No
weight body was fetched. Download completion must still verify the complete
file against the LFS SHA-256; the CDN ETag is not that checksum.

A higher-precision option in the same pinned repository is
`Qwen3-4B-Instruct-2507-Q5_K_M.gguf`, **2,889,514,080 bytes**, SHA-256
`5bde5e9d883622acb02bf77fe7dcbc56a8b9a9ad4be78a72ca23a532658b4ecb`.
It costs about 392 MB more download space. Its speed and TuneBench accuracy
relative to Q4 must be measured rather than assumed.

Sources:

- [Pinned official model card](https://huggingface.co/Qwen/Qwen3-4B-Instruct-2507/blob/cdbee75f17c01a7cc42f958dc650907174af0554/README.md).
- [Pinned conversion card](https://huggingface.co/unsloth/Qwen3-4B-Instruct-2507-GGUF/blob/a06e946bb6b655725eafa393f4a9745d460374c9/README.md).
- [Repository metadata including file hashes](https://huggingface.co/api/models/unsloth/Qwen3-4B-Instruct-2507-GGUF?blobs=true).
- [Pinned Q4 file](https://huggingface.co/unsloth/Qwen3-4B-Instruct-2507-GGUF/resolve/a06e946bb6b655725eafa393f4a9745d460374c9/Qwen3-4B-Instruct-2507-Q4_K_M.gguf).

The attempted repository name `Qwen/Qwen3-4B-Instruct-2507-GGUF` returned HTTP
401. This does not establish that it is public or usable without credentials;
do not describe the chosen Unsloth conversion as an official Qwen GGUF.

## Chat template and local backend

The pinned official `tokenizer_config.json` uses ordinary ChatML for plain
messages: `<|im_start|>{role}\n{content}<|im_end|>\n`, followed by
`<|im_start|>assistant\n` as the generation prefix. EOS is `<|im_end|>` and
there is no BOS token or mandatory thinking prefix. The model card explicitly
says this release only supports non-thinking mode and does not produce thinking
blocks. An explicit llama.cpp `chatml` formatter therefore matches this ordinary
message path. Passing native tool definitions would instead activate the model's
XML tool-call convention; the existing custom JSON decision contract should
remain explicit and separately validated.

The current workspace has GNU `g++`, but no `cmake`, `ninja`, `llama-cli` or
`llama-server` executable was found in PATH. Python build dependencies from PyPI
can supply CMake and Ninja. No system-level installation is needed merely to
compile a Python CPU binding. Actual build success remains to be tested.

PyPI metadata currently identifies `llama-cpp-python` **0.3.36**, distributed as
`llama_cpp_python-0.3.36.tar.gz` (**76,589,250 bytes**), source archive SHA-256
`832db0699007f1be95a7e41ef12e88926b02ba836461e36a36372db2760c1a2e`.
No binary wheel is listed in that PyPI release. Pin the version, record the build
configuration and native runtime version, set zero GPU layers and explicit CPU
thread/context settings, and retain full post-generation validation even when a
JSON grammar is enabled. Neither latency nor total process memory has yet been
measured here.

## Other verified options

| Candidate | Pinned repository revision | Selected file size | Consideration |
| --- | --- | ---: | --- |
| `unsloth/SmolLM3-3B-GGUF` | `a7bc17204c8a326d6bd6e466e076959eddae2025` | Q4_K_M 1,915,306,528 bytes | Apache-2.0 metadata; smaller, but reasoning/template behavior and task quality require separate checks. |
| `Qwen/Qwen3-8B-GGUF` | `7c41481f57cb95916b40956ab2f0b139b296d974` | Q4_K_M 5,027,783,488 bytes | Official Apache-2.0 conversion; more download and CPU work, and thinking-mode behavior needs explicit control. |
| `Qwen/Qwen2.5-7B-Instruct-GGUF` | `bb5d59e06d9551d752d08b292a50eb208b07ab1f` | Q4_K_M split into 3,993,201,344 + 689,872,288 bytes | Official Apache-2.0 conversion; viable larger fallback, but both shards must be downloaded and verified. |
| `Qwen/Qwen2.5-3B-Instruct-GGUF` | `7dabda4d13d513e3e842b20f0d435c732f172cbe` | Q4_K_M 2,104,932,768 bytes | License metadata is `other`, not Apache-2.0; smaller parameter increase than Qwen3-4B. |

The existing Qwen2.5-1.5B model remains the measured baseline. A model change,
quantization change, prompt change and validator change together form a system
comparison. Freeze the selected system before a fresh reviewed test and preserve
all invalid, blocked and failed outputs in the denominator. A faster quantized
backend or a larger model alone does not establish better decisions.
