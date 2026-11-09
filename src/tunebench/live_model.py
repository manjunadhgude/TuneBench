"""One locked, cached local Qwen session for the interactive demonstration.

This is separate from the unchanged research runner. It never downloads weights.
"""

from __future__ import annotations

import hashlib
import re
import threading
from copy import deepcopy
from pathlib import Path
from typing import Any

from tunebench.inference import DEFAULT_MODEL
from tunebench.io import parse_json

_LOCK = threading.RLock()
_SESSION: Any = None
_SESSION_PATH: str | None = None


def verify_local_snapshot(model_path: str | Path) -> dict[str, Any]:
    """Verify retained files against the locally saved upstream-download manifest."""
    directory = Path(model_path).expanduser().resolve()
    if not directory.is_dir():
        raise ValueError("Choose an existing local Qwen snapshot directory; no downloads are run")
    manifest_path = directory / "download-manifest.json"
    if not manifest_path.is_file():
        raise ValueError("Local model is missing its download-manifest.json verification record")
    manifest = parse_json(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict) or manifest.get("model_id") != DEFAULT_MODEL:
        raise ValueError(f"The demo supports only a verified local {DEFAULT_MODEL} snapshot")
    if not re.fullmatch(r"[0-9a-f]{40}", str(manifest.get("revision", ""))):
        raise ValueError("Snapshot manifest needs a full pinned model revision")
    assets = manifest.get("files")
    if not isinstance(assets, dict) or "model.safetensors" not in assets:
        raise ValueError("Snapshot manifest must include model.safetensors")
    for name, asset in assets.items():
        if not isinstance(name, str) or Path(name).name != name:
            raise ValueError("Snapshot manifest filenames must stay inside the snapshot")
        path = directory / name
        if path.resolve().parent != directory or not path.is_file():
            raise ValueError(f"Snapshot asset is missing or outside the snapshot: {name}")
        if not isinstance(asset, dict) or path.stat().st_size != asset.get("size"):
            raise ValueError(f"Snapshot asset size mismatch: {name}")
        if asset.get("hash_algorithm") == "sha256":
            digest = hashlib.sha256()
        elif asset.get("hash_algorithm") == "git-blob-sha1":
            digest = hashlib.sha1()
            digest.update(f"blob {asset['size']}\0".encode())
        else:
            raise ValueError(f"Unsupported snapshot hash algorithm: {name}")
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(4 * 1024 * 1024), b""):
                digest.update(chunk)
        if digest.hexdigest() != asset.get("upstream_hash"):
            raise ValueError(f"Snapshot asset checksum mismatch: {name}")
    if assets["model.safetensors"].get("hash_algorithm") != "sha256":
        raise ValueError("Model weights must have a SHA-256 verification record")
    return manifest


class _LocalSession:
    def __init__(self, directory: Path, manifest: dict[str, Any]):
        try:
            import torch
            import transformers
            from transformers import AutoModelForCausalLM, AutoTokenizer, set_seed
        except ImportError as exc:
            raise RuntimeError("Install TuneBench's [model] extra to enable local Qwen") from exc
        torch.set_num_threads(4)
        set_seed(42)
        try:
            torch.set_num_interop_threads(1)
        except RuntimeError:
            # Another library may already have initialized the process thread pool.
            pass
        self.torch = torch
        self.tokenizer = AutoTokenizer.from_pretrained(
            directory, trust_remote_code=False, local_files_only=True
        )
        self.model = AutoModelForCausalLM.from_pretrained(
            directory,
            trust_remote_code=False,
            local_files_only=True,
            use_safetensors=True,
            torch_dtype=torch.float32,
        ).to("cpu")
        self.model.eval()
        self.config = deepcopy(self.model.generation_config)
        self.config.update(
            do_sample=False,
            num_beams=1,
            max_new_tokens=256,
            repetition_penalty=1.1,
            pad_token_id=(
                self.tokenizer.pad_token_id
                if self.tokenizer.pad_token_id is not None
                else self.tokenizer.eos_token_id
            ),
        )
        self.metadata = {
            "model_id": DEFAULT_MODEL,
            "resolved_model_revision": manifest["revision"],
            "weights_sha256": manifest["files"]["model.safetensors"]["upstream_hash"],
            "verification": "Local assets checked against retained upstream-download manifest",
            "device": "cpu",
            "dtype": "float32",
            "cpu_threads": torch.get_num_threads(),
            "cpu_interop_threads": torch.get_num_interop_threads(),
            "torch_version": torch.__version__,
            "transformers_version": transformers.__version__,
            "effective_generation_config": self.config.to_dict(),
            "downloads": False,
            "seed": 42,
        }

    def generate(self, messages: list[dict[str, str]]) -> str:
        inputs = self.tokenizer.apply_chat_template(
            messages, tokenize=True, add_generation_prompt=True, return_tensors="pt"
        ).to("cpu")
        limit = getattr(self.model.config, "max_position_embeddings", None)
        if limit and inputs.shape[1] + self.config.max_new_tokens > limit:
            raise ValueError("Request exceeds the local model context; shorten the input")
        with self.torch.inference_mode():
            outputs = self.model.generate(
                inputs,
                attention_mask=self.torch.ones_like(inputs),
                generation_config=self.config,
            )
        return self.tokenizer.decode(outputs[0, inputs.shape[1] :], skip_special_tokens=True)


def _load_session(directory: Path) -> _LocalSession:
    return _LocalSession(directory, verify_local_snapshot(directory))


def generate_local(messages: list[dict[str, str]], model_path: str | Path) -> str:
    """Serialize both first load and generation; only one snapshot is resident."""
    global _SESSION, _SESSION_PATH
    directory = Path(model_path).expanduser().resolve()
    with _LOCK:
        if _SESSION is None:
            session = _load_session(directory)
            _SESSION = session
            _SESSION_PATH = str(directory)
        elif _SESSION_PATH != str(directory):
            raise ValueError("A different snapshot is already loaded; restart the app to switch")
        return _SESSION.generate(messages)


def model_status() -> dict[str, Any]:
    """Inspect the cache without loading a model or checking remote services."""
    with _LOCK:
        return {
            "loaded": _SESSION is not None,
            "local_path": _SESSION_PATH,
            **(deepcopy(_SESSION.metadata) if _SESSION is not None else {}),
        }
