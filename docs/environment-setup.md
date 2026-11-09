# Reusable cloud setup

At the initial onboarding checkpoint, the environment configuration tool did not
confirm saving `install_script` or `start_skill` (backend INVALID_ARGUMENT).
These retained instructions record that checkpoint; the historical tool result
does not describe the current published environment settings.

Installation script:

```bash
set -euo pipefail
cd /workspace/TuneBench
bash scripts/setup.sh
```

Startup instructions:

Use `/workspace/TuneBench`, the existing checkout. Cloud tasks are already isolated;
do not create a Git worktree unless explicitly requested. Activate `.venv` with
`source .venv/bin/activate`; run the installation script first if absent.
`python -m tunebench doctor` inspects dependencies and `bash scripts/check.sh`
validates the complete CPU workflow. No server or long-running service is required.

The optional inference workflow needs `huggingface.co` enabled in network settings.
After that change, validate a fresh model request and permit any artifact redirect
destinations it actually needs. Preserve the existing allowlist and TLS verification.
The public candidate does not require a secret. Actual CPU inference has since
been verified with the pinned local snapshot; see the
[retained smoke evidence](../artifacts/baseline-smoke/README.md). GPU LoRA/QLoRA
additionally requires a CUDA GPU and optional dependencies; no GPU training has
been run. Synthetic candidates are unreviewed/unfrozen; use validation for development.

The source setup/check scripts were executed and verified in the current machine.
Saving instructions and publishing/restoring an environment are separate actions.
