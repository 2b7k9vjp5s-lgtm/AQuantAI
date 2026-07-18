"""Validated transactional persistence for exact sector complete snapshots."""

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

from backend.database.models import (
    IngestionRun,
    SectorDailyRecord,
    SectorDefinitionRecord,
)
from backend.database.series import (
    SectorSeriesIdentity,
    build_sector_series_identity,
    canonical_json_object,
)
from datasource.base import (
    SECTOR_DAILY_COLUMNS,
    SECTOR_DEFINITION_COLUMNS,
    SectorMarketBundle,
)

SECTOR_DATASET = "sector_market_bundle"
SECTOR_DEFINITION_DATASET = "sector_definition"
SECTOR_DAILY_DATASET = "sector_daily"
SECTOR_DEFINITION_CONTRACT_VERSION = "1.0"
SECTOR_DAILY_CONTRACT_VERSION = "1.0"
SECTOR_SNAPSHOT_MODE = "complete"
SECTOR_SCOPE_SEMANTICS = "exact"
DEFAULT_SECTOR_TAXONOMY_ENDPOINT = "stock_board_industry_name_em"
DEFAULT_SECTOR_HISTORY_ENDPOINT = "stock_board_industry_hist_em"
DEFAULT_SECTOR_CLASSIFICATION_SYSTEM = "eastmoney_industry_board"
DEFAULT_SECTOR_CLASSIFICATION_LEVEL: str | None = None
DEFAULT_SECTOR_ADAPTER_VERSION = "aquantai.akshare-sector-adapter.v1"
SECTOR_CODE_PATTERN = re.compile(r"^BK[0-9]+$")
SENSITIVE_METADATA_TERMS = {
    "api_key", "apikey", "cookie", "credential", "database_url", "password",
    "secret", "token",
}


class SectorDataValidationError(ValueError):
    """Raised before invalid sector rows can enter a snapshot."""


@dataclass(frozen=True)
class SectorIngestionResult:
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
class SectorValidationSummary:
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


def validate_sector_bundle(
    bundle: SectorMarketBundle,
    *,
    provider: str,
    requested_start_date: str,
    requested_end_date: str,
    information_cutoff_date: str,
    requested_scope: dict[str, Any],
    taxonomy_endpoint: str = DEFAULT_SECTOR_TAXONOMY_ENDPOINT,
    history_endpoint: str = DEFAULT_SECTOR_HISTORY_ENDPOINT,
    adapter_compatibility_version: str = DEFAULT_SECTOR_ADAPTER_VERSION,
    compatibility_parameters: dict[str, Any] | None = None,
) -> SectorValidationSummary:
    provider_text, start, end, cutoff, scope, series = _request_context(
        provider=provider,
        requested_start_date=requested_start_date,
        requested_end_date=requested_end_date,
        information_cutoff_date=information_cutoff_date,
        requested_scope=requested_scope,
        taxonomy_endpoint=taxonomy_endpoint,
        history_endpoint=history_endpoint,
        adapter_compatibility_version=adapter_compatibility_version,
        compatibility_parameters=compatibility_parameters,
    )
    definitions, daily = _normalize_bundle(bundle, provider_text, start, end, cutoff, scope)
    return SectorValidationSummary(
        series_key=series.series_key,
        canonical_scope=series.canonical,
        information_cutoff_date=_compact_date(cutoff),
        dataset_counts={
            SECTOR_DEFINITION_DATASET: len(definitions),
            SECTOR_DAILY_DATASET: len(daily),
        },
    )


class SectorPersistenceService:
    """Persist one exact sector complete snapshot with immutable attempts."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def ingest_bundle(
        self,
        bundle: SectorMarketBundle,
        *,
        provider: str,
        requested_start_date: str,
        requested_end_date: str,
        information_cutoff_date: str,
        requested_scope: dict[str, Any],
        taxonomy_endpoint: str = DEFAULT_SECTOR_TAXONOMY_ENDPOINT,
        history_endpoint: str = DEFAULT_SECTOR_HISTORY_ENDPOINT,
        adapter_compatibility_version: str = DEFAULT_SECTOR_ADAPTER_VERSION,
        provider_request_metadata: dict[str, Any] | None = None,
        adapter_version: str = DEFAULT_SECTOR_ADAPTER_VERSION,
        compatibility_parameters: dict[str, Any] | None = None,
    ) -> SectorIngestionResult:
        provider_text, start, end, cutoff, scope, series = _request_context(
            provider=provider,
            requested_start_date=requested_start_date,
            requested_end_date=requested_end_date,
            information_cutoff_date=information_cutoff_date,
            requested_scope=requested_scope,
            taxonomy_endpoint=taxonomy_endpoint,
            history_endpoint=history_endpoint,
            adapter_compatibility_version=adapter_compatibility_version,
            compatibility_parameters=compatibility_parameters,
        )
        metadata = _request_metadata(provider_request_metadata)
        normalized_adapter = _required_text(adapter_version, "adapter_version")
        raw_count = _raw_count(bundle)
        try:
            definitions, daily = _normalize_bundle(
                bundle, provider_text, start, end, cutoff, scope
            )
        except Exception as exc:
            run_id = self._create_pending_run(
                batch_identifier=_hash_payload({
                    "raw": _bundle_payload(bundle),
                    "series_key": series.series_key,
                    "cutoff": _compact_date(cutoff),
                }),
                provider=provider_text,
                start=start,
                end=end,
                cutoff=cutoff,
                scope=scope,
                series=series,
                metadata=metadata,
                adapter_version=normalized_adapter,
                row_count=raw_count,
                dataset_counts=_raw_dataset_counts(bundle),
            )
            self._mark_failed(run_id, exc)
            raise
        counts = {
            SECTOR_DEFINITION_DATASET: len(definitions),
            SECTOR_DAILY_DATASET: len(daily),
        }
        batch_identifier = _hash_payload({
            "definitions": _json_rows(definitions),
            "daily": _json_rows(daily),
            "series_key": series.series_key,
            "cutoff": _compact_date(cutoff),
            "snapshot_mode": SECTOR_SNAPSHOT_MODE,
        })
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
            row_count=sum(counts.values()),
            dataset_counts=counts,
        )
        try:
            with self._session_factory.begin() as session:
                run = session.get(IngestionRun, run_id, with_for_update=True)
                if run is None:
                    raise RuntimeError(f"Sector ingestion run {run_id} disappeared.")
                session.add_all(
                    [SectorDefinitionRecord(ingestion_run_id=run_id, **row) for row in definitions]
                )
                session.add_all(
                    [SectorDailyRecord(ingestion_run_id=run_id, **row) for row in daily]
                )
                run.status = "succeeded"
                run.row_count_written = sum(counts.values())
                run.completed_at = datetime.now(timezone.utc)
                run.error_summary = None
        except IntegrityError as exc:
            concurrent = self._find_success(batch_identifier, series.series_key)
            if concurrent is not None:
                self._mark_failed(
                    run_id,
                    RuntimeError(
                        f"Concurrent identical sector batch completed as run {concurrent.id}."
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
                raise RuntimeError(f"Sector ingestion run {run_id} is unavailable after commit.")
            return _result(run, idempotent=False, rows_written=sum(counts.values()))

    def record_failed_attempt(
        self,
        exc: Exception,
        *,
        provider: str,
        requested_start_date: str,
        requested_end_date: str,
        information_cutoff_date: str,
        requested_scope: dict[str, Any],
        taxonomy_endpoint: str = DEFAULT_SECTOR_TAXONOMY_ENDPOINT,
        history_endpoint: str = DEFAULT_SECTOR_HISTORY_ENDPOINT,
        adapter_compatibility_version: str = DEFAULT_SECTOR_ADAPTER_VERSION,
        provider_request_metadata: dict[str, Any] | None = None,
        adapter_version: str = DEFAULT_SECTOR_ADAPTER_VERSION,
    ) -> int:
        provider_text, start, end, cutoff, scope, series = _request_context(
            provider=provider,
            requested_start_date=requested_start_date,
            requested_end_date=requested_end_date,
            information_cutoff_date=information_cutoff_date,
            requested_scope=requested_scope,
            taxonomy_endpoint=taxonomy_endpoint,
            history_endpoint=history_endpoint,
            adapter_compatibility_version=adapter_compatibility_version,
            compatibility_parameters=None,
        )
        metadata = _request_metadata(provider_request_metadata)
        run_id = self._create_pending_run(
            batch_identifier=_hash_payload({
                "provider_failure": _error_summary(exc),
                "series_key": series.series_key,
                "cutoff": _compact_date(cutoff),
                "metadata": metadata,
            }),
            provider=provider_text,
            start=start,
            end=end,
            cutoff=cutoff,
            scope=scope,
            series=series,
            metadata=metadata,
            adapter_version=_required_text(adapter_version, "adapter_version"),
            row_count=0,
            dataset_counts={SECTOR_DEFINITION_DATASET: 0, SECTOR_DAILY_DATASET: 0},
        )
        self._mark_failed(run_id, exc)
        return run_id

    def _find_success(self, batch_identifier: str, series_key: str) -> IngestionRun | None:
        with self._session_factory() as session:
            return session.scalar(select(IngestionRun).where(
                IngestionRun.batch_identifier == batch_identifier,
                IngestionRun.series_key == series_key,
                IngestionRun.status == "succeeded",
            ))

    def _create_pending_run(
        self,
        *,
        batch_identifier: str,
        provider: str,
        start: date,
        end: date,
        cutoff: date,
        scope: dict[str, Any],
        series: SectorSeriesIdentity,
        metadata: dict[str, Any],
        adapter_version: str,
        row_count: int,
        dataset_counts: dict[str, int],
    ) -> int:
        with self._session_factory.begin() as session:
            run = IngestionRun(
                batch_identifier=batch_identifier,
                series_key=series.series_key,
                series_identity=series.canonical,
                provider=provider,
                dataset=SECTOR_DATASET,
                imported_at=datetime.now(timezone.utc),
                requested_start_date=start,
                requested_end_date=end,
                information_cutoff_date=cutoff,
                requested_scope=scope,
                provider_request_metadata=metadata,
                adapter_version=adapter_version,
                snapshot_mode=SECTOR_SNAPSHOT_MODE,
                contract_version=(
                    f"definition:{SECTOR_DEFINITION_CONTRACT_VERSION};"
                    f"daily:{SECTOR_DAILY_CONTRACT_VERSION}"
                ),
                status="pending",
                row_count_received=row_count,
                row_count_written=0,
                dataset_counts=dataset_counts,
            )
            session.add(run)
            session.flush()
            return run.id

    def _mark_failed(self, run_id: int, exc: Exception) -> None:
        with self._session_factory.begin() as session:
            run = session.get(IngestionRun, run_id, with_for_update=True)
            if run is None:
                raise RuntimeError(f"Could not record sector failure for run {run_id}.") from exc
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
    taxonomy_endpoint: str,
    history_endpoint: str,
    adapter_compatibility_version: str,
    compatibility_parameters: dict[str, Any] | None,
) -> tuple[str, date, date, date, dict[str, Any], SectorSeriesIdentity]:
    provider_text = _required_text(provider, "provider")
    start = _required_date(requested_start_date, "requested_start_date")
    end = _required_date(requested_end_date, "requested_end_date")
    cutoff = _required_date(information_cutoff_date, "information_cutoff_date")
    if start > end:
        raise SectorDataValidationError("requested_start_date must not be after requested_end_date.")
    if end > cutoff:
        raise SectorDataValidationError("requested_end_date must not exceed information_cutoff_date.")
    scope = _validate_scope(requested_scope)
    _reject_sensitive(compatibility_parameters or {}, "compatibility_parameters")
    series = build_sector_series_identity(
        provider=provider_text,
        sector_definition_contract_version=SECTOR_DEFINITION_CONTRACT_VERSION,
        sector_daily_contract_version=SECTOR_DAILY_CONTRACT_VERSION,
        sector_codes=scope["sector_codes"],
        requested_start_date=_compact_date(start),
        requested_end_date=_compact_date(end),
        taxonomy_endpoint=taxonomy_endpoint,
        history_endpoint=history_endpoint,
        classification_system=scope["classification_system"],
        classification_level=scope["classification_level"],
        adapter_compatibility_version=adapter_compatibility_version,
        compatibility_parameters=compatibility_parameters,
    )
    return provider_text, start, end, cutoff, scope, series


def _validate_scope(value: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise SectorDataValidationError("requested_scope must be a dictionary.")
    allowed = {
        "datasets", "sector_codes", "sector_code_semantics",
        "classification_system", "classification_level",
    }
    unknown = sorted(set(value) - allowed)
    if unknown:
        raise SectorDataValidationError(f"requested_scope contains unknown fields: {unknown}.")
    datasets = sorted({_required_text(item, "requested_scope.datasets") for item in value.get("datasets", [])})
    expected = [SECTOR_DAILY_DATASET, SECTOR_DEFINITION_DATASET]
    if datasets != expected:
        raise SectorDataValidationError(f"requested_scope.datasets must be exactly {expected}.")
    raw_codes = value.get("sector_codes")
    if not isinstance(raw_codes, list):
        raise SectorDataValidationError("requested_scope.sector_codes must be a list.")
    codes = sorted({_sector_code(item) for item in raw_codes})
    if not codes or len(codes) != len(raw_codes):
        raise SectorDataValidationError(
            "requested_scope.sector_codes must be non-empty and contain no duplicates."
        )
    if len(codes) > 30:
        raise SectorDataValidationError("At most 30 sector codes are allowed.")
    semantics = _required_text(value.get("sector_code_semantics"), "sector_code_semantics")
    if semantics != SECTOR_SCOPE_SEMANTICS:
        raise SectorDataValidationError("sector_code_semantics must be 'exact'.")
    system = _required_text(value.get("classification_system"), "classification_system")
    level = _optional_text(value.get("classification_level"), "classification_level")
    return {
        "datasets": expected,
        "sector_codes": codes,
        "sector_code_semantics": semantics,
        "classification_system": system,
        "classification_level": level,
    }


def _normalize_bundle(
    bundle: SectorMarketBundle,
    provider: str,
    start: date,
    end: date,
    cutoff: date,
    scope: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if not isinstance(bundle, SectorMarketBundle):
        raise SectorDataValidationError("bundle must be a SectorMarketBundle.")
    definitions = _normalize_definitions(bundle.sector_definition, provider, scope)
    daily = _normalize_daily(bundle.sector_daily, provider, start, end, cutoff, scope)
    definition_codes = sorted(row["sector_code"] for row in definitions)
    daily_codes = sorted({row["sector_code"] for row in daily})
    if definition_codes != scope["sector_codes"] or daily_codes != scope["sector_codes"]:
        raise SectorDataValidationError(
            "Sector definition and daily rows must both match the exact requested scope."
        )
    return definitions, daily


def _normalize_definitions(
    frame: Any, provider: str, scope: dict[str, Any]
) -> list[dict[str, Any]]:
    if not isinstance(frame, pd.DataFrame):
        raise SectorDataValidationError("sector_definition must be a DataFrame.")
    required = {"source", "sector_code", "sector_name", "classification_system"}
    missing = sorted(required - set(frame.columns))
    unknown = sorted(set(frame.columns) - set(SECTOR_DEFINITION_COLUMNS))
    if missing or unknown:
        raise SectorDataValidationError(
            f"sector_definition contract mismatch; missing={missing}, unknown={unknown}."
        )
    normalized = frame.copy()
    for column in SECTOR_DEFINITION_COLUMNS:
        if column not in normalized.columns:
            normalized[column] = pd.NA
    if normalized.empty:
        raise SectorDataValidationError("sector_definition must not be empty.")
    normalized["source"] = normalized["source"].map(lambda value: _required_text(value, "source"))
    normalized["sector_code"] = normalized["sector_code"].map(_sector_code)
    normalized["sector_name"] = normalized["sector_name"].map(lambda value: _required_text(value, "sector_name"))
    normalized["classification_system"] = normalized["classification_system"].map(
        lambda value: _required_text(value, "classification_system")
    )
    normalized["classification_level"] = normalized["classification_level"].map(
        lambda value: _optional_text(value, "classification_level")
    )
    normalized["parent_sector_code"] = normalized["parent_sector_code"].map(
        lambda value: _optional_sector_code(value, "parent_sector_code")
    )
    normalized["parent_sector_name"] = normalized["parent_sector_name"].map(
        lambda value: _optional_text(value, "parent_sector_name")
    )
    if set(normalized["source"]) != {provider}:
        raise SectorDataValidationError("Every sector definition source must equal provider.")
    if set(normalized["classification_system"]) != {scope["classification_system"]}:
        raise SectorDataValidationError("Sector definitions use an incompatible classification system.")
    if set(normalized["classification_level"]) != {scope["classification_level"]}:
        raise SectorDataValidationError("Sector definitions use an incompatible classification level.")
    observed = sorted(normalized["sector_code"].unique())
    if observed != scope["sector_codes"] or len(normalized) != len(scope["sector_codes"]):
        raise SectorDataValidationError(
            f"Sector definitions must match exact scope; expected={scope['sector_codes']}, observed={observed}."
        )
    if normalized.duplicated(["source", "classification_system", "classification_level", "sector_code"]).any():
        raise SectorDataValidationError("Duplicate sector definition identifiers are not allowed.")
    parent_pair = normalized[["parent_sector_code", "parent_sector_name"]].notna()
    if (parent_pair.any(axis=1) & ~parent_pair.all(axis=1)).any():
        raise SectorDataValidationError("Sector parent code and name must be both present or both null.")
    return _records(normalized, SECTOR_DEFINITION_COLUMNS, ["sector_code"])


def _normalize_daily(
    frame: Any,
    provider: str,
    start: date,
    end: date,
    cutoff: date,
    scope: dict[str, Any],
) -> list[dict[str, Any]]:
    if not isinstance(frame, pd.DataFrame):
        raise SectorDataValidationError("sector_daily must be a DataFrame.")
    required = {"source", "sector_code", "trade_date", "close"}
    missing = sorted(required - set(frame.columns))
    unknown = sorted(set(frame.columns) - set(SECTOR_DAILY_COLUMNS))
    if missing or unknown:
        raise SectorDataValidationError(
            f"sector_daily contract mismatch; missing={missing}, unknown={unknown}."
        )
    normalized = frame.copy()
    for column in SECTOR_DAILY_COLUMNS:
        if column not in normalized.columns:
            normalized[column] = pd.NA
    if normalized.empty:
        raise SectorDataValidationError("sector_daily must not be empty.")
    normalized["source"] = normalized["source"].map(lambda value: _required_text(value, "source"))
    normalized["sector_code"] = normalized["sector_code"].map(_sector_code)
    if set(normalized["source"]) != {provider}:
        raise SectorDataValidationError("Every sector daily source must equal provider.")
    observed = sorted(normalized["sector_code"].unique())
    if observed != scope["sector_codes"]:
        raise SectorDataValidationError(
            f"Sector daily rows must match exact scope; expected={scope['sector_codes']}, observed={observed}."
        )
    try:
        normalized["trade_date"] = pd.to_datetime(normalized["trade_date"], errors="raise").dt.date
    except (TypeError, ValueError) as exc:
        raise SectorDataValidationError("Sector trade_date must contain valid dates.") from exc
    if normalized["trade_date"].lt(start).any() or normalized["trade_date"].gt(end).any():
        raise SectorDataValidationError("Sector trade_date is outside the requested range.")
    if normalized["trade_date"].gt(cutoff).any():
        raise SectorDataValidationError("Sector trade_date exceeds information cutoff.")
    if normalized.duplicated(["source", "sector_code", "trade_date"]).any():
        raise SectorDataValidationError("Duplicate sector source/code/trade_date rows are not allowed.")
    normalized["close"] = _finite_numeric(normalized["close"], "close", nullable=False)
    if normalized["close"].le(0).any():
        raise SectorDataValidationError("Sector close must be positive.")
    for column in ("open", "high", "low", "volume", "amount", "turnover_rate"):
        normalized[column] = _finite_numeric(normalized[column], column, nullable=True)
    ohlc_present = normalized[["open", "high", "low"]].notna()
    if (ohlc_present.any(axis=1) & ~ohlc_present.all(axis=1)).any():
        raise SectorDataValidationError("Sector open/high/low must be all present or all null per row.")
    complete = ohlc_present.all(axis=1)
    if (normalized.loc[complete, ["open", "high", "low"]] <= 0).any().any():
        raise SectorDataValidationError("Sector OHLC prices must be positive.")
    invalid_range = complete & (
        (normalized["low"] > normalized["open"])
        | (normalized["open"] > normalized["high"])
        | (normalized["low"] > normalized["close"])
        | (normalized["close"] > normalized["high"])
    )
    if invalid_range.any():
        raise SectorDataValidationError("Sector OHLC values violate low <= open/close <= high.")
    for column in ("volume", "amount", "turnover_rate"):
        if normalized[column].dropna().lt(0).any():
            raise SectorDataValidationError(f"Sector {column} must be nonnegative when present.")
    return _records(normalized, SECTOR_DAILY_COLUMNS, ["sector_code", "trade_date"])


def _finite_numeric(series: pd.Series, field: str, *, nullable: bool) -> pd.Series:
    numeric = pd.to_numeric(series, errors="coerce")
    if not nullable and numeric.isna().any():
        raise SectorDataValidationError(f"Sector {field} must be finite.")
    values = numeric.dropna().astype(float)
    if not all(math.isfinite(value) for value in values):
        raise SectorDataValidationError(f"Sector {field} must be finite when present.")
    return numeric


def _records(frame: pd.DataFrame, columns: list[str], order: list[str]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for record in frame[columns].sort_values(order).to_dict(orient="records"):
        records.append({key: (None if pd.isna(value) else value) for key, value in record.items()})
    return records


def _request_metadata(value: dict[str, Any] | None) -> dict[str, Any]:
    metadata = canonical_json_object(value, "provider_request_metadata")
    _reject_sensitive(metadata)
    return metadata


def _reject_sensitive(value: Any, path: str = "provider_request_metadata") -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            if any(term in key.lower() for term in SENSITIVE_METADATA_TERMS):
                raise SectorDataValidationError(f"Sensitive metadata field is not allowed: {path}.{key}.")
            _reject_sensitive(item, f"{path}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _reject_sensitive(item, f"{path}[{index}]")


def _required_text(value: Any, field: str) -> str:
    if value is None or (not isinstance(value, (dict, list)) and pd.isna(value)):
        raise SectorDataValidationError(f"{field} must not be blank.")
    normalized = str(value).strip()
    if not normalized:
        raise SectorDataValidationError(f"{field} must not be blank.")
    return normalized


def _optional_text(value: Any, field: str) -> str | None:
    if value is None or (not isinstance(value, (dict, list)) and pd.isna(value)):
        return None
    normalized = str(value).strip()
    if not normalized:
        raise SectorDataValidationError(f"{field} must be null or nonblank.")
    return normalized


def _sector_code(value: Any) -> str:
    normalized = _required_text(value, "sector_code").upper()
    if not SECTOR_CODE_PATTERN.fullmatch(normalized):
        raise SectorDataValidationError("Sector codes must be stable Eastmoney BK identifiers.")
    return normalized


def _optional_sector_code(value: Any, field: str) -> str | None:
    text = _optional_text(value, field)
    return _sector_code(text) if text is not None else None


def _required_date(value: Any, field: str) -> date:
    normalized = _required_text(value, field).replace("-", "")
    try:
        return datetime.strptime(normalized, "%Y%m%d").date()
    except ValueError as exc:
        raise SectorDataValidationError(f"{field} must use YYYYMMDD format.") from exc


def _compact_date(value: date) -> str:
    return value.strftime("%Y%m%d")


def _raw_count(bundle: Any) -> int:
    return sum(_raw_dataset_counts(bundle).values())


def _raw_dataset_counts(bundle: Any) -> dict[str, int]:
    return {
        name: len(getattr(bundle, name, [])) if isinstance(getattr(bundle, name, None), pd.DataFrame) else 0
        for name in (SECTOR_DEFINITION_DATASET, SECTOR_DAILY_DATASET)
    }


def _bundle_payload(bundle: Any) -> dict[str, Any]:
    return {
        name: _frame_payload(getattr(bundle, name, None))
        for name in (SECTOR_DEFINITION_DATASET, SECTOR_DAILY_DATASET)
    }


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


def _result(run: IngestionRun, *, idempotent: bool, rows_written: int) -> SectorIngestionResult:
    return SectorIngestionResult(
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
