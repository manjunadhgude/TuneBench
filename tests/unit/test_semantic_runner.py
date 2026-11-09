import importlib.util
from pathlib import Path

PATH = Path(__file__).resolve().parents[2] / "scripts/compare_semantic_versions.py"
spec = importlib.util.spec_from_file_location("semantic_runner_test", PATH)
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


def test_review_generations_are_included_in_total_cost():
    tasks = [{"example_id": "x"}]
    case = {
        "example_id": "x",
        "raw_first_prediction": {"example_id": "x", "outcome": None},
        "final_prediction": {"example_id": "x", "outcome": None},
        "response": {
            "status": "blocked",
            "elapsed_ms": 10,
            "attempts": [{}, {}],
            "semantic_verifications": [{}, {}],
        },
    }
    r = runner.score_cases(tasks, [case], lambda *_: {})["pipeline"]
    assert r["generation_attempts"] == 2
    assert r["review_generations"] == 2
    assert r["total_generation_records"] == 4
