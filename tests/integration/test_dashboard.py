"""Exercise the optional Streamlit UI without downloading or running a model."""

from pathlib import Path

import pytest

pytest.importorskip("streamlit")
from streamlit.testing.v1 import AppTest

APP = Path(__file__).resolve().parents[2] / "app.py"


def test_missing_predictions_are_not_subtracted_twice_from_valid_count():
    from tunebench.dashboard import report_summary

    report = {
        "total_examples": 4,
        "task_success": {"correct": 1},
        "outcome_accuracy": {"correct": 2},
        "invalid_predictions": 2,
        "missing_predictions": 1,
    }
    assert report_summary(report)["valid_predictions"] == 2


def open_app():
    app = AppTest.from_file(str(APP)).run(timeout=15)
    assert not app.exception
    return app


def test_quick_demo_executes_a_real_mock_tool():
    app = open_app()
    app.text_area(key="request_text").set_value("Check the status of order TB-1001.")
    app.button(key="run_request").click().run()
    assert not app.exception
    result = app.session_state["last_result"]
    assert result["backend"] == "rules"
    assert result["status"] == "executed"
    assert result["outcome"]["tool_name"] == "get_order_status"
    assert result["tool_result"]["simulated"] is True


def test_missing_refund_amount_shows_clarification_without_tool_execution():
    app = open_app()
    app.text_area(key="request_text").set_value(
        "Propose a simulated refund for order TB-1002 because the item arrived damaged. "
        "I have not specified a refund amount."
    )
    app.button(key="run_request").click().run()
    assert not app.exception
    result = app.session_state["last_result"]
    assert result["status"] == "clarification"
    assert result["outcome"]["missing_fields"] == ["refund_amount"]
    assert result["tool_result"] is None


def test_invalid_injected_output_is_visible_and_not_executed(monkeypatch):
    from tunebench import assistant

    original = assistant.respond

    def invalid_backend(message, **kwargs):
        return original(message, generate=lambda _messages: "not JSON", max_repairs=0)

    monkeypatch.setattr(assistant, "respond", invalid_backend)
    app = open_app()
    app.button(key="run_request").click().run()
    assert not app.exception
    result = app.session_state["last_result"]
    assert result["status"] in {"blocked", "error"}
    assert result["tool_result"] is None
    assert result["attempts"][0]["raw_output"] == "not JSON"
    assert result["validation_errors"]


def test_replay_uses_only_selected_saved_input_without_live_backend(monkeypatch):
    from tunebench import assistant

    def forbidden_backend(*args, **kwargs):
        raise AssertionError("Replay must not run an inference backend")

    monkeypatch.setattr(assistant, "respond", forbidden_backend)
    app = open_app()
    app.selectbox(key="run_mode").select("Saved model replay").run()
    app.selectbox(key="replay_index").select(7).run()
    app.button(key="run_request").click().run()
    assert not app.exception
    result = app.session_state["last_result"]
    assert result["status"] == "recorded"
    assert result["backend"] == "recorded model replay"
    assert result["tool_result"] is None
    assert result["validation_errors"]  # This saved output has an invalid outcome tag.


def test_blank_request_is_not_submitted():
    app = open_app()
    app.text_area(key="request_text").set_value("   ").run()
    assert app.button(key="run_request").disabled
    assert "last_result" not in app.session_state
