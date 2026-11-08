import pytest

from tunebench.io import parse_json, read_jsonl, write_jsonl


@pytest.mark.parametrize("text", ['{"a":1,"a":2}', '{"n":NaN}', '{"n":Infinity}'])
def test_ambiguous_json_is_rejected(text):
    with pytest.raises(ValueError):
        parse_json(text)


def test_jsonl_error_identifies_path_and_line(tmp_path):
    path = tmp_path / "broken.jsonl"
    path.write_text('{"ok":1}\n[1,2]\n')
    with pytest.raises(ValueError, match=r"broken.jsonl:2"):
        read_jsonl(path)


def test_unicode_jsonl_roundtrip(tmp_path):
    path = tmp_path / "nested" / "tasks.jsonl"
    rows = [{"prompt": "₹50 — café"}]
    write_jsonl(path, rows)
    assert read_jsonl(path) == rows


def test_failed_serialization_preserves_previous_output(tmp_path):
    path = tmp_path / "predictions.jsonl"
    write_jsonl(path, [{"id": "good"}])
    with pytest.raises(ValueError):
        write_jsonl(path, [{"bad": float("nan")}])
    assert read_jsonl(path) == [{"id": "good"}]
