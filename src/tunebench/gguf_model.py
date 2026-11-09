"""Verified, CPU-only Qwen3 GGUF generation with no implicit downloads.

This is a third-party Unsloth quantization of the official Qwen model. A pinned
upstream file checksum identifies the exact model actually used. JSON grammar
constraints guide structure; the assistant must still validate every decision.
"""

from __future__ import annotations

import hashlib
import json
import threading
from copy import deepcopy
from importlib import metadata as package_metadata
from pathlib import Path
from typing import Any

from tunebench.structured import generation_schema

MODEL_ID = "unsloth/Qwen3-4B-Instruct-2507-GGUF"
MODEL_REVISION = "a06e946bb6b655725eafa393f4a9745d460374c9"
MODEL_FILENAME = "Qwen3-4B-Instruct-2507-Q4_K_M.gguf"
MODEL_SHA256 = "3605803b982cb64aead44f6c1b2ae36e3acdb41d8e46c8a94c6533bc4c67e597"
MODEL_SIZE = 2_497_281_120
UPSTREAM_MODEL_ID = "Qwen/Qwen3-4B-Instruct-2507"

CPU_THREADS = 4
CONTEXT_TOKENS = 8192
MAX_NEW_TOKENS = 256

_LOCK = threading.RLock()
_SESSION: Any = None
_SESSION_PATH: str | None = None
_SESSION_SIGNATURE: tuple[int, ...] | None = None


def _file_signature(path: Path) -> tuple[int, ...]:
    stat = path.stat()
    return stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns


def _model_file(model_path: str | Path) -> Path:
    path = Path(model_path).expanduser()
    if path.is_dir():
        path = path / MODEL_FILENAME
    if path.name != MODEL_FILENAME:
        raise ValueError(f"Choose the pinned {MODEL_FILENAME} file or its directory")
    if not path.is_file():
        raise ValueError("Choose an existing local GGUF model; no downloads are started")
    return path.resolve()


def _verify_file(path: Path) -> dict[str, Any]:
    before = _file_signature(path)
    if before[2] != MODEL_SIZE:
        raise ValueError("Local GGUF model size does not match the pinned upstream file")
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(4 * 1024 * 1024), b""):
            digest.update(chunk)
    if _file_signature(path) != before:
        raise ValueError("Local GGUF model changed during checksum verification")
    if digest.hexdigest() != MODEL_SHA256:
        raise ValueError("Local GGUF model checksum does not match the pinned upstream file")
    return {
        "model_id": MODEL_ID,
        "base_model_id": UPSTREAM_MODEL_ID,
        "revision": MODEL_REVISION,
        "filename": MODEL_FILENAME,
        "size": MODEL_SIZE,
        "sha256": MODEL_SHA256,
        "quantization": "Q4_K_M",
        "publisher": "Unsloth; third-party quantization of the official Qwen model",
    }


def verify_local_model(model_path: str | Path) -> dict[str, Any]:
    """Check bytes against hard-pinned upstream metadata, without importing llama.cpp."""
    return _verify_file(_model_file(model_path))


def _library_version(module: Any) -> str:
    try:
        return package_metadata.version("llama-cpp-python")
    except package_metadata.PackageNotFoundError:
        return str(getattr(module, "__version__", "unknown"))


class _LocalSession:
    def __init__(self, path: Path, verified: dict[str, Any]):
        try:
            import llama_cpp
        except ImportError as exc:
            raise RuntimeError(
                "Install TuneBench's [gguf] extra to enable the local Qwen3 CPU model"
            ) from exc
        self.schema = generation_schema()
        self.model = llama_cpp.Llama(
            model_path=str(path),
            n_ctx=CONTEXT_TOKENS,
            n_batch=512,
            n_threads=CPU_THREADS,
            n_threads_batch=CPU_THREADS,
            n_gpu_layers=0,
            offload_kqv=False,
            seed=42,
            chat_format="chatml",
            use_mmap=True,
            use_mlock=False,
            verbose=False,
        )
        # Qwen3 Instruct 2507 uses ordinary ChatML and no thinking prefix. The
        # explicit format avoids the native-tool XML wrapper: this application
        # instead requests one canonical decision object in the message content.
        self.generation = {
            "temperature": 0.0,
            "top_p": 1.0,
            "top_k": 0,
            "min_p": 0.0,
            "typical_p": 1.0,
            "repeat_penalty": 1.1,
            "frequency_penalty": 0.0,
            "presence_penalty": 0.0,
            "max_tokens": MAX_NEW_TOKENS,
            "seed": 42,
            "stream": False,
        }
        self.metadata = {
            "model_id": verified["model_id"],
            "base_model_id": verified["base_model_id"],
            "resolved_model_revision": verified["revision"],
            "weights_sha256": verified["sha256"],
            "weights_bytes": verified["size"],
            "publisher": verified["publisher"],
            "verification": "Pinned upstream SHA-256 and file size checked locally before loading",
            "backend": "llama.cpp",
            "llama_cpp_python_version": _library_version(llama_cpp),
            "device": "cpu",
            "dtype": "Q4_K_M",
            "quantization": "Q4_K_M",
            "cpu_threads": CPU_THREADS,
            "cpu_batch_threads": CPU_THREADS,
            "context_tokens": CONTEXT_TOKENS,
            "max_new_tokens": MAX_NEW_TOKENS,
            "seed": 42,
            "chat_format": "chatml",
            "thinking": False,
            "prompt_version": "strong-v4",
            "downloads": False,
            "effective_generation_config": {
                **self.generation,
                "do_sample": False,
                "num_beams": 1,
                "max_new_tokens": MAX_NEW_TOKENS,
                "repetition_penalty": 1.1,
            },
            "structured_output": {
                "enabled": True,
                "library": "llama.cpp JSON-schema grammar",
                "schema_sha256": hashlib.sha256(
                    json.dumps(self.schema, sort_keys=True).encode()
                ).hexdigest(),
                "post_validation_required": True,
            },
        }

    def generate(self, messages: list[dict[str, str]]) -> str:
        # The chat-completion adapter constructs a fresh grammar from this
        # response_format on every request. It receives no benchmark labels or
        # alternate rule-generated answers. Return its original text unchanged.
        self.metadata.pop("last_generation", None)
        response = self.model.create_chat_completion(
            messages=deepcopy(messages),
            response_format={"type": "json_object", "schema": deepcopy(self.schema)},
            **self.generation,
        )
        try:
            choice = response["choices"][0]
            raw = choice["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeError(
                "Local GGUF backend did not return a chat-completion result"
            ) from exc
        if not isinstance(raw, str):
            raise RuntimeError("Local GGUF backend did not return text content")
        self.metadata["last_generation"] = {
            "finish_reason": choice.get("finish_reason"),
            "usage": deepcopy(response.get("usage")),
        }
        return raw


def _load_session(path: Path) -> _LocalSession:
    return _LocalSession(path, _verify_file(path))


def generate_local(messages: list[dict[str, str]], model_path: str | Path) -> str:
    """Serialize loading/generation and retain one verified, local CPU model."""
    global _SESSION, _SESSION_PATH, _SESSION_SIGNATURE
    path = _model_file(model_path)
    with _LOCK:
        signature = _file_signature(path)
        if _SESSION is None:
            session = _load_session(path)
            if _file_signature(path) != signature:
                raise ValueError("Local GGUF model changed during loading; restart the app")
            _SESSION = session
            _SESSION_PATH = str(path)
            _SESSION_SIGNATURE = signature
        elif _SESSION_PATH != str(path):
            raise ValueError("A different GGUF model is already loaded; restart the app to switch")
        elif _SESSION_SIGNATURE != signature:
            raise ValueError("The loaded GGUF file changed; restart the app and verify it again")
        return _SESSION.generate(messages)


def model_status() -> dict[str, Any]:
    """Inspect the cache without loading a model, importing llama.cpp or using a network."""
    with _LOCK:
        return {
            "loaded": _SESSION is not None,
            "local_path": _SESSION_PATH,
            **(deepcopy(_SESSION.metadata) if _SESSION is not None else {}),
        }
