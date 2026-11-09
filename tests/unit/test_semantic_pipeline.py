import json

from tunebench.assistant import respond

PATH = "/missing/Qwen3-4B-Instruct-2507-Q4_K_M.gguf"
CALL = {"type": "tool_call", "tool_name": "get_order_status", "arguments": {"order_id": "TB-1001"}}


def test_supported_review_preserves_original_decision_and_records_verdict():
    r = respond(
        "Check order TB-1001 status.",
        model_path=PATH,
        generate=lambda _: json.dumps(CALL),
        verify=lambda *_: {
            "verdict": "supported",
            "reason": "Explicit status request",
            "kind": "injected_test",
        },
        execute_tools=False,
    )
    assert r["backend"] == "injected"
    assert r["accepted_outcome"] == CALL
    assert r["semantic_verifications"][0]["verdict"] == "supported"
    assert r["tool_result"] is None


def test_contradicted_review_blocks_without_rewriting_model_answer():
    r = respond(
        "Check order TB-1001 status.",
        model_path=PATH,
        generate=lambda _: json.dumps(CALL),
        verify=lambda *_: {
            "verdict": "contradicted",
            "reason": "Test rejection",
            "kind": "injected_test",
        },
        execute_tools=False,
    )
    assert r["status"] == "blocked"
    assert r["outcome"] == CALL and r["accepted_outcome"] is None
    assert len(r["attempts"]) == 2


def test_review_backend_failure_is_an_error_and_never_executes():
    def fail(*_):
        raise RuntimeError("injected verifier unavailable")

    r = respond(
        "Check order TB-1001 status.",
        model_path=PATH,
        generate=lambda _: json.dumps(CALL),
        verify=fail,
    )
    assert r["status"] == "error"
    assert r["tool_result"] is None and r["accepted_outcome"] is None
