"""Validated, transactional persistence for normalized market-data contracts."""

from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Any, Iterable

import numpy as np
import pandas as pd
from sqlalchemy import Select, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from backend.database.models import DailyPriceRecord, IngestionRun, StockBasicRecord, TradeCalendarRecord
from datasource.base import DAILY_PRICE_COLUMNS, STOCK_BASIC_COLUMNS, TRADE_CALENDAR_COLUMNS, MarketDataBundle

CONTRACT_VERSION = "1.0"
MARKET_DATASET = "market_data_bundle"
SUCCEEDED = "succeeded"
FAILED = "failed"
PENDING = "pending"
STOCK_CODE_PATTERN = re.compile(r"^[0-9]{6}$")
ALLOWED_ADJUST_TYPES = {"", "qfq", "hfq"}
AUTHORIZED_DATASETS = {"stock_basic", "daily_price", "trade_calendar"}
SNAPSHOT_MODE = "complete"
STOCK_CODE_SCOPE_SEMANTICS = "exact"


class MarketDataValidationError(ValueError):
    """Raised before market-data rows are committed."""


@dataclass(frozen=True)
class IngestionResult:
    ingestion_run_id: int
    batch_identifier: str
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
            "status": self.status,
            "information_cutoff_date": self.information_cutoff_date,
            "rows_received": self.rows_received,
            "rows_written": self.rows_written,
            "dataset_counts": dict(self.dataset_counts),
            "idempotent": self.idempotent,
        }


@dataclass(frozen=True)
class _NormalizedBundle:
    stock_basic: list[dict[str, Any]]
    daily_price: list[dict[str, Any]]
    trade_calendar: list[dict[str, Any]]

    @property
    def counts(self) -> dict[str, int]:
        return {
            "stock_basic": len(self.stock_basic),
            "daily_price": len(self.daily_price),
            "trade_calendar": len(self.trade_calendar),
        }

    @property
    def total_rows(self) -> int:
        return sum(self.counts.values())


class MarketDataPersistenceService:
    """Coordinate validation, provenance, idempotency, and atomic writes."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def ingest_bundle(
        self,
        bundle: MarketDataBundle,
        *,
        provider: str,
        requested_start_date: str,
        requested_end_date: str,
        information_cutoff_date: str,
        requested_scope: dict[str, Any],
        contract_version: str = CONTRACT_VERSION,
    ) -> IngestionResult:
        provider = _required_text(provider, "provider")
        contract_version = _required_text(contract_version, "contract_version")
        start_date = _required_date(requested_start_date, "requested_start_date")
        end_date = _required_date(requested_end_date, "requested_end_date")
        cutoff_date = _required_date(information_cutoff_date, "information_cutoff_date")
        if start_date > end_date:
            raise MarketDataValidationError("requested_start_date must not be after requested_end_date.")
        if end_date > cutoff_date:
            raise MarketDataValidationError("requested_end_date must not exceed information_cutoff_date.")
        scope = _validate_scope(requested_scope)
        raw_batch_identifier = _raw_batch_identifier(
            bundle,
            provider=provider,
            requested_start_date=start_date,
            requested_end_date=end_date,
            information_cutoff_date=cutoff_date,
            requested_scope=scope,
            contract_version=contract_version,
            snapshot_mode=SNAPSHOT_MODE,
        )

        try:
            normalized = _normalize_bundle(
                bundle,
                provider=provider,
                requested_start_date=start_date,
                requested_end_date=end_date,
                information_cutoff_date=cutoff_date,
                requested_scope=scope,
            )
        except Exception as exc:
            counts = _raw_counts(bundle)
            run_id = self._create_pending_run(
                batch_identifier=raw_batch_identifier,
                provider=provider,
                start_date=start_date,
                end_date=end_date,
                cutoff_date=cutoff_date,
                requested_scope=scope,
                contract_version=contract_version,
                dataset_counts=counts,
            )
            self._mark_failed(run_id, exc)
            raise

        batch_identifier = _normalized_batch_identifier(
            normalized,
            provider=provider,
            requested_start_date=start_date,
            requested_end_date=end_date,
            information_cutoff_date=cutoff_date,
            requested_scope=scope,
            contract_version=contract_version,
            snapshot_mode=SNAPSHOT_MODE,
        )
        existing = self._find_successful_run(batch_identifier)
        if existing is not None:
            return _result_from_run(existing, idempotent=True, rows_written=0)

        run_id = self._create_pending_run(
            batch_identifier=batch_identifier,
            provider=provider,
            start_date=start_date,
            end_date=end_date,
            cutoff_date=cutoff_date,
            requested_scope=scope,
            contract_version=contract_version,
            dataset_counts=normalized.counts,
        )
        try:
            with self._session_factory.begin() as session:
                run = session.get(IngestionRun, run_id, with_for_update=True)
                if run is None:
                    raise RuntimeError(f"Ingestion run {run_id} disappeared before persistence.")
                _insert_bundle(session, normalized, run_id)
                run.status = SUCCEEDED
                run.row_count_written = normalized.total_rows
                run.error_summary = None
                run.completed_at = datetime.now(timezone.utc)
        except IntegrityError as exc:
            concurrent_success = self._find_successful_run(batch_identifier)
            if concurrent_success is not None:
                self._mark_failed(
                    run_id,
                    RuntimeError(
                        f"Concurrent identical batch completed as ingestion run {concurrent_success.id}."
                    ),
                )
                return _result_from_run(concurrent_success, idempotent=True, rows_written=0)
            self._mark_failed(run_id, exc)
            raise
        except Exception as exc:
            self._mark_failed(run_id, exc)
            raise

        with self._session_factory() as session:
            completed = session.get(IngestionRun, run_id)
            if completed is None:
                raise RuntimeError(f"Ingestion run {run_id} was not available after commit.")
            return _result_from_run(completed, idempotent=False, rows_written=normalized.total_rows)

    def _find_successful_run(self, batch_identifier: str) -> IngestionRun | None:
        with self._session_factory() as session:
            return session.scalar(
                select(IngestionRun).where(
                    IngestionRun.batch_identifier == batch_identifier,
                    IngestionRun.status == SUCCEEDED,
                )
            )

    def _create_pending_run(
        self,
        *,
        batch_identifier: str,
        provider: str,
        start_date: date,
        end_date: date,
        cutoff_date: date,
        requested_scope: dict[str, Any],
        contract_version: str,
        dataset_counts: dict[str, int],
    ) -> int:
        with self._session_factory.begin() as session:
            run = IngestionRun(
                batch_identifier=batch_identifier,
                provider=provider,
                dataset=MARKET_DATASET,
                requested_start_date=start_date,
                requested_end_date=end_date,
                information_cutoff_date=cutoff_date,
                requested_scope=requested_scope,
                snapshot_mode=SNAPSHOT_MODE,
                contract_version=contract_version,
                status=PENDING,
                row_count_received=sum(dataset_counts.values()),
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
                raise RuntimeError(f"Could not record failure for ingestion run {run_id}.") from exc
            run.status = FAILED
            run.row_count_written = 0
            run.error_summary = _error_summary(exc)
            run.completed_at = datetime.now(timezone.utc)


class MarketDataRepository:
    """Deterministically reconstruct existing normalized DataFrame contracts."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def read_stock_basic(self, provider: str, *, as_of_cutoff: str | None = None) -> pd.DataFrame:
        provider = _required_text(provider, "provider")
        statement = _latest_stock_basic_statement(provider, _optional_date(as_of_cutoff))
        records = [dict(row) for row in self._session.execute(statement).mappings()]
        for record in records:
            record["listing_date"] = _compact_optional_date(record["listing_date"])
        return pd.DataFrame(records, columns=STOCK_BASIC_COLUMNS)

    def read_daily_price(
        self,
        provider: str,
        *,
        start_date: str | None = None,
        end_date: str | None = None,
        as_of_cutoff: str | None = None,
    ) -> pd.DataFrame:
        provider = _required_text(provider, "provider")
        statement = _latest_daily_price_statement(
            provider,
            start_date=_optional_date(start_date),
            end_date=_optional_date(end_date),
            as_of_cutoff=_optional_date(as_of_cutoff),
        )
        records = [dict(row) for row in self._session.execute(statement).mappings()]
        for record in records:
            record["trade_date"] = _compact_date(record["trade_date"])
        return pd.DataFrame(records, columns=DAILY_PRICE_COLUMNS)

    def read_trade_calendar(
        self,
        provider: str,
        *,
        start_date: str | None = None,
        end_date: str | None = None,
        as_of_cutoff: str | None = None,
    ) -> pd.DataFrame:
        provider = _required_text(provider, "provider")
        statement = _latest_trade_calendar_statement(
            provider,
            start_date=_optional_date(start_date),
            end_date=_optional_date(end_date),
            as_of_cutoff=_optional_date(as_of_cutoff),
        )
        records = [dict(row) for row in self._session.execute(statement).mappings()]
        for record in records:
            record["trade_date"] = _compact_date(record["trade_date"])
        return pd.DataFrame(records, columns=TRADE_CALENDAR_COLUMNS)

    def stock_basic_versions(self, provider: str, stock_code: str) -> list[dict[str, Any]]:
        rows = self._session.execute(
            select(
                StockBasicRecord.stock_code,
                StockBasicRecord.stock_name,
                StockBasicRecord.source,
                StockBasicRecord.ingestion_run_id,
                IngestionRun.batch_identifier,
                IngestionRun.information_cutoff_date,
            )
            .join(IngestionRun, IngestionRun.id == StockBasicRecord.ingestion_run_id)
            .where(
                StockBasicRecord.source == _required_text(provider, "provider"),
                StockBasicRecord.stock_code == _stock_code(stock_code, "stock_code"),
                IngestionRun.status == SUCCEEDED,
            )
            .order_by(
                IngestionRun.information_cutoff_date,
                IngestionRun.completed_at,
                IngestionRun.id,
            )
        ).mappings()
        return [dict(row) for row in rows]


def _normalize_bundle(
    bundle: MarketDataBundle,
    *,
    provider: str,
    requested_start_date: date,
    requested_end_date: date,
    information_cutoff_date: date,
    requested_scope: dict[str, Any],
) -> _NormalizedBundle:
    stock_basic = _normalize_stock_basic(bundle.stock_basic, provider, information_cutoff_date)
    daily_price = _normalize_daily_price(
        bundle.daily_price,
        provider,
        requested_start_date,
        requested_end_date,
        information_cutoff_date,
    )
    trade_calendar = _normalize_trade_calendar(
        bundle.trade_calendar,
        provider,
        requested_start_date,
        requested_end_date,
        information_cutoff_date,
    )
    stock_basic_codes = {row["stock_code"] for row in stock_basic}
    daily_price_codes = {row["stock_code"] for row in daily_price}
    missing_stock_basic = {row["stock_code"] for row in daily_price} - stock_basic_codes
    if missing_stock_basic:
        raise MarketDataValidationError(
            f"daily_price contains stock codes missing from stock_basic: {sorted(missing_stock_basic)}"
        )
    declared_codes = set(requested_scope["stock_codes"])
    if stock_basic_codes != declared_codes:
        raise MarketDataValidationError(
            "stock_basic stock codes must exactly match requested_scope.stock_codes; "
            f"missing={sorted(declared_codes - stock_basic_codes)}, "
            f"unexpected={sorted(stock_basic_codes - declared_codes)}."
        )
    if daily_price_codes != declared_codes:
        raise MarketDataValidationError(
            "daily_price stock codes must exactly match requested_scope.stock_codes; "
            f"missing={sorted(declared_codes - daily_price_codes)}, "
            f"unexpected={sorted(daily_price_codes - declared_codes)}."
        )
    calendar = {row["trade_date"]: row["is_open"] for row in trade_calendar}
    price_dates = {row["trade_date"] for row in daily_price}
    missing_calendar_dates = sorted(price_dates - set(calendar))
    if missing_calendar_dates:
        raise MarketDataValidationError(
            "daily_price dates are missing from trade_calendar: "
            f"{[_compact_date(value) for value in missing_calendar_dates]}."
        )
    closed_price_dates = sorted(value for value in price_dates if not calendar[value])
    if closed_price_dates:
        raise MarketDataValidationError(
            "daily_price dates must be open in trade_calendar: "
            f"{[_compact_date(value) for value in closed_price_dates]}."
        )
    return _NormalizedBundle(stock_basic=stock_basic, daily_price=daily_price, trade_calendar=trade_calendar)


def _normalize_stock_basic(frame: pd.DataFrame, provider: str, cutoff_date: date) -> list[dict[str, Any]]:
    normalized = _contract_frame(frame, STOCK_BASIC_COLUMNS, "stock_basic")
    normalized["stock_code"] = _string_series(normalized["stock_code"], "stock_basic.stock_code")
    normalized["stock_name"] = _string_series(normalized["stock_name"], "stock_basic.stock_name")
    normalized["status"] = _string_series(normalized["status"], "stock_basic.status")
    normalized["source"] = _source_series(normalized["source"], provider, "stock_basic.source")
    normalized["exchange"] = normalized["exchange"].fillna("").map(lambda value: str(value).strip())
    normalized["industry"] = normalized["industry"].fillna("").map(lambda value: str(value).strip())
    normalized["listing_date"] = normalized["listing_date"].map(
        lambda value: _nullable_date(value, "stock_basic.listing_date")
    )
    for stock_code in normalized["stock_code"]:
        _stock_code(stock_code, "stock_basic.stock_code")
    if any(value is not None and value > cutoff_date for value in normalized["listing_date"]):
        raise MarketDataValidationError("stock_basic.listing_date exceeds information_cutoff_date.")
    _reject_duplicates(normalized, ["source", "stock_code"], "stock_basic")
    normalized = normalized.sort_values(["source", "stock_code"], kind="stable")
    return normalized.to_dict(orient="records")


def _normalize_daily_price(
    frame: pd.DataFrame,
    provider: str,
    start_date: date,
    end_date: date,
    cutoff_date: date,
) -> list[dict[str, Any]]:
    normalized = _contract_frame(frame, DAILY_PRICE_COLUMNS, "daily_price")
    normalized["trade_date"] = normalized["trade_date"].map(lambda value: _required_date(value, "daily_price.trade_date"))
    normalized["stock_code"] = _string_series(normalized["stock_code"], "daily_price.stock_code")
    normalized["adjust_type"] = normalized["adjust_type"].fillna("").map(lambda value: str(value).strip())
    normalized["source"] = _source_series(normalized["source"], provider, "daily_price.source")
    for stock_code in normalized["stock_code"]:
        _stock_code(stock_code, "daily_price.stock_code")
    invalid_adjustments = sorted(set(normalized["adjust_type"]) - ALLOWED_ADJUST_TYPES)
    if invalid_adjustments:
        raise MarketDataValidationError(f"daily_price.adjust_type contains unsupported values: {invalid_adjustments}")
    for column in ("open", "high", "low", "close", "volume", "amount"):
        normalized[column] = _finite_numeric_series(normalized[column], f"daily_price.{column}")
    if (normalized[["open", "high", "low", "close", "volume", "amount"]] < 0).any(axis=None):
        raise MarketDataValidationError("daily_price numeric values must be non-negative.")
    if (
        (normalized["high"] < normalized[["open", "low", "close"]].max(axis=1)).any()
        or (normalized["low"] > normalized[["open", "high", "close"]].min(axis=1)).any()
    ):
        raise MarketDataValidationError("daily_price OHLC values are inconsistent.")
    _validate_dates_in_scope(normalized["trade_date"], start_date, end_date, cutoff_date, "daily_price.trade_date")
    _reject_duplicates(normalized, ["source", "stock_code", "trade_date", "adjust_type"], "daily_price")
    normalized = normalized.sort_values(["trade_date", "stock_code", "adjust_type", "source"], kind="stable")
    return normalized.to_dict(orient="records")


def _normalize_trade_calendar(
    frame: pd.DataFrame,
    provider: str,
    start_date: date,
    end_date: date,
    cutoff_date: date,
) -> list[dict[str, Any]]:
    normalized = _contract_frame(frame, TRADE_CALENDAR_COLUMNS, "trade_calendar")
    normalized["trade_date"] = normalized["trade_date"].map(
        lambda value: _required_date(value, "trade_calendar.trade_date")
    )
    normalized["source"] = _source_series(normalized["source"], provider, "trade_calendar.source")
    if not normalized["is_open"].map(lambda value: isinstance(value, (bool, np.bool_))).all():
        raise MarketDataValidationError("trade_calendar.is_open must contain booleans.")
    normalized["is_open"] = normalized["is_open"].map(bool)
    _validate_dates_in_scope(
        normalized["trade_date"], start_date, end_date, cutoff_date, "trade_calendar.trade_date"
    )
    _reject_duplicates(normalized, ["source", "trade_date"], "trade_calendar")
    normalized = normalized.sort_values(["trade_date", "source"], kind="stable")
    return normalized.to_dict(orient="records")


def _insert_bundle(session: Session, bundle: _NormalizedBundle, run_id: int) -> None:
    session.add_all(StockBasicRecord(ingestion_run_id=run_id, **row) for row in bundle.stock_basic)
    session.add_all(DailyPriceRecord(ingestion_run_id=run_id, **row) for row in bundle.daily_price)
    session.add_all(TradeCalendarRecord(ingestion_run_id=run_id, **row) for row in bundle.trade_calendar)
    session.flush()


def _latest_stock_basic_statement(provider: str, cutoff: date | None) -> Select[Any]:
    run_id = _latest_successful_run_id(provider, cutoff)
    return (
        select(*(getattr(StockBasicRecord, column) for column in STOCK_BASIC_COLUMNS))
        .where(StockBasicRecord.ingestion_run_id == run_id)
        .order_by(StockBasicRecord.stock_code, StockBasicRecord.source)
    )


def _latest_daily_price_statement(
    provider: str,
    *,
    start_date: date | None,
    end_date: date | None,
    as_of_cutoff: date | None,
) -> Select[Any]:
    statement = select(*(getattr(DailyPriceRecord, column) for column in DAILY_PRICE_COLUMNS)).where(
        DailyPriceRecord.ingestion_run_id == _latest_successful_run_id(provider, as_of_cutoff)
    )
    statement = _apply_date_filters(statement, DailyPriceRecord.trade_date, start_date, end_date)
    return statement.order_by(
        DailyPriceRecord.trade_date,
        DailyPriceRecord.stock_code,
        DailyPriceRecord.adjust_type,
        DailyPriceRecord.source,
    )


def _latest_trade_calendar_statement(
    provider: str,
    *,
    start_date: date | None,
    end_date: date | None,
    as_of_cutoff: date | None,
) -> Select[Any]:
    statement = select(*(getattr(TradeCalendarRecord, column) for column in TRADE_CALENDAR_COLUMNS)).where(
        TradeCalendarRecord.ingestion_run_id == _latest_successful_run_id(provider, as_of_cutoff)
    )
    statement = _apply_date_filters(statement, TradeCalendarRecord.trade_date, start_date, end_date)
    return statement.order_by(TradeCalendarRecord.trade_date, TradeCalendarRecord.source)


def _latest_successful_run_id(provider: str, cutoff: date | None) -> Any:
    statement = select(IngestionRun.id).where(
        IngestionRun.provider == provider,
        IngestionRun.dataset == MARKET_DATASET,
        IngestionRun.status == SUCCEEDED,
        IngestionRun.snapshot_mode == SNAPSHOT_MODE,
    )
    if cutoff is not None:
        statement = statement.where(IngestionRun.information_cutoff_date <= cutoff)
    return (
        statement.order_by(
            IngestionRun.information_cutoff_date.desc(),
            IngestionRun.completed_at.desc(),
            IngestionRun.id.desc(),
        )
        .limit(1)
        .scalar_subquery()
    )


def _apply_date_filters(statement: Select[Any], column: Any, start_date: date | None, end_date: date | None) -> Select[Any]:
    if start_date is not None:
        statement = statement.where(column >= start_date)
    if end_date is not None:
        statement = statement.where(column <= end_date)
    return statement


def _contract_frame(frame: pd.DataFrame, expected_columns: list[str], dataset: str) -> pd.DataFrame:
    if not isinstance(frame, pd.DataFrame):
        raise MarketDataValidationError(f"{dataset} must be a pandas DataFrame.")
    missing = sorted(set(expected_columns) - set(frame.columns))
    extra = sorted(set(frame.columns) - set(expected_columns))
    if missing or extra:
        raise MarketDataValidationError(f"{dataset} contract mismatch; missing={missing}, extra={extra}.")
    return frame.loc[:, expected_columns].copy()


def _string_series(series: pd.Series, field: str) -> pd.Series:
    if series.isna().any():
        raise MarketDataValidationError(f"{field} contains missing values.")
    normalized = series.map(lambda value: str(value).strip())
    if normalized.eq("").any():
        raise MarketDataValidationError(f"{field} contains blank values.")
    return normalized


def _source_series(series: pd.Series, provider: str, field: str) -> pd.Series:
    normalized = _string_series(series, field)
    if not normalized.eq(provider).all():
        raise MarketDataValidationError(f"{field} must match declared provider {provider!r}.")
    return normalized


def _finite_numeric_series(series: pd.Series, field: str) -> pd.Series:
    if series.isna().any():
        raise MarketDataValidationError(f"{field} contains missing values.")
    try:
        normalized = pd.to_numeric(series, errors="raise").astype(float)
    except (TypeError, ValueError) as exc:
        raise MarketDataValidationError(f"{field} contains non-numeric values.") from exc
    if not np.isfinite(normalized.to_numpy()).all():
        raise MarketDataValidationError(f"{field} contains non-finite values.")
    return normalized


def _validate_dates_in_scope(
    dates: Iterable[date], start_date: date, end_date: date, cutoff_date: date, field: str
) -> None:
    for value in dates:
        if value < start_date or value > end_date:
            raise MarketDataValidationError(f"{field} falls outside the requested date range.")
        if value > cutoff_date:
            raise MarketDataValidationError(f"{field} exceeds information_cutoff_date.")


def _reject_duplicates(frame: pd.DataFrame, key_columns: list[str], dataset: str) -> None:
    if frame.duplicated(key_columns, keep=False).any():
        raise MarketDataValidationError(f"{dataset} contains duplicate natural keys {key_columns}.")


def _validate_scope(scope: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(scope, dict):
        raise MarketDataValidationError("requested_scope must be a dictionary.")
    datasets = scope.get("datasets")
    stock_codes = scope.get("stock_codes")
    if not isinstance(datasets, list) or set(datasets) != AUTHORIZED_DATASETS:
        raise MarketDataValidationError(f"requested_scope.datasets must contain {sorted(AUTHORIZED_DATASETS)}.")
    if not isinstance(stock_codes, list) or not stock_codes:
        raise MarketDataValidationError("requested_scope.stock_codes must be a non-empty list.")
    if scope.get("stock_code_semantics", STOCK_CODE_SCOPE_SEMANTICS) != STOCK_CODE_SCOPE_SEMANTICS:
        raise MarketDataValidationError("requested_scope.stock_code_semantics must be 'exact'.")
    if scope.get("snapshot_mode", SNAPSHOT_MODE) != SNAPSHOT_MODE:
        raise MarketDataValidationError("requested_scope.snapshot_mode must be 'complete'.")
    normalized_codes = sorted({_stock_code(value, "requested_scope.stock_codes") for value in stock_codes})
    if len(normalized_codes) != len(stock_codes):
        raise MarketDataValidationError("requested_scope.stock_codes contains duplicates.")
    return {
        "datasets": sorted(AUTHORIZED_DATASETS),
        "stock_codes": normalized_codes,
        "stock_code_semantics": STOCK_CODE_SCOPE_SEMANTICS,
        "snapshot_mode": SNAPSHOT_MODE,
    }


def _required_text(value: Any, field: str) -> str:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        raise MarketDataValidationError(f"{field} is required.")
    normalized = str(value).strip()
    if not normalized:
        raise MarketDataValidationError(f"{field} must not be blank.")
    return normalized


def _stock_code(value: Any, field: str) -> str:
    normalized = _required_text(value, field)
    if not STOCK_CODE_PATTERN.fullmatch(normalized):
        raise MarketDataValidationError(f"{field} must be a six-digit stock code.")
    return normalized


def _required_date(value: Any, field: str) -> date:
    if value is None or pd.isna(value):
        raise MarketDataValidationError(f"{field} is required.")
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    normalized = str(value).strip()
    try:
        return datetime.strptime(normalized, "%Y%m%d").date()
    except ValueError as exc:
        raise MarketDataValidationError(f"{field} must use YYYYMMDD format.") from exc


def _nullable_date(value: Any, field: str) -> date | None:
    if value is None or pd.isna(value) or str(value).strip() == "":
        return None
    return _required_date(value, field)


def _optional_date(value: str | None) -> date | None:
    return None if value is None else _required_date(value, "date filter")


def _compact_date(value: date) -> str:
    return value.strftime("%Y%m%d")


def _compact_optional_date(value: date | None) -> str | None:
    return None if value is None else _compact_date(value)


def _raw_counts(bundle: MarketDataBundle) -> dict[str, int]:
    return {
        "stock_basic": len(bundle.stock_basic) if isinstance(bundle.stock_basic, pd.DataFrame) else 0,
        "daily_price": len(bundle.daily_price) if isinstance(bundle.daily_price, pd.DataFrame) else 0,
        "trade_calendar": len(bundle.trade_calendar) if isinstance(bundle.trade_calendar, pd.DataFrame) else 0,
    }


def _raw_batch_identifier(bundle: MarketDataBundle, **metadata: Any) -> str:
    payload = dict(metadata)
    payload["frames"] = {
        "stock_basic": _raw_frame_payload(bundle.stock_basic),
        "daily_price": _raw_frame_payload(bundle.daily_price),
        "trade_calendar": _raw_frame_payload(bundle.trade_calendar),
    }
    return _hash_payload(payload)


def _normalized_batch_identifier(bundle: _NormalizedBundle, **metadata: Any) -> str:
    payload = dict(metadata)
    payload["frames"] = {
        "stock_basic": _json_records(bundle.stock_basic),
        "daily_price": _json_records(bundle.daily_price),
        "trade_calendar": _json_records(bundle.trade_calendar),
    }
    return _hash_payload(payload)


def _raw_frame_payload(frame: Any) -> Any:
    if not isinstance(frame, pd.DataFrame):
        return {"type": type(frame).__name__}
    return json.loads(frame.to_json(orient="split", date_format="iso", double_precision=15))


def _json_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [{key: _json_value(value) for key, value in record.items()} for record in records]


def _json_value(value: Any) -> Any:
    if isinstance(value, date):
        return _compact_date(value)
    if isinstance(value, np.generic):
        return value.item()
    return value


def _hash_payload(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=_json_value)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _error_summary(exc: Exception) -> str:
    first_line = str(exc).splitlines()[0].strip()
    return f"{type(exc).__name__}: {first_line}"[:500]


def _result_from_run(run: IngestionRun, *, idempotent: bool, rows_written: int) -> IngestionResult:
    return IngestionResult(
        ingestion_run_id=run.id,
        batch_identifier=run.batch_identifier,
        status=run.status,
        information_cutoff_date=_compact_date(run.information_cutoff_date),
        rows_received=run.row_count_received,
        rows_written=rows_written,
        dataset_counts=dict(run.dataset_counts),
        idempotent=idempotent,
    )
