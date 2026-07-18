"""Canonical identity for compatible complete market-data snapshots."""

from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any

SERIES_SCHEMA = "aquantai.snapshot-series.v1"
ALLOWED_ADJUST_TYPES = {"", "qfq", "hfq"}
STOCK_CODE_PATTERN = re.compile(r"^[0-9]{6}$")
SERIES_KEY_PATTERN = re.compile(r"^[0-9a-f]{64}$")


class SnapshotSeriesError(ValueError):
    """Raised when a snapshot-series selector is incomplete or invalid."""


@dataclass(frozen=True)
class SnapshotSeriesIdentity:
    """Canonical selector payload and its stable SHA-256 identity."""

    series_key: str
    canonical: dict[str, Any]


def build_snapshot_series_identity(
    *,
    provider: str,
    dataset: str,
    contract_version: str,
    datasets: list[str],
    stock_codes: list[str],
    requested_start_date: str,
    requested_end_date: str,
    adjust_type: str,
    compatibility_parameters: dict[str, Any] | None = None,
    snapshot_mode: str = "complete",
    stock_code_semantics: str = "exact",
) -> SnapshotSeriesIdentity:
    """Build the one identity under which complete snapshots may compete."""
    normalized_provider = _required_text(provider, "provider")
    normalized_dataset = _required_text(dataset, "dataset")
    normalized_contract = _required_text(contract_version, "contract_version")
    normalized_datasets = sorted({_required_text(value, "datasets") for value in datasets})
    if not normalized_datasets:
        raise SnapshotSeriesError("datasets must not be empty.")
    normalized_codes = sorted({_stock_code(value) for value in stock_codes})
    if not normalized_codes:
        raise SnapshotSeriesError("stock_codes must not be empty.")
    if len(normalized_codes) != len(stock_codes):
        raise SnapshotSeriesError("stock_codes must not contain duplicates.")
    start_date = _compact_date(requested_start_date, "requested_start_date")
    end_date = _compact_date(requested_end_date, "requested_end_date")
    if start_date > end_date:
        raise SnapshotSeriesError("requested_start_date must not be after requested_end_date.")
    normalized_adjust = _required_adjust_type(adjust_type)
    if snapshot_mode != "complete":
        raise SnapshotSeriesError("snapshot_mode must be 'complete'.")
    if stock_code_semantics != "exact":
        raise SnapshotSeriesError("stock_code_semantics must be 'exact'.")

    canonical = {
        "series_schema": SERIES_SCHEMA,
        "provider": normalized_provider,
        "dataset": normalized_dataset,
        "contract_version": normalized_contract,
        "datasets": normalized_datasets,
        "stock_codes": normalized_codes,
        "requested_start_date": start_date,
        "requested_end_date": end_date,
        "adjust_type": normalized_adjust,
        "snapshot_mode": snapshot_mode,
        "stock_code_semantics": stock_code_semantics,
        "compatibility_parameters": _canonical_json_value(
            compatibility_parameters or {}, "compatibility_parameters"
        ),
    }
    encoded = json.dumps(canonical, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return SnapshotSeriesIdentity(
        series_key=hashlib.sha256(encoded.encode("utf-8")).hexdigest(),
        canonical=canonical,
    )


def validate_series_key(value: str) -> str:
    """Validate a caller-supplied canonical series key."""
    normalized = _required_text(value, "series_key").lower()
    if not SERIES_KEY_PATTERN.fullmatch(normalized):
        raise SnapshotSeriesError("series_key must be a 64-character lowercase SHA-256 value.")
    return normalized


def validate_snapshot_series_identity(identity: SnapshotSeriesIdentity) -> SnapshotSeriesIdentity:
    """Reject forged or internally inconsistent selector objects."""
    if not isinstance(identity, SnapshotSeriesIdentity):
        raise SnapshotSeriesError("selector must be a SnapshotSeriesIdentity.")
    canonical = canonical_json_object(identity.canonical, "selector.canonical")
    required = {
        "provider",
        "dataset",
        "contract_version",
        "datasets",
        "stock_codes",
        "requested_start_date",
        "requested_end_date",
        "adjust_type",
        "compatibility_parameters",
        "snapshot_mode",
        "stock_code_semantics",
        "series_schema",
    }
    missing = sorted(required - set(canonical))
    extra = sorted(set(canonical) - required)
    if missing or extra:
        raise SnapshotSeriesError(f"selector canonical fields are incomplete; missing={missing}, extra={extra}.")
    if canonical["series_schema"] != SERIES_SCHEMA:
        raise SnapshotSeriesError(f"selector series_schema must be {SERIES_SCHEMA!r}.")
    rebuilt = build_snapshot_series_identity(
        provider=canonical["provider"],
        dataset=canonical["dataset"],
        contract_version=canonical["contract_version"],
        datasets=canonical["datasets"],
        stock_codes=canonical["stock_codes"],
        requested_start_date=canonical["requested_start_date"],
        requested_end_date=canonical["requested_end_date"],
        adjust_type=canonical["adjust_type"],
        compatibility_parameters=canonical["compatibility_parameters"],
        snapshot_mode=canonical["snapshot_mode"],
        stock_code_semantics=canonical["stock_code_semantics"],
    )
    if rebuilt.canonical != canonical:
        raise SnapshotSeriesError("selector canonical payload is not normalized.")
    if validate_series_key(identity.series_key) != rebuilt.series_key:
        raise SnapshotSeriesError("selector series_key does not match its canonical payload.")
    return rebuilt


def canonical_json_object(value: dict[str, Any] | None, field: str) -> dict[str, Any]:
    """Return deterministic JSON-safe metadata without accepting opaque objects."""
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise SnapshotSeriesError(f"{field} must be a dictionary.")
    return _canonical_json_value(value, field)


def _canonical_json_value(value: Any, field: str) -> Any:
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise SnapshotSeriesError(f"{field} contains a non-finite number.")
        return value
    if isinstance(value, list):
        return [_canonical_json_value(item, field) for item in value]
    if isinstance(value, dict):
        if not all(isinstance(key, str) for key in value):
            raise SnapshotSeriesError(f"{field} keys must be strings.")
        normalized: dict[str, Any] = {}
        for key in sorted(value):
            normalized_key = _required_text(key, field)
            normalized[normalized_key] = _canonical_json_value(value[key], field)
        return normalized
    raise SnapshotSeriesError(f"{field} contains unsupported value type {type(value).__name__}.")


def _required_text(value: Any, field: str) -> str:
    if value is None:
        raise SnapshotSeriesError(f"{field} is required.")
    normalized = str(value).strip()
    if not normalized:
        raise SnapshotSeriesError(f"{field} must not be blank.")
    return normalized


def _stock_code(value: Any) -> str:
    normalized = _required_text(value, "stock_codes")
    if not STOCK_CODE_PATTERN.fullmatch(normalized):
        raise SnapshotSeriesError("stock_codes must contain six-digit stock codes.")
    return normalized


def _compact_date(value: Any, field: str) -> str:
    normalized = _required_text(value, field).replace("-", "")
    try:
        return datetime.strptime(normalized, "%Y%m%d").strftime("%Y%m%d")
    except ValueError as exc:
        raise SnapshotSeriesError(f"{field} must use YYYYMMDD format.") from exc


def _required_adjust_type(value: Any) -> str:
    normalized = "" if value is None else str(value).strip()
    if normalized not in ALLOWED_ADJUST_TYPES:
        raise SnapshotSeriesError(f"adjust_type must be one of {sorted(ALLOWED_ADJUST_TYPES)!r}.")
    return normalized
