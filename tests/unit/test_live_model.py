import hashlib
import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor

import pytest

from tunebench import live_model
from tunebench.inference import DEFAULT_MODEL


def _snapshot(tmp_path):
    data = b"test fixture, not real model weights"
    (tmp_path / "model.safetensors").write_bytes(data)
    manifest = {
        "model_id": DEFAULT_MODEL,
        "revision": "a" * 40,
        "files": {
            "model.safetensors": {
                "size": len(data),
                "hash_algorithm": "sha256",
                "upstream_hash": hashlib.sha256(data).hexdigest(),
            }
        },
    }
    (tmp_path / "download-manifest.json").write_text(json.dumps(manifest))
    return manifest


def test_local_snapshot_checksum_is_verified_before_any_loading(tmp_path):
    manifest = _snapshot(tmp_path)
    assert live_model.verify_local_snapshot(tmp_path) == manifest
    (tmp_path / "model.safetensors").write_bytes(
        b"x" * manifest["files"]["model.safetensors"]["size"]
    )
    with pytest.raises(ValueError, match="checksum mismatch"):
        live_model.verify_local_snapshot(tmp_path)


def test_missing_verification_manifest_is_a_clear_failure(tmp_path):
    with pytest.raises(ValueError, match="download-manifest"):
        live_model.verify_local_snapshot(tmp_path)


def test_manifest_cannot_escape_snapshot(tmp_path):
    manifest = _snapshot(tmp_path)
    manifest["files"]["../outside"] = manifest["files"]["model.safetensors"]
    (tmp_path / "download-manifest.json").write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="filenames"):
        live_model.verify_local_snapshot(tmp_path)


def test_one_cached_session_serializes_generation_and_prevents_double_load(monkeypatch, tmp_path):
    monkeypatch.setattr(live_model, "_SESSION", None)
    monkeypatch.setattr(live_model, "_SESSION_PATH", None)
    loads = []
    active = 0
    maximum_active = 0
    counter_lock = threading.Lock()

    class FakeSession:
        metadata = {"model_id": "unit test fake session"}

        def generate(self, messages):
            nonlocal active, maximum_active
            with counter_lock:
                active += 1
                maximum_active = max(maximum_active, active)
            time.sleep(0.005)
            with counter_lock:
                active -= 1
            return messages[0]["content"]

    def load(path):
        loads.append(path)
        return FakeSession()

    monkeypatch.setattr(live_model, "_load_session", load)
    with ThreadPoolExecutor(max_workers=4) as pool:
        outputs = list(
            pool.map(
                lambda value: live_model.generate_local(
                    [{"role": "user", "content": value}], tmp_path
                ),
                ["one", "two", "three", "four"],
            )
        )
    assert outputs == ["one", "two", "three", "four"]
    assert loads == [tmp_path]
    assert maximum_active == 1
    assert live_model.model_status()["loaded"] is True
    with pytest.raises(ValueError, match="different snapshot"):
        live_model.generate_local([], tmp_path / "other")


def test_model_status_does_not_initialize_session(monkeypatch):
    monkeypatch.setattr(live_model, "_SESSION", None)
    monkeypatch.setattr(live_model, "_SESSION_PATH", None)
    assert live_model.model_status() == {"loaded": False, "local_path": None}
