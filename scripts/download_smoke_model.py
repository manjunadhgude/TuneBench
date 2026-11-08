"""Download the pinned public model with upstream content-hash verification."""

import argparse
import hashlib
import json
import os
import time
import urllib.request
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--output", type=Path, required=True)
args = parser.parse_args()
project_root = Path(__file__).resolve().parents[1]
metadata = json.loads(
    (project_root / "artifacts/baseline-smoke/upstream-model-metadata.json").read_text()
)
model_id = metadata["id"]
revision = metadata["sha"]
target = args.output
target.mkdir(parents=True, exist_ok=True)
selected = {
    "config.json",
    "generation_config.json",
    "tokenizer.json",
    "tokenizer_config.json",
    "vocab.json",
    "merges.txt",
    "model.safetensors",
    "LICENSE",
    "README.md",
}
manifest = {
    "model_id": model_id,
    "revision": revision,
    "license": metadata.get("cardData", {}).get("license"),
    "files": {},
}
start = time.monotonic()
downloaded_any = False
for entry in metadata["siblings"]:
    filename = entry["rfilename"]
    if filename not in selected:
        continue
    path = target / filename
    lfs = entry.get("lfs")
    expected = lfs["sha256"] if lfs else entry["blobId"]
    size = entry["size"]

    def hasher(lfs=lfs, size=size):
        digest = hashlib.sha256() if lfs else hashlib.sha1()
        if not lfs:
            digest.update(f"blob {size}\0".encode())
        return digest

    existing = hasher()
    if path.exists() and path.stat().st_size == size:
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(4 * 1024 * 1024), b""):
                existing.update(chunk)
    if not path.exists() or existing.hexdigest() != expected:
        downloaded_any = True
        print(f"Downloading {filename} ({size:,} bytes)", flush=True)
        partial = path.with_name(path.name + ".part")
        digest = hasher()
        received = 0
        checkpoint = 256 * 1024 * 1024
        request = urllib.request.Request(
            f"https://huggingface.co/{model_id}/resolve/{revision}/{filename}"
        )
        with urllib.request.urlopen(request, timeout=60) as response, partial.open("wb") as handle:
            while chunk := response.read(4 * 1024 * 1024):
                handle.write(chunk)
                digest.update(chunk)
                received += len(chunk)
                if received >= checkpoint:
                    print(f"{filename}: {received / 1024**3:.2f} GiB received", flush=True)
                    checkpoint += 256 * 1024 * 1024
        if received != size or digest.hexdigest() != expected:
            raise RuntimeError(
                f"Content verification failed for {filename}; do not use partial file"
            )
        os.replace(partial, path)
    manifest["files"][filename] = {
        "size": size,
        "upstream_hash": expected,
        "hash_algorithm": "sha256" if lfs else "git-blob-sha1",
        "verified": True,
    }
    print(f"Verified {filename}", flush=True)
if not selected <= manifest["files"].keys():
    raise RuntimeError("Missing required model assets")
manifest["download_seconds"] = time.monotonic() - start
if downloaded_any or not (target / "download-manifest.json").exists():
    (target / "download-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
print(
    json.dumps(
        {
            "verified_model_directory": str(target),
            "revision": revision,
            "seconds": manifest["download_seconds"],
        }
    ),
    flush=True,
)
