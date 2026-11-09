"""Explicit download of the pinned public CPU GGUF; verify before making it usable."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import time
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

from tunebench.gguf_model import (
    MODEL_FILENAME,
    MODEL_ID,
    MODEL_REVISION,
    MODEL_SHA256,
    MODEL_SIZE,
    UPSTREAM_MODEL_ID,
)


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(4 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True, help="Local model directory")
    args = parser.parse_args()
    target = args.output.expanduser().resolve()
    target.mkdir(parents=True, exist_ok=True)
    destination = target / MODEL_FILENAME
    started = time.monotonic()
    url = f"https://huggingface.co/{MODEL_ID}/resolve/{MODEL_REVISION}/{MODEL_FILENAME}"
    if not (
        destination.is_file()
        and destination.stat().st_size == MODEL_SIZE
        and file_hash(destination) == MODEL_SHA256
    ):
        partial = destination.with_suffix(destination.suffix + ".part")
        offset = partial.stat().st_size if partial.exists() else 0
        if offset > MODEL_SIZE:
            raise RuntimeError(
                "Oversized partial download; preserve it and choose a fresh directory"
            )
        headers = {"Range": f"bytes={offset}-"} if offset else {}
        request = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(request, timeout=120) as response:
            if offset and response.status == 206:
                if not response.headers.get("Content-Range", "").startswith(f"bytes {offset}-"):
                    raise RuntimeError("Unexpected partial-response offset")
            else:
                offset = 0
            received = offset
            checkpoint = received + 256 * 1024 * 1024
            with partial.open("ab" if offset else "wb") as handle:
                while chunk := response.read(4 * 1024 * 1024):
                    received += len(chunk)
                    if received > MODEL_SIZE:
                        raise RuntimeError("Response exceeds the pinned file size")
                    handle.write(chunk)
                    if received >= checkpoint:
                        print(f"Downloaded {received / 1024**3:.2f} GiB", flush=True)
                        checkpoint += 256 * 1024 * 1024
                handle.flush()
                os.fsync(handle.fileno())
        if received != MODEL_SIZE or file_hash(partial) != MODEL_SHA256:
            raise RuntimeError("GGUF verification failed; partial file will not be loaded")
        partial.replace(destination)
    manifest = {
        "model_id": MODEL_ID,
        "revision": MODEL_REVISION,
        "upstream_model_id": UPSTREAM_MODEL_ID,
        "publisher": "Unsloth GGUF conversion of the upstream Qwen model",
        "license": "apache-2.0",
        "filename": MODEL_FILENAME,
        "bytes": MODEL_SIZE,
        "sha256": MODEL_SHA256,
        "verified": True,
        "source_url": url,
        "verified_at_utc": datetime.now(UTC).isoformat(),
        "elapsed_seconds": time.monotonic() - started,
    }
    (target / "download-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({"verified_gguf": str(destination), **manifest}), flush=True)


if __name__ == "__main__":
    main()
