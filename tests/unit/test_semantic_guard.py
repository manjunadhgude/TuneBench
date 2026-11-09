"""Native-adapter tests inject fake responses; they do not measure an LLM."""

import json
from pathlib import Path

import pytest

from tunebench import semantic_guard


@pytest.mark.parametrize(("amount", "has_error"), [(7.5, False), (6.75, True)])
def test_calculator_checks_supported_verdict_independently(monkeypatch, amount, has_error):
    class Fake:
        def create_chat_completion(self, **kwargs):
            assert (
                kwargs["response_format"]["schema"]["properties"]["calculation"]["type"] == "string"
            )
            return {
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                {
                                    "reason": "Injected test judgement",
                                    "calculation": "45/6",
                                    "verdict": "supported",
                                }
                            )
                        }
                    }
                ],
                "usage": {"completion_tokens": 1},
            }

    monkeypatch.setattr(
        semantic_guard,
        "verify_local_model",
        lambda _: {"model_id": "injected test", "sha256": "fake"},
    )
    monkeypatch.setattr(semantic_guard, "_MODEL", Fake())
    monkeypatch.setattr(semantic_guard, "_PATH", str(Path("/tmp/fake.gguf").resolve()))
    r = semantic_guard.verify_decision(
        "Order T-6 contained six units for 45.00; one is missing. Propose its price.",
        {
            "type": "tool_call",
            "tool_name": "propose_refund",
            "arguments": {"order_id": "T-6", "refund_amount": amount, "reason": "not_received"},
        },
        "/tmp/fake.gguf",
    )
    assert r["verdict"] == "supported"
    assert r["calculation_result"] == "7.5"
    assert bool(r["calculation_error"]) is has_error
