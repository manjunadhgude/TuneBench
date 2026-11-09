"""Backend plumbing tests use synthetic bytes and fake generation, never model inference."""

import builtins
import hashlib
import json
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from types import SimpleNamespace

import pytest

from tunebench import gguf_model
from tunebench.structured import generation_schema


def test_installed_native_grammar_accepts_canonical_decision_schema():
    library = pytest.importorskip("llama_cpp")
    grammar = library.LlamaGrammar.from_json_schema(json.dumps(generation_schema()), verbose=False)
    assert grammar is not None


@pytest.fixture(autouse=True)
def empty_cache(monkeypatch):
    monkeypatch.setattr(gguf_model, "_SESSION", None)
    monkeypatch.setattr(gguf_model, "_SESSION_PATH", None)
    monkeypatch.setattr(gguf_model, "_SESSION_SIGNATURE", None)


@pytest.fixture
def model_file(tmp_path, monkeypatch):
    # This fixture explicitly changes the expected byte identity. It does not
    # create real GGUF weights or claim that model inference was performed.
    data = b"GGUF synthetic unit-test fixture, not real model weights"
    path = tmp_path / gguf_model.MODEL_FILENAME
    path.write_bytes(data)
    monkeypatch.setattr(gguf_model, "MODEL_SIZE", len(data))
    monkeypatch.setattr(gguf_model, "MODEL_SHA256", hashlib.sha256(data).hexdigest())
    return path


@pytest.fixture
def fake_library(monkeypatch):
    captures = {"loads": [], "requests": []}

    class FakeLlama:
        def __init__(self, **kwargs):
            captures["loads"].append(kwargs)

        def create_chat_completion(self, **kwargs):
            captures["requests"].append(deepcopy(kwargs))
            return {
                "choices": [
                    {
                        "message": {
                            "content": ' {"type":"no_tool","reason_code":"no_action_requested"} '
                        },
                        "finish_reason": "stop",
                    }
                ],
                "usage": {"prompt_tokens": 10, "completion_tokens": 15, "total_tokens": 25},
            }

    module = SimpleNamespace(Llama=FakeLlama, __version__="0.0.synthetic")
    monkeypatch.setitem(sys.modules, "llama_cpp", module)
    monkeypatch.setattr(gguf_model, "_library_version", lambda _: "0.0.synthetic")
    return captures, module


def test_verification_uses_pinned_bytes_and_preserves_third_party_provenance(model_file):
    info = gguf_model.verify_local_model(model_file)
    assert info["model_id"] == "unsloth/Qwen3-4B-Instruct-2507-GGUF"
    assert info["base_model_id"] == "Qwen/Qwen3-4B-Instruct-2507"
    assert info["revision"] == "a06e946bb6b655725eafa393f4a9745d460374c9"
    assert info["sha256"] == hashlib.sha256(model_file.read_bytes()).hexdigest()
    assert "third-party" in info["publisher"]
    assert gguf_model.verify_local_model(model_file.parent) == info


def test_wrong_size_is_rejected_before_backend_loading(model_file, fake_library):
    model_file.write_bytes(b"short")
    with pytest.raises(ValueError, match="size"):
        gguf_model.generate_local([], model_file)
    assert fake_library[0]["loads"] == []


def test_same_size_wrong_checksum_is_rejected_before_loading(model_file, fake_library):
    model_file.write_bytes(b"x" * model_file.stat().st_size)
    with pytest.raises(ValueError, match="checksum"):
        gguf_model.generate_local([], model_file)
    assert fake_library[0]["loads"] == []


def test_arbitrary_file_is_not_treated_as_an_approved_gguf(model_file):
    other = model_file.with_name("unverified.gguf")
    other.write_bytes(model_file.read_bytes())
    with pytest.raises(ValueError, match="pinned"):
        gguf_model.verify_local_model(other)


def test_missing_file_does_not_attempt_to_download_or_import_backend(tmp_path, monkeypatch):
    original = builtins.__import__

    def guarded(name, *args, **kwargs):
        if name.startswith(("llama_cpp", "huggingface_hub", "requests")):
            raise AssertionError("Missing local files must not trigger backend/network imports")
        return original(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", guarded)
    with pytest.raises(ValueError, match="existing local"):
        gguf_model.generate_local([], tmp_path / gguf_model.MODEL_FILENAME)
    assert gguf_model.model_status() == {"loaded": False, "local_path": None}


def test_verification_and_status_do_not_require_optional_backend(model_file, monkeypatch):
    original = builtins.__import__

    def guarded(name, *args, **kwargs):
        if name.startswith("llama_cpp"):
            raise ImportError("optional dependency absent")
        return original(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", guarded)
    assert gguf_model.verify_local_model(model_file)["size"] == model_file.stat().st_size
    with pytest.raises(RuntimeError, match=r"\[gguf\] extra"):
        gguf_model.generate_local([], model_file)
    assert gguf_model.model_status()["loaded"] is False


def test_cpu_settings_actual_parameters_and_raw_text_are_retained(model_file, fake_library):
    messages = [{"role": "user", "content": "Thanks."}]
    before = deepcopy(messages)
    raw = gguf_model.generate_local(messages, model_file)
    assert raw == ' {"type":"no_tool","reason_code":"no_action_requested"} '
    assert messages == before
    captured, _ = fake_library
    load = captured["loads"][0]
    assert load["model_path"] == str(model_file)
    assert load["n_gpu_layers"] == 0
    assert load["offload_kqv"] is False
    assert load["n_threads"] == load["n_threads_batch"] == 4
    assert load["n_ctx"] == 8192
    assert load["chat_format"] == "chatml"
    request = captured["requests"][0]
    assert "tools" not in request
    assert request["temperature"] == 0
    assert request["top_p"] == 1
    assert request["top_k"] == request["min_p"] == 0
    assert request["max_tokens"] == 256
    assert request["repeat_penalty"] == 1.1
    assert request["seed"] == 42
    assert request["stream"] is False
    assert request["response_format"]["type"] == "json_object"
    assert request["response_format"]["schema"] == gguf_model.generation_schema()
    status = gguf_model.model_status()
    assert status["backend"] == "llama.cpp"
    assert status["downloads"] is False
    assert status["thinking"] is False
    assert status["weights_sha256"] == hashlib.sha256(model_file.read_bytes()).hexdigest()
    assert status["llama_cpp_python_version"] == "0.0.synthetic"
    assert status["structured_output"]["post_validation_required"] is True
    assert status["last_generation"]["usage"]["completion_tokens"] == 15


def test_schema_and_messages_are_fresh_for_each_generation(model_file, fake_library):
    _, module = fake_library
    seen = []

    class MutatingBackend:
        def __init__(self, **_kwargs):
            pass

        def create_chat_completion(self, **kwargs):
            seen.append(deepcopy(kwargs))
            kwargs["messages"][0]["content"] = "changed by backend"
            kwargs["response_format"]["schema"].clear()
            return {"choices": [{"message": {"content": "unmodified original backend text"}}]}

    module.Llama = MutatingBackend
    messages = [{"role": "user", "content": "Original request"}]
    for _ in range(2):
        assert gguf_model.generate_local(messages, model_file) == "unmodified original backend text"
    assert messages[0]["content"] == "Original request"
    assert seen[0]["response_format"]["schema"] == seen[1]["response_format"]["schema"]
    assert seen[1]["response_format"]["schema"]["oneOf"]


@pytest.mark.parametrize(
    ("response", "error"),
    [
        ({}, "chat-completion"),
        ({"choices": []}, "chat-completion"),
        ({"choices": [{"message": {"content": None}}]}, "text content"),
    ],
)
def test_malformed_backend_results_fail_explicitly(model_file, fake_library, response, error):
    _, module = fake_library

    class BadBackend:
        def __init__(self, **_kwargs):
            pass

        def create_chat_completion(self, **_kwargs):
            return response

    module.Llama = BadBackend
    with pytest.raises(RuntimeError, match=error):
        gguf_model.generate_local([], model_file)


def test_one_cached_session_serializes_concurrent_generations(model_file, monkeypatch):
    loads = []
    active = 0
    maximum = 0
    counter_lock = threading.Lock()

    class FakeSession:
        metadata = {"backend": "unit-test fake, not inference"}

        def generate(self, messages):
            nonlocal active, maximum
            with counter_lock:
                active += 1
                maximum = max(maximum, active)
            time.sleep(0.005)
            with counter_lock:
                active -= 1
            return messages[0]["content"]

    def load(path):
        loads.append(path)
        return FakeSession()

    monkeypatch.setattr(gguf_model, "_load_session", load)
    with ThreadPoolExecutor(max_workers=4) as pool:
        result = list(
            pool.map(
                lambda text: gguf_model.generate_local(
                    [{"role": "user", "content": text}], model_file
                ),
                ["one", "two", "three", "four"],
            )
        )
    assert result == ["one", "two", "three", "four"]
    assert loads == [model_file]
    assert maximum == 1


def test_switching_or_modifying_a_loaded_file_requires_restart(model_file, fake_library, tmp_path):
    gguf_model.generate_local([], model_file)
    other_dir = tmp_path / "other"
    other_dir.mkdir()
    other = other_dir / model_file.name
    other.write_bytes(model_file.read_bytes())
    with pytest.raises(ValueError, match="different GGUF"):
        gguf_model.generate_local([], other)
    model_file.write_bytes(b"x" * model_file.stat().st_size)
    with pytest.raises(ValueError, match="file changed"):
        gguf_model.generate_local([], model_file)


def test_status_is_a_copy_and_does_not_allow_metadata_mutation(model_file, fake_library):
    gguf_model.generate_local([], model_file)
    status = gguf_model.model_status()
    status["last_generation"]["usage"]["completion_tokens"] = -1
    assert gguf_model.model_status()["last_generation"]["usage"]["completion_tokens"] == 15
