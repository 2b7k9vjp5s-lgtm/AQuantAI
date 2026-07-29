"""Strict source-envelope and coverage validation for THS daily-market Slice A."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import Enum
import json
import math
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping

from .fingerprint import canonical_sha256
from .live_contracts import SOURCE_KEY, DailyMarketCapability
from .live_planner import CAPABILITY_PLANNING_REGISTRY
from .live_selectors import (
    AShareDailySelector,
    BenchmarkDailySelector,
    HistoricalBlockSnapshotSelector,
    ListedInstrumentSelector,
    LiveDailyMarketSelector,
    TradingCalendarSelector,
)


_FIXTURE_MARKER = "_aquantai_fixture_kind"
_EXPECTED_FIXTURE_KIND = "synthetic"
_ALLOWED_LISTING_STATUSES = {"listed", "suspended", "delisted"}


class LiveResponseFailureCode(str, Enum):
    SCHEMA_MISMATCH = "THS_DAILY_MARKET_SCHEMA_MISMATCH"
    SOURCE_MISMATCH = "THS_DAILY_MARKET_SOURCE_MISMATCH"
    CAPABILITY_MISMATCH = "THS_DAILY_MARKET_CAPABILITY_MISMATCH"
    IDENTITY_MISMATCH = "THS_DAILY_MARKET_IDENTITY_MISMATCH"
    DATE_MISMATCH = "THS_DAILY_MARKET_DATE_MISMATCH"
    COVERAGE_INCOMPLETE = "THS_DAILY_MARKET_COVERAGE_INCOMPLETE"
    DUPLICATE_NATURAL_KEY = "THS_DAILY_MARKET_DUPLICATE_NATURAL_KEY"
    ORDERING_INVALID = "THS_DAILY_MARKET_ORDERING_INVALID"
    OHLC_INVALID = "THS_DAILY_MARKET_OHLC_INVALID"
    UNSUPPORTED_CAPABILITY = "THS_DAILY_MARKET_UNSUPPORTED_CAPABILITY"


class LiveResponseValidationError(ValueError):
    def __init__(self, message: str, reason_code: LiveResponseFailureCode) -> None:
        self.reason_code = reason_code
        super().__init__(message)


FrozenPrimitive = str | int | float | bool | None
FrozenRow = tuple[tuple[str, FrozenPrimitive], ...]


@dataclass(frozen=True, slots=True)
class ValidatedLiveResponse:
    source_key: str
    capability: DailyMarketCapability
    schema_version: str
    item_count: int
    covered_sessions: tuple[str, ...]
    normalized_items: tuple[FrozenRow, ...]
    content_fingerprint: str

    def items_as_dicts(self) -> tuple[dict[str, FrozenPrimitive], ...]:
        return tuple(dict(item) for item in self.normalized_items)

    def public_summary(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "source_key": self.source_key,
                "capability": self.capability.value,
                "schema_version": self.schema_version,
                "item_count": self.item_count,
                "covered_sessions": self.covered_sessions,
                "content_fingerprint": self.content_fingerprint,
            }
        )


def _require_mapping(value: Any, field_name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise LiveResponseValidationError(
            f"{field_name} must be an object",
            LiveResponseFailureCode.SCHEMA_MISMATCH,
        )
    return value


def _require_exact_keys(
    value: Mapping[str, Any],
    required: set[str],
    optional: set[str],
    field_name: str,
) -> None:
    keys = set(value)
    missing = required - keys
    unknown = keys - required - optional
    if missing:
        raise LiveResponseValidationError(
            f"{field_name} missing required fields: {sorted(missing)}",
            LiveResponseFailureCode.SCHEMA_MISMATCH,
        )
    if unknown:
        raise LiveResponseValidationError(
            f"{field_name} has unknown fields: {sorted(unknown)}",
            LiveResponseFailureCode.SCHEMA_MISMATCH,
        )


def _require_text(value: Any, field_name: str, *, allow_empty: bool = False) -> str:
    if not isinstance(value, str):
        raise LiveResponseValidationError(
            f"{field_name} must be a string",
            LiveResponseFailureCode.SCHEMA_MISMATCH,
        )
    normalized = value.strip()
    if not allow_empty and not normalized:
        raise LiveResponseValidationError(
            f"{field_name} must not be empty",
            LiveResponseFailureCode.SCHEMA_MISMATCH,
        )
    return normalized


def _require_date_text(value: Any, field_name: str) -> str:
    normalized = _require_text(value, field_name)
    try:
        parsed = date.fromisoformat(normalized)
    except ValueError as exc:
        raise LiveResponseValidationError(
            f"{field_name} must be an ISO date",
            LiveResponseFailureCode.SCHEMA_MISMATCH,
        ) from exc
    if parsed.isoformat() != normalized:
        raise LiveResponseValidationError(
            f"{field_name} must use canonical ISO date form",
            LiveResponseFailureCode.SCHEMA_MISMATCH,
        )
    return normalized


def _require_number(
    value: Any,
    field_name: str,
    *,
    strictly_positive: bool = False,
    non_negative: bool = False,
) -> int | float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise LiveResponseValidationError(
            f"{field_name} must be a JSON number",
            LiveResponseFailureCode.SCHEMA_MISMATCH,
        )
    if isinstance(value, float) and not math.isfinite(value):
        raise LiveResponseValidationError(
            f"{field_name} must be finite",
            LiveResponseFailureCode.SCHEMA_MISMATCH,
        )
    if strictly_positive and value <= 0:
        raise LiveResponseValidationError(
            f"{field_name} must be positive",
            LiveResponseFailureCode.OHLC_INVALID,
        )
    if non_negative and value < 0:
        raise LiveResponseValidationError(
            f"{field_name} must be non-negative",
            LiveResponseFailureCode.OHLC_INVALID,
        )
    return value


def _freeze_row(row: Mapping[str, FrozenPrimitive]) -> FrozenRow:
    return tuple((key, row[key]) for key in sorted(row))


def _reject_duplicate_keys(keys: list[tuple[object, ...]], field_name: str) -> None:
    if len(set(keys)) != len(keys):
        raise LiveResponseValidationError(
            f"{field_name} contains duplicate or conflicting natural keys",
            LiveResponseFailureCode.DUPLICATE_NATURAL_KEY,
        )


def strip_synthetic_live_fixture_marker(value: Mapping[str, Any]) -> dict[str, Any]:
    fixture = dict(value)
    if fixture.pop(_FIXTURE_MARKER, None) != _EXPECTED_FIXTURE_KIND:
        raise LiveResponseValidationError(
            "fixture must carry the exact synthetic marker",
            LiveResponseFailureCode.SCHEMA_MISMATCH,
        )
    return fixture


def load_synthetic_live_fixture(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    return strip_synthetic_live_fixture_marker(_require_mapping(value, "fixture"))


def _validate_envelope(
    selector: LiveDailyMarketSelector,
    value: Mapping[str, Any],
) -> tuple[str, list[Any]]:
    envelope = _require_mapping(value, "envelope")
    _require_exact_keys(envelope, {"code", "message", "data"}, {"request_id"}, "envelope")
    code = envelope["code"]
    if isinstance(code, bool) or not isinstance(code, int) or code != 0:
        raise LiveResponseValidationError(
            "success envelope code must equal zero",
            LiveResponseFailureCode.SCHEMA_MISMATCH,
        )
    _require_text(envelope["message"], "message", allow_empty=True)
    if "request_id" in envelope and envelope["request_id"] is not None:
        _require_text(envelope["request_id"], "request_id")

    data = _require_mapping(envelope["data"], "data")
    _require_exact_keys(
        data,
        {"source_key", "capability", "schema_version", "items"},
        set(),
        "data",
    )
    source_key = _require_text(data["source_key"], "data.source_key")
    if source_key != SOURCE_KEY:
        raise LiveResponseValidationError(
            "response source_key does not match the selected source authority",
            LiveResponseFailureCode.SOURCE_MISMATCH,
        )
    capability = _require_text(data["capability"], "data.capability")
    if capability != selector.capability.value:
        raise LiveResponseValidationError(
            "response capability does not match the request selector",
            LiveResponseFailureCode.CAPABILITY_MISMATCH,
        )
    contract = CAPABILITY_PLANNING_REGISTRY[selector.capability]
    schema_version = _require_text(data["schema_version"], "data.schema_version")
    if schema_version != contract.response_schema_version:
        raise LiveResponseValidationError(
            "response schema_version does not match the closed capability contract",
            LiveResponseFailureCode.SCHEMA_MISMATCH,
        )
    items = data["items"]
    if not isinstance(items, list):
        raise LiveResponseValidationError(
            "data.items must be an array",
            LiveResponseFailureCode.SCHEMA_MISMATCH,
        )
    return schema_version, items


def _validate_listed_instruments(
    selector: ListedInstrumentSelector,
    items: list[Any],
) -> tuple[tuple[FrozenRow, ...], tuple[str, ...]]:
    required = {
        "provider_symbol",
        "stock_code",
        "stock_name",
        "exchange",
        "listing_date",
        "status",
    }
    normalized: list[dict[str, FrozenPrimitive]] = []
    natural_keys: list[tuple[object, ...]] = []
    ordered_keys: list[str] = []
    for index, raw in enumerate(items):
        row = _require_mapping(raw, f"data.items[{index}]")
        _require_exact_keys(row, required, set(), f"data.items[{index}]")
        provider_symbol = _require_text(row["provider_symbol"], f"data.items[{index}].provider_symbol")
        stock_code = _require_text(row["stock_code"], f"data.items[{index}].stock_code")
        exchange = _require_text(row["exchange"], f"data.items[{index}].exchange")
        identity_key = f"{exchange}:{stock_code}:{provider_symbol}"
        listing_date = row["listing_date"]
        if listing_date is not None:
            listing_date = _require_date_text(listing_date, f"data.items[{index}].listing_date")
            if listing_date > selector.as_of_date.isoformat():
                raise LiveResponseValidationError(
                    "listing_date exceeds selector as_of_date",
                    LiveResponseFailureCode.DATE_MISMATCH,
                )
        status = _require_text(row["status"], f"data.items[{index}].status")
        if status not in _ALLOWED_LISTING_STATUSES:
            raise LiveResponseValidationError(
                "status is outside the closed listing-status set",
                LiveResponseFailureCode.SCHEMA_MISMATCH,
            )
        normalized.append(
            {
                "provider_symbol": provider_symbol,
                "stock_code": stock_code,
                "stock_name": _require_text(row["stock_name"], f"data.items[{index}].stock_name"),
                "exchange": exchange,
                "listing_date": listing_date,
                "status": status,
            }
        )
        natural_keys.append((identity_key,))
        ordered_keys.append(identity_key)
    _reject_duplicate_keys(natural_keys, "listed instrument response")
    if ordered_keys != sorted(ordered_keys):
        raise LiveResponseValidationError(
            "listed instrument rows must be sorted by identity key",
            LiveResponseFailureCode.ORDERING_INVALID,
        )
    expected = {item.identity_key for item in selector.identities}
    observed = set(ordered_keys)
    if observed != expected:
        raise LiveResponseValidationError(
            f"listed instrument identity coverage mismatch; missing={sorted(expected-observed)}, "
            f"unexpected={sorted(observed-expected)}",
            LiveResponseFailureCode.IDENTITY_MISMATCH,
        )
    return tuple(_freeze_row(row) for row in normalized), (selector.as_of_date.isoformat(),)


def _validate_trade_calendar(
    selector: TradingCalendarSelector,
    items: list[Any],
) -> tuple[tuple[FrozenRow, ...], tuple[str, ...]]:
    required = {"exchange", "trade_date", "is_open"}
    normalized: list[dict[str, FrozenPrimitive]] = []
    dates: list[str] = []
    natural_keys: list[tuple[object, ...]] = []
    for index, raw in enumerate(items):
        row = _require_mapping(raw, f"data.items[{index}]")
        _require_exact_keys(row, required, set(), f"data.items[{index}]")
        exchange = _require_text(row["exchange"], f"data.items[{index}].exchange")
        if exchange != selector.exchange.value:
            raise LiveResponseValidationError(
                "trade-calendar exchange does not match selector",
                LiveResponseFailureCode.IDENTITY_MISMATCH,
            )
        trade_date = _require_date_text(row["trade_date"], f"data.items[{index}].trade_date")
        if not isinstance(row["is_open"], bool):
            raise LiveResponseValidationError(
                "trade-calendar is_open must be a boolean",
                LiveResponseFailureCode.SCHEMA_MISMATCH,
            )
        normalized.append(
            {"exchange": exchange, "trade_date": trade_date, "is_open": row["is_open"]}
        )
        dates.append(trade_date)
        natural_keys.append((exchange, trade_date))
    _reject_duplicate_keys(natural_keys, "trade-calendar response")
    if dates != sorted(dates):
        raise LiveResponseValidationError(
            "trade-calendar rows must be sorted by trade_date",
            LiveResponseFailureCode.ORDERING_INVALID,
        )
    expected = {item.isoformat() for item in selector.requested_dates}
    observed = set(dates)
    if observed != expected:
        raise LiveResponseValidationError(
            f"trade-calendar date coverage mismatch; missing={sorted(expected-observed)}, "
            f"unexpected={sorted(observed-expected)}",
            LiveResponseFailureCode.COVERAGE_INCOMPLETE,
        )
    return tuple(_freeze_row(row) for row in normalized), tuple(dates)


def _validate_ohlc(
    row: Mapping[str, Any],
    field_prefix: str,
) -> tuple[int | float, int | float, int | float, int | float, int | float, int | float]:
    open_value = _require_number(row["open"], f"{field_prefix}.open", strictly_positive=True)
    high_value = _require_number(row["high"], f"{field_prefix}.high", strictly_positive=True)
    low_value = _require_number(row["low"], f"{field_prefix}.low", strictly_positive=True)
    close_value = _require_number(row["close"], f"{field_prefix}.close", strictly_positive=True)
    volume = _require_number(row["volume"], f"{field_prefix}.volume", non_negative=True)
    amount = _require_number(row["amount"], f"{field_prefix}.amount", non_negative=True)
    if high_value < max(open_value, low_value, close_value) or low_value > min(
        open_value, high_value, close_value
    ):
        raise LiveResponseValidationError(
            f"{field_prefix} has inconsistent OHLC values",
            LiveResponseFailureCode.OHLC_INVALID,
        )
    return open_value, high_value, low_value, close_value, volume, amount


def _validate_a_share_daily(
    selector: AShareDailySelector,
    items: list[Any],
) -> tuple[tuple[FrozenRow, ...], tuple[str, ...]]:
    required = {
        "provider_symbol",
        "stock_code",
        "exchange",
        "trade_date",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "amount",
        "adjust_type",
    }
    normalized: list[dict[str, FrozenPrimitive]] = []
    natural_keys: list[tuple[object, ...]] = []
    ordered_keys: list[tuple[str, str]] = []
    for index, raw in enumerate(items):
        row = _require_mapping(raw, f"data.items[{index}]")
        _require_exact_keys(row, required, set(), f"data.items[{index}]")
        provider_symbol = _require_text(row["provider_symbol"], f"data.items[{index}].provider_symbol")
        stock_code = _require_text(row["stock_code"], f"data.items[{index}].stock_code")
        exchange = _require_text(row["exchange"], f"data.items[{index}].exchange")
        identity_key = f"{exchange}:{stock_code}:{provider_symbol}"
        trade_date = _require_date_text(row["trade_date"], f"data.items[{index}].trade_date")
        adjustment = _require_text(
            row["adjust_type"],
            f"data.items[{index}].adjust_type",
            allow_empty=True,
        )
        if adjustment != selector.adjustment.value:
            raise LiveResponseValidationError(
                "daily adjust_type does not match selector",
                LiveResponseFailureCode.CAPABILITY_MISMATCH,
            )
        open_value, high_value, low_value, close_value, volume, amount = _validate_ohlc(
            row, f"data.items[{index}]"
        )
        normalized.append(
            {
                "provider_symbol": provider_symbol,
                "stock_code": stock_code,
                "exchange": exchange,
                "trade_date": trade_date,
                "open": open_value,
                "high": high_value,
                "low": low_value,
                "close": close_value,
                "volume": volume,
                "amount": amount,
                "adjust_type": adjustment,
            }
        )
        natural_keys.append((identity_key, trade_date, adjustment))
        ordered_keys.append((trade_date, identity_key))
    _reject_duplicate_keys(natural_keys, "A-share daily response")
    if ordered_keys != sorted(ordered_keys):
        raise LiveResponseValidationError(
            "A-share daily rows must be sorted by trade_date and identity_key",
            LiveResponseFailureCode.ORDERING_INVALID,
        )
    expected = {
        (item.identity_key, item.trade_date.isoformat(), selector.adjustment.value)
        for item in selector.expected_observations
    }
    observed = set(natural_keys)
    if observed != expected:
        raise LiveResponseValidationError(
            f"A-share daily coverage mismatch; missing={sorted(expected-observed)}, "
            f"unexpected={sorted(observed-expected)}",
            LiveResponseFailureCode.COVERAGE_INCOMPLETE,
        )
    sessions = tuple(sorted({item[1] for item in natural_keys}))
    return tuple(_freeze_row(row) for row in normalized), sessions


def _validate_benchmark_daily(
    selector: BenchmarkDailySelector,
    items: list[Any],
) -> tuple[tuple[FrozenRow, ...], tuple[str, ...]]:
    required = {
        "provider_symbol",
        "index_code",
        "exchange",
        "trade_date",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "amount",
    }
    normalized: list[dict[str, FrozenPrimitive]] = []
    natural_keys: list[tuple[object, ...]] = []
    ordered_keys: list[tuple[str, str]] = []
    for index, raw in enumerate(items):
        row = _require_mapping(raw, f"data.items[{index}]")
        _require_exact_keys(row, required, set(), f"data.items[{index}]")
        provider_symbol = _require_text(row["provider_symbol"], f"data.items[{index}].provider_symbol")
        index_code = _require_text(row["index_code"], f"data.items[{index}].index_code")
        exchange = _require_text(row["exchange"], f"data.items[{index}].exchange")
        identity_key = f"{exchange}:{index_code}:{provider_symbol}"
        trade_date = _require_date_text(row["trade_date"], f"data.items[{index}].trade_date")
        open_value, high_value, low_value, close_value, volume, amount = _validate_ohlc(
            row, f"data.items[{index}]"
        )
        normalized.append(
            {
                "provider_symbol": provider_symbol,
                "index_code": index_code,
                "exchange": exchange,
                "trade_date": trade_date,
                "open": open_value,
                "high": high_value,
                "low": low_value,
                "close": close_value,
                "volume": volume,
                "amount": amount,
            }
        )
        natural_keys.append((identity_key, trade_date))
        ordered_keys.append((trade_date, identity_key))
    _reject_duplicate_keys(natural_keys, "benchmark daily response")
    if ordered_keys != sorted(ordered_keys):
        raise LiveResponseValidationError(
            "benchmark daily rows must be sorted by trade_date and identity_key",
            LiveResponseFailureCode.ORDERING_INVALID,
        )
    expected = {
        (item.identity_key, item.trade_date.isoformat())
        for item in selector.expected_observations
    }
    observed = set(natural_keys)
    if observed != expected:
        raise LiveResponseValidationError(
            f"benchmark daily coverage mismatch; missing={sorted(expected-observed)}, "
            f"unexpected={sorted(observed-expected)}",
            LiveResponseFailureCode.COVERAGE_INCOMPLETE,
        )
    sessions = tuple(sorted({item[1] for item in natural_keys}))
    return tuple(_freeze_row(row) for row in normalized), sessions


def validate_live_response(
    selector: LiveDailyMarketSelector,
    value: Mapping[str, Any],
) -> ValidatedLiveResponse:
    if isinstance(selector, HistoricalBlockSnapshotSelector):
        raise LiveResponseValidationError(
            "historical block snapshot response schema remains fail-closed pending exact taxonomy review",
            LiveResponseFailureCode.UNSUPPORTED_CAPABILITY,
        )
    schema_version, items = _validate_envelope(selector, value)
    if isinstance(selector, ListedInstrumentSelector):
        normalized, covered_sessions = _validate_listed_instruments(selector, items)
    elif isinstance(selector, TradingCalendarSelector):
        normalized, covered_sessions = _validate_trade_calendar(selector, items)
    elif isinstance(selector, AShareDailySelector):
        normalized, covered_sessions = _validate_a_share_daily(selector, items)
    elif isinstance(selector, BenchmarkDailySelector):
        normalized, covered_sessions = _validate_benchmark_daily(selector, items)
    else:
        raise LiveResponseValidationError(
            "selector type is not supported by the live validator",
            LiveResponseFailureCode.UNSUPPORTED_CAPABILITY,
        )

    content_payload = {
        "source_key": SOURCE_KEY,
        "capability": selector.capability.value,
        "schema_version": schema_version,
        "covered_sessions": covered_sessions,
        "normalized_items": normalized,
    }
    return ValidatedLiveResponse(
        source_key=SOURCE_KEY,
        capability=selector.capability,
        schema_version=schema_version,
        item_count=len(normalized),
        covered_sessions=covered_sessions,
        normalized_items=normalized,
        content_fingerprint=canonical_sha256(content_payload),
    )
