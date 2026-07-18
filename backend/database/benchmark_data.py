"""Validated, transactional persistence for benchmark-index daily snapshots."""

from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Any

import pandas as pd
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from backend.database.models import BenchmarkIndexDailyRecord, IngestionRun
from backend.database.series import (
    BenchmarkSeriesIdentity,
    build_benchmark_series_identity,
    canonical_json_object,
)
from datasource.base import BENCHMARK_INDEX_DAILY_COLUMNS, BenchmarkIndexBundle

BENCHMARK_DATASET = "benchmark_index_daily"
BENCHMARK_CONTRACT_VERSION = "1.0"
BENCHMARK_SNAPSHOT_MODE = "complete"
BENCHMARK_SCOPE_SEMANTICS = "exact"
DEFAULT_BENCHMARK_ENDPOINT = "index_zh_a_hist"
DEFAULT_BENCHMARK_ADAPTER_VERSION = "aquantai.akshare-benchmark-adapter.v1"
INDEX_CODE_PATTERN = re.compile(r"^[0-9]{6}$")
SENSITIVE_METADATA_TERMS = {
    "api_key",
    "apikey",
    "cookie",
    "credential",
    "database_url",
    "password",
    "secret",
    "token",
}


class BenchmarkDataValidationError(ValueError):
    """Raised before invalid benchmark rows can be committed."""


@dataclass(frozen=True)
class BenchmarkIngestionResult:
    ingestion_run_id: int
    batch_identifier: str
    series_key: str
    status: str
    information_cutoff_date: str
    rows_received: int
    rows_written: int
    dataset_counts: dict[str, int]
    idempotent: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "ingestion_run_id": self.ingestion_run_id,
            "batch_identifier": self.batch_identifier,
            "series_key": self.series_key,
            "status": self.status,
            "information_cutoff_date": self.information_cutoff_date,
            "rows_received": self.rows_received,
            "rows_written": self.rows_written,
            "dataset_counts": dict(self.dataset_counts),
            "idempotent": self.idempotent,
        }


@dataclass(frozen=True)
class BenchmarkValidationSummary:
    series_key: str
    canonical_scope: dict[str, Any]
    information_cutoff_date: str
    dataset_counts: dict[str, int]
    valid: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "series_key": self.series_key,
            "canonical_scope": dict(self.canonical_scope),
            "information_cutoff_date": self.information_cutoff_date,
            "dataset_counts": dict(self.dataset_counts),
            "valid": self.valid,
        }


def validate_benchmark_bundle(
    bundle: BenchmarkIndexBundle,
    *,
    provider: str,
    requested_start_date: str,
    requested_end_date: str,
    information_cutoff_date: str,
    requested_scope: dict[str, Any],
    endpoint: str = DEFAULT_BENCHMARK_ENDPOINT,
    adapter_compatibility_version: str = DEFAULT_BENCHMARK_ADAPTER_VERSION,
    contract_version: str = BENCHMARK_CONTRACT_VERSION,
    compatibility_parameters: dict[str, Any] | None = None,
) -> BenchmarkValidationSummary:
    provider_text, start, end, cutoff, scope, series = _request_context(
        provider=provider,
        requested_start_date=requested_start_date,
        requested_end_date=requested_end_date,
        information_cutoff_date=information_cutoff_date,
        requested_scope=requested_scope,
        endpoint=endpoint,
        adapter_compatibility_version=adapter_compatibility_version,
        contract_version=contract_version,
        compatibility_parameters=compatibility_parameters,
    )
    rows = _normalize_rows(bundle, provider_text, start, end, cutoff, scope)
    return BenchmarkValidationSummary(
        series_key=series.series_key,
        canonical_scope=series.canonical,
        information_cutoff_date=_compact_date(cutoff),
        dataset_counts={BENCHMARK_DATASET: len(rows)},
    )


class BenchmarkPersistenceService:
    """Persist one exact benchmark complete snapshot with immutable attempts."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def ingest_bundle(
        self,
        bundle: BenchmarkIndexBundle,
        *,
        provider: str,
        requested_start_date: str,
        requested_end_date: str,
        information_cutoff_date: str,
        requested_scope: dict[str, Any],
        endpoint: str = DEFAULT_BENCHMARK_ENDPOINT,
        adapter_compatibility_version: str = DEFAULT_BENCHMARK_ADAPTER_VERSION,
        provider_request_metadata: dict[str, Any] | None = None,
        adapter_version: str = DEFAULT_BENCHMARK_ADAPTER_VERSION,
        contract_version: str = BENCHMARK_CONTRACT_VERSION,
        compatibility_parameters: dict[str, Any] | None = None,
    ) -> BenchmarkIngestionResult:
        provider_text, start, end, cutoff, scope, series = _request_context(
            provider=provider,
            requested_start_date=requested_start_date,
            requested_end_date=requested_end_date,
            information_cutoff_date=information_cutoff_date,
            requested_scope=requested_scope,
            endpoint=endpoint,
            adapter_compatibility_version=adapter_compatibility_version,
            contract_version=contract_version,
            compatibility_parameters=compatibility_parameters,
        )
        metadata = _request_metadata(provider_request_metadata)
        normalized_adapter = _required_text(adapter_version, "adapter_version")
        raw_count = _raw_count(bundle)
        raw_identifier = _hash_payload(
            {
                "raw": _frame_payload(getattr(bundle, BENCHMARK_DATASET, None)),
                "series_key": series.series_key,
                "cutoff": _compact_date(cutoff),
            }
        )
        try:
            rows = _normalize_rows(bundle, provider_text, start, end, cutoff, scope)
        except Exception as exc:
            run_id = self._create_pending_run(
                batch_identifier=raw_identifier,
                provider=provider_text,
                start=start,
                end=end,
                cutoff=cutoff,
                scope=scope,
                series=series,
                metadata=metadata,
                adapter_version=normalized_adapter,
                contract_version=contract_version,
                row_count=raw_count,
            )
            self._mark_failed(run_id, exc)
            raise

        batch_identifier = _hash_payload(
            {
                "rows": _json_rows(rows),
                "series_key": series.series_key,
                "cutoff": _compact_date(cutoff),
                "snapshot_mode": BENCHMARK_SNAPSHOT_MODE,
            }
        )
        existing = self._find_success(batch_identifier, series.series_key)
        if existing is not None:
            return _result(existing, idempotent=True, rows_written=0)
        run_id = self._create_pending_run(
            batch_identifier=batch_identifier,
            provider=provider_text,
            start=start,
            end=end,
            cutoff=cutoff,
            scope=scope,
            series=series,
            metadata=metadata,
            adapter_version=normalized_adapter,
            contract_version=contract_version,
            row_count=len(rows),
        )
        try:
            with self._session_factory.begin() as session:
                run = session.get(IngestionRun, run_id, with_for_update=True)
                if run is None:
                    raise RuntimeError(f"Benchmark ingestion run {run_id} disappeared.")
                session.add_all(
                    [BenchmarkIndexDailyRecord(ingestion_run_id=run_id, **row) for row in rows]
                )
                run.status = "succeeded"
                run.row_count_written = len(rows)
                run.completed_at = datetime.now(timezone.utc)
                run.error_summary = None
        except IntegrityError as exc:
            concurrent = self._find_success(batch_identifier, series.series_key)
            if concurrent is not None:
                self._mark_failed(
                    run_id,
                    RuntimeError(
                        f"Concurrent identical benchmark batch completed as run {concurrent.id}."
                    ),
                )
                return _result(concurrent, idempotent=True, rows_written=0)
            self._mark_failed(run_id, exc)
            raise
        except Exception as exc:
            self._mark_failed(run_id, exc)
            raise
        with self._session_factory() as session:
            run = session.get(IngestionRun, run_id)
            if run is None:
                raise RuntimeError(f"Benchmark ingestion run {run_id} is unavailable after commit.")
            return _result(run, idempotent=False, rows_written=len(rows))

    def record_failed_attempt(
        self,
        exc: Exception,
        *,
        provider: str,
        requested_start_date: str,
        requested_end_date: str,
        information_cutoff_date: str,
        requested_scope: dict[str, Any],
        endpoint: str = DEFAULT_BENCHMARK_ENDPOINT,
        adapter_compatibility_version: str = DEFAULT_BENCHMARK_ADAPTER_VERSION,
        provider_request_metadata: dict[str, Any] | None = None,
        adapter_version: str = DEFAULT_BENCHMARK_ADAPTER_VERSION,
        contract_version: str = BENCHMARK_CONTRACT_VERSION,
    ) -> int:
        provider_text, start, end, cutoff, scope, series = _request_context(
            provider=provider,
            requested_start_date=requested_start_date,
            requested_end_date=requested_end_date,
            information_cutoff_date=information_cutoff_date,
            requested_scope=requested_scope,
            endpoint=endpoint,
            adapter_compatibility_version=adapter_compatibility_version,
            contract_version=contract_version,
            compatibility_parameters=None,
        )
        metadata = _request_metadata(provider_request_metadata)
        normalized_adapter = _required_text(adapter_version, "adapter_version")
        run_id = self._create_pending_run(
            batch_identifier=_hash_payload(
                {
                    "provider_failure": _error_summary(exc),
                    "series_key": series.series_key,
                    "cutoff": _compact_date(cutoff),
                    "metadata": metadata,
                }
            ),
            provider=provider_text,
            start=start,
            end=end,
            cutoff=cutoff,
            scope=scope,
            series=series,
            metadata=metadata,
            adapter_version=normalized_adapter,
            contract_version=contract_version,
            row_count=0,
        )
        self._mark_failed(run_id, exc)
        return run_id

    def _find_success(self, batch_identifier: str, series_key: str) -> IngestionRun | None:
        with self._session_factory() as session:
            return session.scalar(
                select(IngestionRun).where(
                    IngestionRun.batch_identifier == batch_identifier,
                    IngestionRun.series_key == series_key,
                    IngestionRun.status == "succeeded",
                )
            )

    def _create_pending_run(
        self,
        *,
        batch_identifier: str,
        provider: str,
        start: date,
        end: date,
        cutoff: date,
        scope: dict[str, Any],
        series: BenchmarkSeriesIdentity,
        metadata: dict[str, Any],
        adapter_version: str,
        contract_version: str,
        row_count: int,
    ) -> int:
        with self._session_factory.begin() as session:
            run = IngestionRun(
                batch_identifier=batch_identifier,
                series_key=series.series_key,
                series_identity=series.canonical,
                provider=provider,
                dataset=BENCHMARK_DATASET,
                imported_at=datetime.now(timezone.utc),
                requested_start_date=start,
                requested_end_date=end,
                information_cutoff_date=cutoff,
                requested_scope=scope,
                provider_request_metadata=metadata,
                adapter_version=adapter_version,
                snapshot_mode=BENCHMARK_SNAPSHOT_MODE,
                contract_version=contract_version,
                status="pending",
                row_count_received=row_count,
                row_count_written=0,
                dataset_counts={BENCHMARK_DATASET: row_count},
            )
            session.add(run)
            session.flush()
            return run.id

    def _mark_failed(self, run_id: int, exc: Exception) -> None:
        with self._session_factory.begin() as session:
            run = session.get(IngestionRun, run_id, with_for_update=True)
            if run is None:
                raise RuntimeError(f"Could not record benchmark failure for run {run_id}.") from exc
            run.status = "failed"
            run.row_count_written = 0
            run.error_summary = _error_summary(exc)
            run.completed_at = datetime.now(timezone.utc)


def _request_context(
    *,
    provider: str,
    requested_start_date: str,
    requested_end_date: str,
    information_cutoff_date: str,
    requested_scope: dict[str, Any],
    endpoint: str,
    adapter_compatibility_version: str,
    contract_version: str,
    compatibility_parameters: dict[str, Any] | None,
) -> tuple[str, date, date, date, dict[str, Any], BenchmarkSeriesIdentity]:
    provider_text = _required_text(provider, "provider")
    start = _required_date(requested_start_date, "requested_start_date")
    end = _required_date(requested_end_date, "requested_end_date")
    cutoff = _required_date(information_cutoff_date, "information_cutoff_date")
    if start > end:
        raise BenchmarkDataValidationError(
            "requested_start_date must not be after requested_end_date."
        )
    if end > cutoff:
        raise BenchmarkDataValidationError(
            "requested_end_date must not exceed information_cutoff_date."
        )
    scope = _validate_scope(requested_scope)
    contract = _required_text(contract_version, "contract_version")
    _reject_sensitive(compatibility_parameters or {}, "compatibility_parameters")
    series = build_benchmark_series_identity(
        provider=provider_text,
        contract_version=contract,
        index_codes=scope["index_codes"],
        requested_start_date=_compact_date(start),
        requested_end_date=_compact_date(end),
        endpoint=endpoint,
        adapter_compatibility_version=adapter_compatibility_version,
        compatibility_parameters=compatibility_parameters,
    )
    return provider_text, start, end, cutoff, scope, series


def _validate_scope(value: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise BenchmarkDataValidationError("requested_scope must be a dictionary.")
    allowed = {"datasets", "index_codes", "index_code_semantics"}
    unknown = sorted(set(value) - allowed)
    if unknown:
        raise BenchmarkDataValidationError(f"requested_scope contains unknown fields: {unknown}.")
    datasets = sorted({_required_text(item, "requested_scope.datasets") for item in value.get("datasets", [])})
    if datasets != [BENCHMARK_DATASET]:
        raise BenchmarkDataValidationError(
            f"requested_scope.datasets must be exactly [{BENCHMARK_DATASET!r}]."
        )
    raw_codes = value.get("index_codes")
    if not isinstance(raw_codes, list):
        raise BenchmarkDataValidationError("requested_scope.index_codes must be a list.")
    codes = sorted({_index_code(item) for item in raw_codes})
    if not codes or len(codes) != len(raw_codes):
        raise BenchmarkDataValidationError(
            "requested_scope.index_codes must be non-empty and contain no duplicates."
        )
    if len(codes) > 20:
        raise BenchmarkDataValidationError("At most 20 benchmark index codes are allowed.")
    semantics = str(value.get("index_code_semantics", BENCHMARK_SCOPE_SEMANTICS)).strip()
    if semantics != BENCHMARK_SCOPE_SEMANTICS:
        raise BenchmarkDataValidationError("index_code_semantics must be 'exact'.")
    return {
        "datasets": [BENCHMARK_DATASET],
        "index_codes": codes,
        "index_code_semantics": semantics,
    }


def _normalize_rows(
    bundle: BenchmarkIndexBundle,
    provider: str,
    start: date,
    end: date,
    cutoff: date,
    scope: dict[str, Any],
) -> list[dict[str, Any]]:
    if not isinstance(bundle, BenchmarkIndexBundle):
        raise BenchmarkDataValidationError("bundle must be a BenchmarkIndexBundle.")
    frame = bundle.benchmark_index_daily
    if not isinstance(frame, pd.DataFrame):
        raise BenchmarkDataValidationError("benchmark_index_daily must be a DataFrame.")
    required = {"source", "index_code", "trade_date", "close"}
    missing = sorted(required - set(frame.columns))
    unknown = sorted(set(frame.columns) - set(BENCHMARK_INDEX_DAILY_COLUMNS))
    if missing or unknown:
        raise BenchmarkDataValidationError(
            f"benchmark_index_daily contract mismatch; missing={missing}, unknown={unknown}."
        )
    normalized = frame.copy()
    for column in BENCHMARK_INDEX_DAILY_COLUMNS:
        if column not in normalized.columns:
            normalized[column] = pd.NA
    if normalized.empty:
        raise BenchmarkDataValidationError("benchmark_index_daily must not be empty.")
    normalized["source"] = normalized["source"].map(
        lambda value: _required_text(value, "source")
    )
    if set(normalized["source"]) != {provider}:
        raise BenchmarkDataValidationError("Every benchmark source must equal provider.")
    normalized["index_code"] = normalized["index_code"].map(_index_code)
    observed_codes = sorted(normalized["index_code"].unique())
    if observed_codes != scope["index_codes"]:
        raise BenchmarkDataValidationError(
            "Benchmark rows must match the exact requested index-code scope; "
            f"expected={scope['index_codes']}, observed={observed_codes}."
        )
    normalized["trade_date"] = pd.to_datetime(
        normalized["trade_date"], errors="raise"
    ).dt.date
    if normalized["trade_date"].lt(start).any() or normalized["trade_date"].gt(end).any():
        raise BenchmarkDataValidationError("Benchmark trade_date is outside the requested range.")
    if normalized["trade_date"].gt(cutoff).any():
        raise BenchmarkDataValidationError("Benchmark trade_date exceeds information cutoff.")
    if normalized.duplicated(["source", "index_code", "trade_date"]).any():
        raise BenchmarkDataValidationError("Duplicate benchmark source/index_code/trade_date rows are not allowed.")
    normalized["close"] = _finite_numeric(normalized["close"], "close", nullable=False)
    if normalized["close"].le(0).any():
        raise BenchmarkDataValidationError("Benchmark close must be positive.")
    for column in ("open", "high", "low", "volume", "amount"):
        normalized[column] = _finite_numeric(normalized[column], column, nullable=True)
    ohlc_present = normalized[["open", "high", "low"]].notna()
    partial_ohlc = ohlc_present.any(axis=1) & ~ohlc_present.all(axis=1)
    if partial_ohlc.any():
        raise BenchmarkDataValidationError("Benchmark open/high/low must be all present or all null per row.")
    complete_ohlc = ohlc_present.all(axis=1)
    if (normalized.loc[complete_ohlc, ["open", "high", "low"]] <= 0).any().any():
        raise BenchmarkDataValidationError("Benchmark OHLC prices must be positive.")
    invalid_range = complete_ohlc & (
        (normalized["low"] > normalized["open"])
        | (normalized["open"] > normalized["high"])
        | (normalized["low"] > normalized["close"])
        | (normalized["close"] > normalized["high"])
    )
    if invalid_range.any():
        raise BenchmarkDataValidationError("Benchmark OHLC values violate low <= open/close <= high.")
    for column in ("volume", "amount"):
        if normalized[column].dropna().lt(0).any():
            raise BenchmarkDataValidationError(f"Benchmark {column} must be nonnegative when present.")
    records: list[dict[str, Any]] = []
    for record in normalized[BENCHMARK_INDEX_DAILY_COLUMNS].sort_values(
        ["index_code", "trade_date"]
    ).to_dict(orient="records"):
        records.append(
            {
                key: (None if pd.isna(value) else value)
                for key, value in record.items()
            }
        )
    return records


def _finite_numeric(series: pd.Series, field: str, *, nullable: bool) -> pd.Series:
    numeric = pd.to_numeric(series, errors="coerce")
    if not nullable and numeric.isna().any():
        raise BenchmarkDataValidationError(f"Benchmark {field} must be finite.")
    non_null = numeric.dropna().astype(float)
    if not all(math.isfinite(value) for value in non_null):
        raise BenchmarkDataValidationError(f"Benchmark {field} must be finite when present.")
    return numeric


def _request_metadata(value: dict[str, Any] | None) -> dict[str, Any]:
    metadata = canonical_json_object(value, "provider_request_metadata")
    _reject_sensitive(metadata)
    return metadata


def _reject_sensitive(value: Any, path: str = "provider_request_metadata") -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            lowered = key.lower()
            if any(term in lowered for term in SENSITIVE_METADATA_TERMS):
                raise BenchmarkDataValidationError(f"Sensitive metadata field is not allowed: {path}.{key}.")
            _reject_sensitive(item, f"{path}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _reject_sensitive(item, f"{path}[{index}]")


def _required_text(value: Any, field: str) -> str:
    normalized = "" if value is None else str(value).strip()
    if not normalized:
        raise BenchmarkDataValidationError(f"{field} must not be blank.")
    return normalized


def _index_code(value: Any) -> str:
    normalized = _required_text(value, "index_code")
    if not INDEX_CODE_PATTERN.fullmatch(normalized):
        raise BenchmarkDataValidationError("Benchmark index codes must be six digits.")
    return normalized


def _required_date(value: Any, field: str) -> date:
    normalized = _required_text(value, field).replace("-", "")
    try:
        return datetime.strptime(normalized, "%Y%m%d").date()
    except ValueError as exc:
        raise BenchmarkDataValidationError(f"{field} must use YYYYMMDD format.") from exc


def _compact_date(value: date) -> str:
    return value.strftime("%Y%m%d")


def _raw_count(bundle: Any) -> int:
    frame = getattr(bundle, BENCHMARK_DATASET, None)
    return len(frame) if isinstance(frame, pd.DataFrame) else 0


def _frame_payload(frame: Any) -> Any:
    if not isinstance(frame, pd.DataFrame):
        return {"type": type(frame).__name__}
    return _json_rows(frame.to_dict(orient="records"))


def _json_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [{key: _json_value(value) for key, value in row.items()} for row in rows]


def _json_value(value: Any) -> Any:
    if value is None or pd.isna(value):
        return None
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if hasattr(value, "item"):
        return value.item()
    return value


def _hash_payload(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _error_summary(exc: Exception) -> str:
    return f"{type(exc).__name__}: {str(exc).splitlines()[0]}"[:500]


def _result(
    run: IngestionRun,
    *,
    idempotent: bool,
    rows_written: int,
) -> BenchmarkIngestionResult:
    return BenchmarkIngestionResult(
        ingestion_run_id=run.id,
        batch_identifier=run.batch_identifier,
        series_key=run.series_key,
        status=run.status,
        information_cutoff_date=_compact_date(run.information_cutoff_date),
        rows_received=run.row_count_received,
        rows_written=rows_written,
        dataset_counts=dict(run.dataset_counts),
        idempotent=idempotent,
    )
