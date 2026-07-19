"""Sanitized, no-database-write probe for reviewed Hithink contracts."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
import hashlib
import json
import math
import os
from pathlib import Path
import re
from typing import Callable, Mapping, Protocol
from urllib.error import HTTPError
from urllib.parse import urlencode, urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener
from zoneinfo import ZoneInfo


BASE_URL = "https://fuyao.aicubes.cn"
API_KEY_ENV = "HITHINK_FINANCE_API_KEY"
TIMEOUT_SECONDS = 10.0
MAX_RESPONSE_BYTES = 1_000_000
TICKER_LIMIT = 100
MAX_DATE_WINDOW_DAYS = 31
REPRESENTATIVE_SUFFIXES = ("SH", "SZ", "BJ")
_MARKET_TIMEZONE = ZoneInfo("Asia/Shanghai")
_THSCODE = re.compile(r"^[0-9]{6}\.(SH|SZ|BJ)$")
_DATE_TEXT = re.compile(r"^[0-9]{8}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_SAFE_FILE_NAME = re.compile(r"^[A-Za-z0-9._-]+\.parquet$")

_TICKER_FIELDS = {
    "asset_type": "str",
    "currency": "str",
    "exchange": "str",
    "name": "str",
    "thscode": "str",
    "ticker": "str",
}
_CALENDAR_FIELDS = {"date": "str", "date_ms": "int"}
_BAR_FIELDS = {
    "close_price": "number",
    "date_ms": "int",
    "high_price": "number",
    "low_price": "number",
    "open_price": "number",
    "turnover": "number",
    "volume": "number",
}
_DUMP_FIELDS = {"url": "str"}
_DUMP_SCHEMA = (
    "adjusted",
    "close_price",
    "currency",
    "date_ms",
    "high_price",
    "interval",
    "low_price",
    "open_price",
    "thscode",
    "turnover",
    "volume",
)
_RIGHTS_FIELDS = (
    "caching_and_transformation",
    "dump_reproducibility",
    "enabled_capabilities",
    "local_display",
    "local_long_term_storage",
    "quotas_and_qps",
    "redistribution_and_deployment",
    "retention_and_deletion",
)


class ProbeConfigurationError(ValueError):
    """A safe configuration failure that never includes caller data."""

    def __init__(self, category: str, message: str) -> None:
        self.category = category
        super().__init__(message)


@dataclass(frozen=True, repr=False)
class HttpResponse:
    status: int
    payload: object

    def __repr__(self) -> str:
        return "HttpResponse(status=<redacted>, payload=<redacted>)"


class ProbeTransport(Protocol):
    def get(
        self,
        path: str,
        params: Mapping[str, object],
        *,
        api_key: str,
        timeout: float,
    ) -> HttpResponse: ...


class _NoRedirectHandler(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class UrllibProbeTransport:
    """One-attempt standard-library transport with no retained credential."""

    def get(
        self,
        path: str,
        params: Mapping[str, object],
        *,
        api_key: str,
        timeout: float,
    ) -> HttpResponse:
        query = urlencode(sorted(params.items()))
        url = f"{BASE_URL}{path}" + (f"?{query}" if query else "")
        request = Request(url, headers={"X-api-key": api_key}, method="GET")
        opener = build_opener(_NoRedirectHandler())
        try:
            with opener.open(request, timeout=timeout) as response:
                raw = response.read(MAX_RESPONSE_BYTES + 1)
                if len(raw) > MAX_RESPONSE_BYTES:
                    raise ValueError("response exceeds probe limit")
                payload = json.loads(raw.decode("utf-8"))
                return HttpResponse(status=int(response.status), payload=payload)
        except HTTPError as error:
            try:
                raw = error.read(MAX_RESPONSE_BYTES + 1)
                payload = (
                    json.loads(raw.decode("utf-8"))
                    if len(raw) <= MAX_RESPONSE_BYTES
                    else None
                )
            except (UnicodeDecodeError, json.JSONDecodeError):
                payload = None
            return HttpResponse(status=int(error.code), payload=payload)


@dataclass(frozen=True)
class ProbeOptions:
    mode: str
    representatives: tuple[str, ...]
    start_date: str
    end_date: str
    manifest_path: Path | None = None
    rights_path: Path | None = None


def _fingerprint(fields: Mapping[str, str], *, dump: bool = False) -> str:
    if dump:
        return "data.url:str"
    item_fields = "|".join(
        f"item[].{name}:{fields[name]}" for name in sorted(fields)
    )
    return f"data.timestamp:int|{item_fields}"


def _safe_request_id(value: object) -> str | None:
    if not isinstance(value, str) or not value or len(value) > 256:
        return None
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]


def _is_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _is_number(value: object) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(float(value))
    )


def _field_type_matches(value: object, expected: str) -> bool:
    if expected == "str":
        return isinstance(value, str)
    if expected == "int":
        return _is_int(value)
    if expected == "number":
        return _is_number(value)
    raise AssertionError(f"unknown internal field type: {expected}")


def _validate_rows(rows: object, fields: Mapping[str, str]) -> list[Mapping[str, object]]:
    if not isinstance(rows, list):
        raise ProbeConfigurationError("contract_invalid", "Contract item list is invalid.")
    validated: list[Mapping[str, object]] = []
    for row in rows:
        if not isinstance(row, Mapping):
            raise ProbeConfigurationError("contract_invalid", "Contract item is invalid.")
        if any(
            name not in row or not _field_type_matches(row[name], expected)
            for name, expected in fields.items()
        ):
            raise ProbeConfigurationError("contract_invalid", "Contract fields are invalid.")
        validated.append(row)
    return validated


def _validate_tickers(rows: object) -> tuple[int, list[str]]:
    items = _validate_rows(rows, _TICKER_FIELDS)
    suffixes: set[str] = set()
    for item in items:
        thscode = item["thscode"]
        match = _THSCODE.fullmatch(thscode)
        if (
            match is None
            or item["ticker"] != thscode[:6]
            or item["exchange"] != match.group(1)
            or item["asset_type"] != "a-share"
            or item["currency"] != "CNY"
        ):
            raise ProbeConfigurationError("contract_invalid", "Ticker semantics are invalid.")
        suffixes.add(match.group(1))
    return len(items), sorted(suffixes)


def _validate_calendar(rows: object) -> tuple[int, list[str]]:
    items = _validate_rows(rows, _CALENDAR_FIELDS)
    for item in items:
        if item["date_ms"] <= 0 or _DATE_TEXT.fullmatch(item["date"]) is None:
            raise ProbeConfigurationError("contract_invalid", "Calendar semantics are invalid.")
    return len(items), []


def _validate_bars(rows: object, suffix: str) -> tuple[int, list[str]]:
    items = _validate_rows(rows, _BAR_FIELDS)
    for item in items:
        if item["date_ms"] <= 0:
            raise ProbeConfigurationError("contract_invalid", "Historical-bar date is invalid.")
    return len(items), [suffix]


def _classify_business_code(code: int) -> str:
    if code == 0:
        return "success"
    if 1000 <= code < 2000:
        return "validation"
    if code == 2001:
        return "authentication"
    if 2000 <= code < 3000:
        return "permission"
    if 3000 <= code < 4000:
        return "absence_or_data_state"
    if code == 4001:
        return "rate_limit"
    if code == 5002:
        return "timeout"
    if code in {5001, 5003}:
        return "upstream_unavailable"
    return "unknown"


def _endpoint_result(
    endpoint_id: str,
    response: HttpResponse,
    *,
    fields: Mapping[str, str],
    validator: Callable[[object], tuple[int, list[str]]] | None = None,
    dump_manifest_complete: bool = True,
) -> dict[str, object]:
    result: dict[str, object] = {
        "business_category": "transport_http",
        "business_code": None,
        "dump_https_link_present": False,
        "endpoint_id": endpoint_id,
        "item_count": 0,
        "request_id": None,
        "required_field_type_fingerprint": _fingerprint(
            fields, dump=endpoint_id == "dump_link"
        ),
        "status": "blocked",
        "suffix_coverage": [],
    }
    if response.status != 200 or not isinstance(response.payload, Mapping):
        return result
    payload = response.payload
    code = payload.get("code")
    if not _is_int(code):
        result["business_category"] = "contract_invalid"
        return result
    category = _classify_business_code(code)
    result["business_code"] = code
    result["business_category"] = category
    result["request_id"] = _safe_request_id(payload.get("request_id"))
    if not isinstance(payload.get("message"), str) or result["request_id"] is None:
        result["business_category"] = "contract_invalid"
        return result
    if code != 0:
        return result
    data = payload.get("data")
    if not isinstance(data, Mapping):
        result["business_category"] = "contract_invalid"
        return result
    try:
        if endpoint_id == "dump_link":
            link = data.get("url")
            parsed = urlparse(link) if isinstance(link, str) else None
            present = bool(parsed and parsed.scheme == "https" and parsed.netloc)
            result["dump_https_link_present"] = present
            if not present:
                result["business_category"] = "contract_invalid"
                return result
            if not dump_manifest_complete:
                result["business_category"] = "local_manifest_incomplete"
                return result
        elif validator is not None:
            if not _is_int(data.get("timestamp")) or data["timestamp"] <= 0:
                result["business_category"] = "contract_invalid"
                return result
            count, suffixes = validator(data.get("item"))
            result["item_count"] = count
            result["suffix_coverage"] = suffixes
    except ProbeConfigurationError:
        result["business_category"] = "contract_invalid"
        return result
    result["status"] = "accepted"
    return result


def _transport_error_result(endpoint_id: str, fields: Mapping[str, str]) -> dict[str, object]:
    return {
        "business_category": "transport_error",
        "business_code": None,
        "dump_https_link_present": False,
        "endpoint_id": endpoint_id,
        "item_count": 0,
        "request_id": None,
        "required_field_type_fingerprint": _fingerprint(
            fields, dump=endpoint_id == "dump_link"
        ),
        "status": "blocked",
        "suffix_coverage": [],
    }


def _load_local_json(path: Path | None) -> Mapping[str, object] | None:
    if path is None:
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ProbeConfigurationError(
            "local_evidence_invalid", "Local evidence JSON is invalid."
        ) from error
    if not isinstance(payload, Mapping):
        raise ProbeConfigurationError(
            "local_evidence_invalid", "Local evidence JSON is invalid."
        )
    return payload


def _manifest_complete(payload: Mapping[str, object] | None) -> bool:
    if payload is None:
        return False
    coverage_start = payload.get("coverage_start")
    coverage_end = payload.get("coverage_end")
    schema = payload.get("schema")
    failed = payload.get("failed_tickers")
    return bool(
        payload.get("dump_id") == "a_share_daily_k_1d_none_10d"
        and isinstance(payload.get("version"), str)
        and bool(payload.get("version"))
        and payload.get("mode") == "RECENT_TRADING_DAYS"
        and isinstance(coverage_start, str)
        and isinstance(coverage_end, str)
        and _parse_date(coverage_start) <= _parse_date(coverage_end)
        and _is_int(payload.get("row_count"))
        and payload["row_count"] > 0
        and _is_int(payload.get("ticker_count"))
        and payload["ticker_count"] > 0
        and isinstance(failed, list)
        and not failed
        and isinstance(payload.get("file_name"), str)
        and _SAFE_FILE_NAME.fullmatch(payload["file_name"]) is not None
        and isinstance(payload.get("sha256"), str)
        and _SHA256.fullmatch(payload["sha256"]) is not None
        and isinstance(schema, list)
        and all(isinstance(item, str) for item in schema)
        and tuple(sorted(schema)) == _DUMP_SCHEMA
    )


def _rights_complete(payload: Mapping[str, object] | None) -> bool:
    return payload is not None and all(
        name in payload and payload[name] is not None for name in _RIGHTS_FIELDS
    )


def _parse_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError) as error:
        raise ProbeConfigurationError("date_invalid", "Probe date is invalid.") from error


def _validated_options(options: ProbeOptions) -> tuple[tuple[str, ...], int, int]:
    if options.mode not in {"live", "offline"}:
        raise ProbeConfigurationError(
            "mode_invalid", "Select exactly one probe execution mode."
        )
    if len(options.representatives) != 3 or len(set(options.representatives)) != 3:
        raise ProbeConfigurationError(
            "representatives_invalid", "Exactly three unique representatives are required."
        )
    by_suffix: dict[str, str] = {}
    for symbol in options.representatives:
        if not isinstance(symbol, str):
            raise ProbeConfigurationError(
                "representatives_invalid", "Representative format is invalid."
            )
        match = _THSCODE.fullmatch(symbol)
        if match is None or match.group(1) in by_suffix:
            raise ProbeConfigurationError(
                "representatives_invalid", "Representative format is invalid."
            )
        by_suffix[match.group(1)] = symbol
    if set(by_suffix) != set(REPRESENTATIVE_SUFFIXES):
        raise ProbeConfigurationError(
            "representatives_invalid", "SH, SZ and BJ representatives are required."
        )
    start = _parse_date(options.start_date)
    end = _parse_date(options.end_date)
    if end < start or (end - start).days > MAX_DATE_WINDOW_DAYS:
        raise ProbeConfigurationError("date_invalid", "Probe date range is invalid.")
    start_ms = int(datetime(start.year, start.month, start.day, tzinfo=_MARKET_TIMEZONE).timestamp() * 1000)
    end_ms = int(datetime(end.year, end.month, end.day, tzinfo=_MARKET_TIMEZONE).timestamp() * 1000)
    ordered = tuple(by_suffix[suffix] for suffix in REPRESENTATIVE_SUFFIXES)
    return ordered, start_ms, end_ms


def _offline_responses(representatives: tuple[str, ...]) -> dict[str, HttpResponse]:
    ticker_items = []
    for symbol in representatives:
        suffix = symbol[-2:]
        ticker_items.append(
            {
                "asset_type": "a-share",
                "currency": "CNY",
                "exchange": suffix,
                "name": f"Synthetic {suffix}",
                "thscode": symbol,
                "ticker": symbol[:6],
            }
        )
    envelope = lambda request_id, data: HttpResponse(  # noqa: E731
        200, {"code": 0, "message": "success", "request_id": request_id, "data": data}
    )
    responses = {
        "ticker_list": envelope(
            "offline-tickers", {"timestamp": 1783900800000, "item": ticker_items}
        ),
        "trading_calendar": envelope(
            "offline-calendar",
            {
                "timestamp": 1783900800000,
                "item": [{"date_ms": 1783900800000, "date": "20260713"}],
            },
        ),
        "dump_link": envelope(
            "offline-dump",
            {"url": "https://example.invalid/private-dump?signature=discarded"},
        ),
    }
    for symbol in representatives:
        suffix = symbol[-2:]
        responses[f"historical_bar_{suffix}"] = envelope(
            f"offline-bar-{suffix}",
            {
                "timestamp": 1783900800000,
                "item": [
                    {
                        "date_ms": 1783900800000,
                        "open_price": 10.0,
                        "high_price": 10.5,
                        "low_price": 9.5,
                        "close_price": 10.2,
                        "volume": 1000.0,
                        "turnover": 10200.0,
                    }
                ]
            },
        )
    return responses


def run_contract_probe(
    options: ProbeOptions,
    *,
    env_getter: Callable[[str], str | None] = os.getenv,
    transport_factory: Callable[[], ProbeTransport] = UrllibProbeTransport,
) -> dict[str, object]:
    """Run one explicit offline or live probe and return sanitized evidence."""

    representatives, start_ms, end_ms = _validated_options(options)
    manifest_complete = _manifest_complete(_load_local_json(options.manifest_path))
    rights_complete = _rights_complete(_load_local_json(options.rights_path))

    transport: ProbeTransport | None = None
    api_key = ""
    offline = options.mode == "offline"
    if not offline:
        try:
            configured_key = env_getter(API_KEY_ENV)
        except Exception:
            raise ProbeConfigurationError(
                "credential_unavailable", "Live probe credential could not be read."
            ) from None
        api_key = configured_key if isinstance(configured_key, str) else ""
        if not api_key.strip():
            raise ProbeConfigurationError(
                "credential_missing", "Live probe credential is not configured."
            )
        try:
            transport = transport_factory()
        except Exception:
            raise ProbeConfigurationError(
                "transport_unavailable", "Live probe transport could not be constructed."
            ) from None

    requests: list[tuple[str, str, dict[str, object], Mapping[str, str], Callable[[object], tuple[int, list[str]]] | None]] = [
        (
            "ticker_list",
            "/api/meta/tickers/list",
            {"asset_type": "a-share", "limit": TICKER_LIMIT, "offset": 0},
            _TICKER_FIELDS,
            _validate_tickers,
        ),
        (
            "trading_calendar",
            "/api/a-share/calendar/trading-days",
            {},
            _CALENDAR_FIELDS,
            _validate_calendar,
        ),
    ]
    for symbol in representatives:
        suffix = symbol[-2:]
        requests.append(
            (
                f"historical_bar_{suffix}",
                "/api/a-share/prices/historical",
                {
                    "adjust": "none",
                    "end": end_ms,
                    "interval": "1d",
                    "start": start_ms,
                    "thscode": symbol,
                },
                _BAR_FIELDS,
                lambda rows, suffix=suffix: _validate_bars(rows, suffix),
            )
        )
    requests.append(
        (
            "dump_link",
            "/dump/market-dumps/daily-k-10d/download-url",
            {},
            _DUMP_FIELDS,
            None,
        )
    )

    offline_responses = _offline_responses(representatives) if offline else {}
    results: list[dict[str, object]] = []
    for endpoint_id, path, params, fields, validator in requests:
        try:
            if offline:
                response = offline_responses[endpoint_id]
            else:
                assert transport is not None
                response = transport.get(
                    path, params, api_key=api_key, timeout=TIMEOUT_SECONDS
                )
            result = _endpoint_result(
                endpoint_id,
                response,
                fields=fields,
                validator=validator,
                dump_manifest_complete=(manifest_complete if endpoint_id == "dump_link" else True),
            )
        except Exception:  # transport details are intentionally never exposed
            result = _transport_error_result(endpoint_id, fields)
        results.append(result)

    results.sort(key=lambda item: str(item["endpoint_id"]))
    accepted = (
        all(item["status"] == "accepted" for item in results)
        and manifest_complete
        and rights_complete
    )
    return {
        "endpoints": results,
        "manifest_evidence_complete": manifest_complete,
        "overall_status": "accepted" if accepted else "blocked",
        "rights_evidence_complete": rights_complete,
    }


def report_json(report: Mapping[str, object]) -> str:
    return json.dumps(report, allow_nan=False, indent=2, sort_keys=True)
