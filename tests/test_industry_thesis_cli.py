import json

import pytest

from industry_alpha.industry_thesis_cli import MAX_INPUT_BYTES, _load
from industry_alpha.industry_thesis_rules import IndustryThesisError


def test_cli_loads_only_utf8_json_objects(tmp_path) -> None:
    valid = tmp_path / "valid.json"
    valid.write_text(json.dumps({"driver_type": "unknown"}), encoding="utf-8")
    assert _load(valid) == {"driver_type": "unknown"}

    array = tmp_path / "array.json"
    array.write_text("[]", encoding="utf-8")
    with pytest.raises(IndustryThesisError, match="JSON object"):
        _load(array)


def test_cli_rejects_input_over_one_mib(tmp_path) -> None:
    oversized = tmp_path / "oversized.json"
    oversized.write_bytes(b"{" + b" " * MAX_INPUT_BYTES + b"}")
    with pytest.raises(IndustryThesisError, match="1 MiB"):
        _load(oversized)
