"""Single-run SQLAlchemy adapter for Market Cockpit source data."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.database.models import (
    DailyPriceRecord,
    IngestionRun,
    StockBasicRecord,
    TradeCalendarRecord,
)
from backend.database.series import (
    SnapshotSeriesIdentity,
    validate_series_key,
    validate_snapshot_series_identity,
)
from datasource.base import DAILY_PRICE_COLUMNS, STOCK_BASIC_COLUMNS, TRADE_CALENDAR_COLUMNS

MARKET_DATASET = "market_data_bundle"


class MarketCockpitSelectionError(ValueError):
    """Raised when a caller does not supply one complete series selector."""


class MarketCockpitSnapshotNotFound(LookupError):
    """Raised when no successful complete snapshot satisfies the selector."""


@dataclass(frozen=True)
class PersistedMarketDataSnapshot:
    series_key: str
    ingestion_run_id: int
    provider: str
    contract_version: str
    adapter_version: str
    information_cutoff_date: str
    requested_start_date: str
    requested_end_date: str
    adjust_type: str
    stock_codes: list[str]
    series_identity: dict
    stock_basic: pd.DataFrame
    daily_price: pd.DataFrame
    trade_calendar: pd.DataFrame


class MarketCockpitRepository:
    """Select one compatible complete snapshot and read only its physical rows."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def load_snapshot(
        self,
        *,
        series_key: str | None = None,
        selector: SnapshotSeriesIdentity | None = None,
        as_of_cutoff: str | None = None,
    ) -> PersistedMarketDataSnapshot:
        resolved_key, canonical = _resolve_selector(series_key, selector)
        cutoff = _optional_date(as_of_cutoff)
        statement = select(IngestionRun).where(
            IngestionRun.series_key == resolved_key,
            IngestionRun.dataset == MARKET_DATASET,
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
            suffix = f" at or before cutoff {_compact_date(cutoff)}" if cutoff is not None else ""
            raise MarketCockpitSnapshotNotFound(
                f"No successful complete snapshot exists for series {resolved_key}{suffix}."
            )

        stored = validate_snapshot_series_identity(
            SnapshotSeriesIdentity(run.series_key, dict(run.series_identity))
        )
        if canonical is not None and stored.canonical != canonical:
            raise MarketCockpitSelectionError(
                "The canonical selector does not match the selected persisted series identity."
            )

        stock_basic = _stock_basic_frame(self._session, run.id)
        daily_price = _daily_price_frame(self._session, run.id)
        trade_calendar = _trade_calendar_frame(self._session, run.id)
        identity = stored.canonical
        return PersistedMarketDataSnapshot(
            series_key=run.series_key,
            ingestion_run_id=run.id,
            provider=run.provider,
            contract_version=run.contract_version,
            adapter_version=run.adapter_version,
            information_cutoff_date=_compact_date(run.information_cutoff_date),
            requested_start_date=_compact_date(run.requested_start_date),
            requested_end_date=_compact_date(run.requested_end_date),
            adjust_type=str(identity["adjust_type"]),
            stock_codes=list(identity["stock_codes"]),
            series_identity=identity,
            stock_basic=stock_basic,
            daily_price=daily_price,
            trade_calendar=trade_calendar,
        )


def _resolve_selector(
    series_key: str | None,
    selector: SnapshotSeriesIdentity | None,
) -> tuple[str, dict | None]:
    if series_key is None and selector is None:
        raise MarketCockpitSelectionError(
            "Market Cockpit requires an explicit series_key or complete canonical selector; "
            "provider-only selection is not allowed."
        )
    if series_key is not None and selector is not None:
        raise MarketCockpitSelectionError("Provide series_key or canonical selector, not both.")
    if selector is not None:
        validated = validate_snapshot_series_identity(selector)
        return validated.series_key, validated.canonical
    return validate_series_key(series_key or ""), None


def _stock_basic_frame(session: Session, run_id: int) -> pd.DataFrame:
    rows = session.execute(
        select(*(getattr(StockBasicRecord, column) for column in STOCK_BASIC_COLUMNS))
        .where(StockBasicRecord.ingestion_run_id == run_id)
        .order_by(StockBasicRecord.stock_code)
    ).mappings()
    records = [dict(row) for row in rows]
    for record in records:
        record["listing_date"] = _compact_optional_date(record["listing_date"])
    return pd.DataFrame(records, columns=STOCK_BASIC_COLUMNS)


def _daily_price_frame(session: Session, run_id: int) -> pd.DataFrame:
    rows = session.execute(
        select(*(getattr(DailyPriceRecord, column) for column in DAILY_PRICE_COLUMNS))
        .where(DailyPriceRecord.ingestion_run_id == run_id)
        .order_by(DailyPriceRecord.trade_date, DailyPriceRecord.stock_code)
    ).mappings()
    records = [dict(row) for row in rows]
    for record in records:
        record["trade_date"] = _compact_date(record["trade_date"])
    return pd.DataFrame(records, columns=DAILY_PRICE_COLUMNS)


def _trade_calendar_frame(session: Session, run_id: int) -> pd.DataFrame:
    rows = session.execute(
        select(*(getattr(TradeCalendarRecord, column) for column in TRADE_CALENDAR_COLUMNS))
        .where(TradeCalendarRecord.ingestion_run_id == run_id)
        .order_by(TradeCalendarRecord.trade_date)
    ).mappings()
    records = [dict(row) for row in rows]
    for record in records:
        record["trade_date"] = _compact_date(record["trade_date"])
    return pd.DataFrame(records, columns=TRADE_CALENDAR_COLUMNS)


def _optional_date(value: str | None) -> date | None:
    if value is None:
        return None
    normalized = str(value).strip().replace("-", "")
    try:
        return datetime.strptime(normalized, "%Y%m%d").date()
    except ValueError as exc:
        raise MarketCockpitSelectionError("as_of_cutoff must use YYYYMMDD format.") from exc


def _compact_date(value: date | None) -> str:
    if value is None:
        return ""
    return value.strftime("%Y%m%d")


def _compact_optional_date(value: date | None) -> str | None:
    return _compact_date(value) if value is not None else None
