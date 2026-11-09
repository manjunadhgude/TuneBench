"""Small public integration smoke; never a held-out accuracy estimate."""

import argparse
import json
from pathlib import Path

from tunebench.assistant import respond
from tunebench.live_model import model_status

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = Path("/workspace/models/Qwen2.5-1.5B-Instruct/989aa7980e4cf806f80c7fef2b1adb7bc71aa306")
CASES = [
    "Check the status of order TB-1001.",
    "Propose a refund for damaged order TB-1002; I have not chosen an amount.",
    "Execute a refund payment for order TB-1002.",
    "Propose a refund for order TB-1002: 2 damaged units at INR 25 each; use their combined price.",
]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "artifacts/development-v3-smoke")
    parser.add_argument("--case", type=int, choices=range(1, len(CASES) + 1), action="append")
    args = parser.parse_args()
    output = args.output
    cases = [CASES[index - 1] for index in args.case] if args.case else CASES
    output.mkdir(parents=True, exist_ok=True)
    path = output / "cases.jsonl"
    if path.exists():
        raise SystemExit("Smoke evidence already exists; choose an explicit new directory")
    with path.open("x") as handle:
        for message in cases:
            result = respond(
                message, backend="model", model_path=str(SNAPSHOT), execute_tools=False
            )
            handle.write(json.dumps(result, ensure_ascii=False) + "\n")
            handle.flush()
            print(result["status"], result["outcome"], flush=True)
    (output / "metadata.json").write_text(
        json.dumps(
            {
                "purpose": "Development integration smoke, not unseen evaluation",
                "cases": len(cases),
                "model": model_status(),
            },
            indent=2,
        )
        + "\n"
    )


if __name__ == "__main__":
    main()
