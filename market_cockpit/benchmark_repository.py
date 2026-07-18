"""Single-run repository for benchmark-index context."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Any

import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.database.benchmark_data import BENCHMARK_DATASET
from backend.database.models import BenchmarkIndexDailyRecord, IngestionRun
from backend.database.series import (
    BenchmarkSeriesIdentity,
    validate_benchmark_series_identity,
    validate_series_key,
)
from datasource.base import BENCHMARK_INDEX_DAILY_COLUMNS

PUBLIC_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")


class BenchmarkSelectionError(ValueError):
    """Raised when a benchmark selector is missing, incomplete, or incompatible."""


class BenchmarkSnapshotNotFound(LookupError):
    """Raised when no eligible successful benchmark snapshot exists."""


@dataclass(frozen=True)
class PersistedBenchmarkSnapshot:
    series_key: str
    ingestion_run_id: int
    provider: str
    contract_version: str
    adapter_version: str
    information_cutoff_date: str
    requested_start_date: str
    requested_end_date: str
    index_codes: list[str]
    endpoint: str
    frequency: str
    adapter_compatibility_version: str
    ingestion_imported_at_utc: str
    ingestion_completed_at_utc: str | None
    collection_timestamp_utc: str | None
    effective_information_cutoff_date: str | None
    akshare_package_version: str | None
    network_mode: str | None
    timeout_seconds: float | None
    max_retries: int | None
    effective_benchmark_session: str
    series_identity: dict[str, Any]
    benchmark_index_daily: pd.DataFrame


class BenchmarkRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def load_snapshot(
        self,
        *,
        series_key: str | None = None,
        selector: BenchmarkSeriesIdentity | None = None,
        as_of_cutoff: str | None = None,
        permitted_end_session: str | None = None,
    ) -> PersistedBenchmarkSnapshot:
        resolved_key, canonical = _resolve_selector(series_key, selector)
        cutoff = _optional_date(as_of_cutoff, "as_of_cutoff")
        permitted = _optional_date(permitted_end_session, "permitted_end_session")
        statement = select(IngestionRun).where(
            IngestionRun.series_key == resolved_key,
            IngestionRun.dataset == BENCHMARK_DATASET,
            IngestionRun.status == "succeeded",
            IngestionRun.snapshot_mode == "complete",
        )
        if cutoff is not None:
            statement = statement.where(IngestionRun.information_cutoff_date <= cutoff)
        run = self._session.scalar(
            statement.order_by(
                IngestionRun.information_cutoff_date.desc(),
                IngestionRun.completed_at.desc(),
                IngestionRun.id.desc(),
            ).limit(1)
        )
        if run is None:
            suffix = f" at or before cutoff {_compact_date(cutoff)}" if cutoff else ""
            raise BenchmarkSnapshotNotFound(
                f"No successful complete benchmark snapshot exists for series {resolved_key}{suffix}."
            )
        stored = validate_benchmark_series_identity(
            BenchmarkSeriesIdentity(run.series_key, dict(run.series_identity))
        )
        if canonical is not None and stored.canonical != canonical:
            raise BenchmarkSelectionError(
                "The canonical benchmark selector does not match the persisted series."
            )
        identity = stored.canonical
        bound = min(
            value
            for value in (
                run.information_cutoff_date,
                run.requested_end_date,
                cutoff,
                permitted,
            )
            if value is not None
        )
        rows = self._session.execute(
            select(
                *(getattr(BenchmarkIndexDailyRecord, column) for column in BENCHMARK_INDEX_DAILY_COLUMNS)
            )
            .where(
                BenchmarkIndexDailyRecord.ingestion_run_id == run.id,
                BenchmarkIndexDailyRecord.trade_date <= bound,
            )
            .order_by(BenchmarkIndexDailyRecord.index_code, BenchmarkIndexDailyRecord.trade_date)
        ).mappings()
        records = [dict(row) for row in rows]
        if not records:
            raise BenchmarkSnapshotNotFound(
                f"Benchmark snapshot {run.id} has no rows at or before permitted session {_compact_date(bound)}."
            )
        for record in records:
            record["trade_date"] = _compact_date(record["trade_date"])
        frame = pd.DataFrame(records, columns=BENCHMARK_INDEX_DAILY_COLUMNS)
        metadata = dict(run.provider_request_metadata or {})
        effective = max(frame["trade_date"].astype(str))
        return PersistedBenchmarkSnapshot(
            series_key=run.series_key,
            ingestion_run_id=run.id,
            provider=run.provider,
            contract_version=run.contract_version,
            adapter_version=run.adapter_version,
            information_cutoff_date=_compact_date(run.information_cutoff_date),
            requested_start_date=_compact_date(run.requested_start_date),
            requested_end_date=_compact_date(run.requested_end_date),
            index_codes=list(identity["index_codes"]),
            endpoint=str(identity["endpoint"]),
            frequency=str(identity["frequency"]),
            adapter_compatibility_version=str(identity["adapter_compatibility_version"]),
            ingestion_imported_at_utc=_utc_iso(run.imported_at),
            ingestion_completed_at_utc=_utc_iso_or_none(run.completed_at),
            collection_timestamp_utc=_utc_iso_or_none(metadata.get("collection_timestamp_utc")),
            effective_information_cutoff_date=_optional_metadata_date(
                metadata.get("effective_information_cutoff_date")
            ),
            akshare_package_version=_public_identifier(metadata.get("akshare_package_version")),
            network_mode=_public_identifier(metadata.get("network_mode")),
            timeout_seconds=_finite_number(metadata.get("timeout_seconds")),
            max_retries=_nonnegative_int(metadata.get("max_retries")),
            effective_benchmark_session=effective,
            series_identity=identity,
            benchmark_index_daily=frame,
        )


def _resolve_selector(
    series_key: str | None,
    selector: BenchmarkSeriesIdentity | None,
) -> tuple[str, dict[str, Any] | None]:
    if series_key is None and selector is None:
        raise BenchmarkSelectionError(
            "Benchmark context requires an explicit benchmark series_key or complete canonical selector."
        )
    if series_key is not None and selector is not None:
        raise BenchmarkSelectionError("Provide benchmark series_key or selector, not both.")
    if selector is not None:
        validated = validate_benchmark_series_identity(selector)
        return validated.series_key, validated.canonical
    return validate_series_key(series_key or ""), None


def _optional_date(value: str | None, field: str) -> date | None:
    if value is None:
        return None
    normalized = str(value).strip().replace("-", "")
    try:
        return datetime.strptime(normalized, "%Y%m%d").date()
    except ValueError as exc:
        raise BenchmarkSelectionError(f"{field} must use YYYYMMDD format.") from exc


def _compact_date(value: date | None) -> str:
    return value.strftime("%Y%m%d") if value is not None else ""


def _utc_iso(value: datetime | str) -> str:
    if isinstance(value, datetime):
        parsed = value
    else:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _utc_iso_or_none(value: Any) -> str | None:
    if value is None or str(value).strip() == "":
        return None
    try:
        return _utc_iso(value)
    except (TypeError, ValueError):
        return None


def _optional_metadata_date(value: Any) -> str | None:
    if value is None:
        return None
    try:
        return datetime.strptime(str(value).replace("-", ""), "%Y%m%d").strftime("%Y%m%d")
    except ValueError:
        return None


def _public_identifier(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip()
    return normalized if PUBLIC_IDENTIFIER.fullmatch(normalized) else None


def _finite_number(value: Any) -> float | None:
    if value is None:
        return None
    try:
        normalized = float(value)
    except (TypeError, ValueError):
        return None
    return normalized if math.isfinite(normalized) and normalized > 0 else None


def _nonnegative_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    try:
        normalized = int(value)
    except (TypeError, ValueError):
        return None
    return normalized if normalized >= 0 else None
