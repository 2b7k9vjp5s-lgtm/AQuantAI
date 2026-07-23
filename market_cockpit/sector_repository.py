"""Single-run repository for selected-sector context."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Any

import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.database.models import IngestionRun, SectorDailyRecord, SectorDefinitionRecord
from backend.database.sector_data import SECTOR_DATASET
from backend.database.series import (
    SectorSeriesIdentity,
    validate_sector_series_identity,
    validate_series_key,
)
from datasource.base import SECTOR_DAILY_COLUMNS, SECTOR_DEFINITION_COLUMNS

PUBLIC_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")


class SectorSelectionError(ValueError):
    """Raised when a sector selector is missing, incomplete, or incompatible."""


class SectorSnapshotNotFound(LookupError):
    """Raised when no eligible successful sector snapshot exists."""


@dataclass(frozen=True)
class PersistedSectorSnapshot:
    series_key: str
    ingestion_run_id: int
    provider: str
    definition_contract_version: str
    daily_contract_version: str
    adapter_version: str
    adapter_compatibility_version: str
    information_cutoff_date: str
    requested_start_date: str
    requested_end_date: str
    sector_codes: list[str]
    taxonomy_endpoint: str
    history_endpoint: str
    classification_system: str
    classification_level: str | None
    frequency: str
    adjust_type: str
    ingestion_imported_at_utc: str
    ingestion_completed_at_utc: str | None
    collection_timestamp_utc: str | None
    effective_information_cutoff_date: str | None
    akshare_package_version: str | None
    network_mode: str | None
    timeout_seconds: float | None
    max_retries: int | None
    series_identity: dict[str, Any]
    sector_definition: pd.DataFrame
    sector_daily: pd.DataFrame


class SectorRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def load_snapshot(
        self,
        *,
        series_key: str | None = None,
        selector: SectorSeriesIdentity | None = None,
        as_of_cutoff: str | None = None,
        permitted_end_session: str | None = None,
        as_of_recorded_at_utc: datetime | str | None = None,
    ) -> PersistedSectorSnapshot:
        resolved_key, canonical = _resolve_selector(series_key, selector)
        cutoff = _optional_date(as_of_cutoff, "as_of_cutoff")
        permitted = _optional_date(permitted_end_session, "permitted_end_session")
        recorded_at = _optional_recorded_at(as_of_recorded_at_utc)
        statement = select(IngestionRun).where(
            IngestionRun.series_key == resolved_key,
            IngestionRun.dataset == SECTOR_DATASET,
            IngestionRun.status == "succeeded",
            IngestionRun.snapshot_mode == "complete",
        )
        if cutoff is not None:
            statement = statement.where(IngestionRun.information_cutoff_date <= cutoff)
        if recorded_at is not None:
            statement = statement.where(
                IngestionRun.imported_at <= recorded_at,
                IngestionRun.completed_at.is_not(None),
                IngestionRun.completed_at <= recorded_at,
            )
        run = self._session.scalar(
            statement.order_by(
                IngestionRun.information_cutoff_date.desc(),
                IngestionRun.completed_at.desc(),
                IngestionRun.id.desc(),
            ).limit(1)
        )
        if run is None:
            boundaries: list[str] = []
            if cutoff is not None:
                boundaries.append(f"cutoff {_compact_date(cutoff)}")
            if recorded_at is not None:
                boundaries.append(f"recorded UTC {_utc_iso(recorded_at)}")
            suffix = f" at or before {' and '.join(boundaries)}" if boundaries else ""
            raise SectorSnapshotNotFound(
                f"No successful complete sector snapshot exists for series {resolved_key}{suffix}."
            )
        stored = validate_sector_series_identity(
            SectorSeriesIdentity(run.series_key, dict(run.series_identity))
        )
        if canonical is not None and stored.canonical != canonical:
            raise SectorSelectionError(
                "The canonical sector selector does not match the persisted series."
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
        definition_rows = self._session.execute(
            select(
                *(getattr(SectorDefinitionRecord, column) for column in SECTOR_DEFINITION_COLUMNS)
            )
            .where(SectorDefinitionRecord.ingestion_run_id == run.id)
            .order_by(SectorDefinitionRecord.sector_code)
        ).mappings()
        definitions = [dict(row) for row in definition_rows]
        daily_rows = self._session.execute(
            select(*(getattr(SectorDailyRecord, column) for column in SECTOR_DAILY_COLUMNS))
            .where(
                SectorDailyRecord.ingestion_run_id == run.id,
                SectorDailyRecord.trade_date <= bound,
            )
            .order_by(SectorDailyRecord.sector_code, SectorDailyRecord.trade_date)
        ).mappings()
        daily = [dict(row) for row in daily_rows]
        if not definitions or not daily:
            raise SectorSnapshotNotFound(
                f"Sector snapshot {run.id} has no complete rows at or before permitted session {_compact_date(bound)}."
            )
        expected_codes = list(identity["sector_codes"])
        observed_definitions = sorted(str(row["sector_code"]) for row in definitions)
        observed_daily = sorted({str(row["sector_code"]) for row in daily})
        if observed_definitions != expected_codes or observed_daily != expected_codes:
            raise SectorSelectionError(
                "Persisted sector snapshot does not match its exact canonical code scope."
            )
        definition_sources = {str(row["source"]) for row in definitions}
        daily_sources = {str(row["source"]) for row in daily}
        if definition_sources != {run.provider} or daily_sources != {run.provider}:
            raise SectorSelectionError(
                "Persisted sector snapshot source does not match its canonical provider."
            )
        classification_systems = {
            str(row["classification_system"]) for row in definitions
        }
        classification_levels = {row["classification_level"] for row in definitions}
        if classification_systems != {identity["classification_system"]}:
            raise SectorSelectionError(
                "Persisted sector definitions do not match the canonical taxonomy."
            )
        if classification_levels != {identity["classification_level"]}:
            raise SectorSelectionError(
                "Persisted sector definitions do not match the canonical classification level."
            )
        if any(not str(row["sector_name"]).strip() for row in definitions):
            raise SectorSelectionError("Persisted sector definitions contain a blank display name.")
        for row in daily:
            row["trade_date"] = _compact_date(row["trade_date"])
        metadata = dict(run.provider_request_metadata or {})
        return PersistedSectorSnapshot(
            series_key=run.series_key,
            ingestion_run_id=run.id,
            provider=run.provider,
            definition_contract_version=str(identity["sector_definition_contract_version"]),
            daily_contract_version=str(identity["sector_daily_contract_version"]),
            adapter_version=run.adapter_version,
            adapter_compatibility_version=str(identity["adapter_compatibility_version"]),
            information_cutoff_date=_compact_date(run.information_cutoff_date),
            requested_start_date=_compact_date(run.requested_start_date),
            requested_end_date=_compact_date(run.requested_end_date),
            sector_codes=expected_codes,
            taxonomy_endpoint=str(identity["taxonomy_endpoint"]),
            history_endpoint=str(identity["history_endpoint"]),
            classification_system=str(identity["classification_system"]),
            classification_level=identity["classification_level"],
            frequency=str(identity["frequency"]),
            adjust_type=str(identity["adjust_type"]),
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
            series_identity=identity,
            sector_definition=pd.DataFrame(definitions, columns=SECTOR_DEFINITION_COLUMNS),
            sector_daily=pd.DataFrame(daily, columns=SECTOR_DAILY_COLUMNS),
        )


def _resolve_selector(
    series_key: str | None,
    selector: SectorSeriesIdentity | None,
) -> tuple[str, dict[str, Any] | None]:
    if series_key is None and selector is None:
        raise SectorSelectionError(
            "Sector context requires an explicit sector series_key or complete canonical selector."
        )
    if series_key is not None and selector is not None:
        raise SectorSelectionError("Provide sector series_key or selector, not both.")
    if selector is not None:
        validated = validate_sector_series_identity(selector)
        return validated.series_key, validated.canonical
    return validate_series_key(series_key or ""), None


def _optional_date(value: str | None, field: str) -> date | None:
    if value is None:
        return None
    normalized = str(value).strip().replace("-", "")
    try:
        return datetime.strptime(normalized, "%Y%m%d").date()
    except ValueError as exc:
        raise SectorSelectionError(f"{field} must use YYYYMMDD format.") from exc


def _optional_recorded_at(value: datetime | str | None) -> datetime | None:
    if value is None:
        return None
    try:
        parsed = value if isinstance(value, datetime) else datetime.fromisoformat(
            str(value).strip().replace("Z", "+00:00")
        )
    except ValueError as exc:
        raise SectorSelectionError(
            "as_of_recorded_at_utc must use an ISO-8601 timestamp."
        ) from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise SectorSelectionError(
            "as_of_recorded_at_utc must include an explicit UTC offset."
        )
    return parsed.astimezone(timezone.utc)


def _compact_date(value: date | str | None) -> str:
    if value is None:
        return ""
    if isinstance(value, date):
        return value.strftime("%Y%m%d")
    return datetime.strptime(str(value).replace("-", ""), "%Y%m%d").strftime("%Y%m%d")


def _utc_iso(value: datetime | str) -> str:
    parsed = value if isinstance(value, datetime) else datetime.fromisoformat(
        str(value).replace("Z", "+00:00")
    )
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
