"""Strict synthetic-envelope validation for THS index history."""

from __future__ import annotations

from dataclasses import dataclass
import json
import math
from pathlib import Path
from typing import Any, Mapping

from .fingerprint import canonical_sha256

_FIXTURE_MARKER = "_aquantai_fixture_kind"
_EXPECTED_FIXTURE_KIND = "synthetic"


class SchemaValidationError(ValueError):
    """Raised when a synthetic response does not match the frozen schema."""


@dataclass(frozen=True, slots=True)
class IndexPriceBar:
    date_ms: int
    open_price: int | float
    high_price: int | float
    low_price: int | float
    close_price: int | float
    volume: int | float
    turnover: int | float


@dataclass(frozen=True, slots=True)
class IndexHistoryData:
    timestamp: int | None
    adjust: None
    item: tuple[IndexPriceBar, ...]


@dataclass(frozen=True, slots=True)
class IndexHistoryEnvelope:
    code: int
    message: str
    request_id: str | None
    data: IndexHistoryData


@dataclass(frozen=True, slots=True)
class ErrorEnvelope:
    code: int
    message: str
    request_id: str | None
    data: None


def _require_mapping(value: Any, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise SchemaValidationError(f"{name} must be an object")
    return value


def _require_exact_keys(value: Mapping[str, Any], required: set[str], optional: set[str], name: str) -> None:
    keys = set(value)
    missing = required - keys
    unknown = keys - required - optional
    if missing:
        raise SchemaValidationError(f"{name} missing required fields: {sorted(missing)}")
    if unknown:
        raise SchemaValidationError(f"{name} has unknown fields: {sorted(unknown)}")


def _require_int(value: Any, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise SchemaValidationError(f"{name} must be an integer")
    return value


def _require_number(value: Any, name: str, *, non_negative: bool = True) -> int | float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise SchemaValidationError(f"{name} must be a JSON number")
    if isinstance(value, float) and not math.isfinite(value):
        raise SchemaValidationError(f"{name} must be finite")
    if non_negative and value < 0:
        raise SchemaValidationError(f"{name} must be non-negative")
    return value


def strip_synthetic_fixture_marker(value: Mapping[str, Any]) -> dict[str, Any]:
    fixture = dict(value)
    if fixture.pop(_FIXTURE_MARKER, None) != _EXPECTED_FIXTURE_KIND:
        raise SchemaValidationError("fixture must carry the synthetic marker")
    return fixture


def load_synthetic_fixture(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as handle:
        raw = json.load(handle)
    return strip_synthetic_fixture_marker(_require_mapping(raw, "fixture"))


def validate_index_history_envelope(value: Mapping[str, Any]) -> IndexHistoryEnvelope:
    envelope = _require_mapping(value, "envelope")
    _require_exact_keys(envelope, {"code", "message", "data"}, {"request_id"}, "envelope")

    code = _require_int(envelope["code"], "code")
    if code != 0:
        raise SchemaValidationError("success envelope code must equal zero")
    message = envelope["message"]
    if not isinstance(message, str):
        raise SchemaValidationError("message must be a string")
    request_id = envelope.get("request_id")
    if request_id is not None and not isinstance(request_id, str):
        raise SchemaValidationError("request_id must be a string when present")

    data = _require_mapping(envelope["data"], "data")
    _require_exact_keys(data, {"timestamp", "adjust", "item"}, set(), "data")
    timestamp = data["timestamp"]
    if timestamp is not None:
        timestamp = _require_int(timestamp, "data.timestamp")
    if data["adjust"] is not None:
        raise SchemaValidationError("data.adjust must be null for index history")
    rows = data["item"]
    if not isinstance(rows, list):
        raise SchemaValidationError("data.item must be an array")

    parsed_rows: list[IndexPriceBar] = []
    prior_date_ms: int | None = None
    required_row_keys = {
        "date_ms",
        "open_price",
        "high_price",
        "low_price",
        "close_price",
        "volume",
        "turnover",
    }
    for index, raw_row in enumerate(rows):
        row = _require_mapping(raw_row, f"data.item[{index}]")
        _require_exact_keys(row, required_row_keys, set(), f"data.item[{index}]")
        date_ms = _require_int(row["date_ms"], f"data.item[{index}].date_ms")
        if prior_date_ms is not None and date_ms <= prior_date_ms:
            raise SchemaValidationError("data.item date_ms values must be strictly ascending")
        prior_date_ms = date_ms
        parsed_rows.append(
            IndexPriceBar(
                date_ms=date_ms,
                open_price=_require_number(row["open_price"], f"data.item[{index}].open_price"),
                high_price=_require_number(row["high_price"], f"data.item[{index}].high_price"),
                low_price=_require_number(row["low_price"], f"data.item[{index}].low_price"),
                close_price=_require_number(row["close_price"], f"data.item[{index}].close_price"),
                volume=_require_number(row["volume"], f"data.item[{index}].volume"),
                turnover=_require_number(row["turnover"], f"data.item[{index}].turnover"),
            )
        )

    return IndexHistoryEnvelope(
        code=code,
        message=message,
        request_id=request_id,
        data=IndexHistoryData(timestamp=timestamp, adjust=None, item=tuple(parsed_rows)),
    )


def validate_error_envelope(value: Mapping[str, Any]) -> ErrorEnvelope:
    envelope = _require_mapping(value, "envelope")
    _require_exact_keys(envelope, {"code", "message", "data"}, {"request_id"}, "envelope")
    code = _require_int(envelope["code"], "code")
    if code == 0:
        raise SchemaValidationError("error envelope code must be non-zero")
    message = envelope["message"]
    if not isinstance(message, str):
        raise SchemaValidationError("message must be a string")
    request_id = envelope.get("request_id")
    if request_id is not None and not isinstance(request_id, str):
        raise SchemaValidationError("request_id must be a string when present")
    if envelope["data"] is not None:
        raise SchemaValidationError("synthetic error envelope data must be null")
    return ErrorEnvelope(code=code, message=message, request_id=request_id, data=None)


INDEX_HISTORY_SCHEMA_CONTRACT = {
    "schema_version": "aquantai.ths-index-history-response.v1",
    "envelope": {
        "required": ("code", "message", "data"),
        "optional": ("request_id",),
        "types": {"code": "integer", "message": "string", "request_id": "string|null", "data": "object"},
    },
    "data": {
        "required": ("timestamp", "adjust", "item"),
        "types": {"timestamp": "integer|null", "adjust": "null", "item": "array"},
    },
    "row": {
        "required": (
            "date_ms",
            "open_price",
            "high_price",
            "low_price",
            "close_price",
            "volume",
            "turnover",
        ),
        "types": {
            "date_ms": "integer",
            "open_price": "number",
            "high_price": "number",
            "low_price": "number",
            "close_price": "number",
            "volume": "number",
            "turnover": "number",
        },
        "ordering": "date_ms strictly ascending",
    },
    "unknown_fields": "reject",
}


def index_history_schema_fingerprint() -> str:
    return canonical_sha256(INDEX_HISTORY_SCHEMA_CONTRACT)
