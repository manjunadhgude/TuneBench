import json
import subprocess
import sys


def run(*args):
    return subprocess.run(
        [sys.executable, "-m", "tunebench", *args], capture_output=True, text=True
    )


def test_rule_assistant_executes_an_actual_simulated_order_lookup():
    result = run("assist", "--message", "Check the status of order TB-1001.")
    assert result.returncode == 0, result.stderr
    value = json.loads(result.stdout)
    assert value["backend"] == "rules"
    assert value["status"] == "executed"
    assert value["tool_result"]["data"]["status"] == "shipped"
    assert value["tool_result"]["simulated"] is True


def test_missing_amount_clarifies_without_a_tool_result():
    result = run("assist", "--message", "Propose a refund for order TB-1002; it was damaged.")
    assert result.returncode == 0, result.stderr
    value = json.loads(result.stdout)
    assert value["status"] == "clarification"
    assert value["outcome"]["missing_fields"] == ["refund_amount"]
    assert value["tool_result"] is None


def test_model_prerequisite_failure_has_nonzero_exit_status():
    result = run("assist", "--backend", "model", "--message", "Check order TB-1001 status.")
    assert result.returncode == 2
    value = json.loads(result.stdout)
    assert value["status"] == "error"
    assert value["tool_result"] is None


def test_order_command_exposes_only_the_fictional_fixture():
    result = run("orders")
    assert result.returncode == 0, result.stderr
    value = json.loads(result.stdout)
    assert value["simulated"] is True
    assert {order["order_id"] for order in value["orders"]} == {
        "TB-1001",
        "TB-1002",
        "TB-1003",
        "TB-1004",
        "TB-1005",
    }
