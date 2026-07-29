"""Immutable persistence integration for validated THS daily-market foundations.

M5 reuses the existing market-data and benchmark owners. It performs complete cross-component
preflight validation before opening either persistence path. The two accepted owners retain
their own transactions and immutable runs; a complete acquisition receipt is emitted only when
both component writes succeed. A component that succeeds before a later database failure remains
valid local history but is never promoted as a complete acquisition.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import Enum
import re
from types import MappingProxyType
from typing import Mapping, TypeAlias

import pandas as pd

from backend.database.benchmark_data import (
    BENCHMARK_CONTRACT_VERSION,
    BenchmarkIngestionResult,
    BenchmarkPersistenceService,
    validate_benchmark_bundle,
)
from backend.database.market_data import (
    CONTRACT_VERSION as MARKET_CONTRACT_VERSION,
    IngestionResult,
    MarketDataPersistenceService,
    validate_market_data_bundle,
)
from datasource.base import (
    BENCHMARK_INDEX_DAILY_COLUMNS,
    DAILY_PRICE_COLUMNS,
    STOCK_BASIC_COLUMNS,
    TRADE_CALENDAR_COLUMNS,
    BenchmarkIndexBundle,
    MarketDataBundle,
)

from .contracts import SOURCE_KEY
from .fingerprint import canonical_sha256
from .live_contracts import DEFAULT_LIVE_SOURCE_POLICY, DailyMarketCapability
from .live_planner import DailyMarketRequestPlan
from .live_schemas import ValidatedLiveResponse
from .live_selectors import (
    AShareDailySelector,
    BenchmarkDailySelector,
    ListedInstrumentSelector,
    LiveDailyMarketSelector,
    TradingCalendarSelector,
)

ACQUISITION_CONTRACT_VERSION = "aquantai.ths-daily-market-acquisition.v1"
ACQUISITION_ADAPTER_VERSION = "aquantai.ths-daily-market-acquisition-adapter.v1"
MARKET_DATA_COMPONENT_KEY = "market_data_bundle"
BENCHMARK_INDEX_DAILY_COMPONENT_KEY = "benchmark_index_daily"
_INDEX_OWNER_CODE = re.compile(r"^[0-9]{6}$")


class AcquisitionFailureCode(str, Enum):
    COMPONENT_TYPE_MISMATCH = "THS_ACQUISITION_COMPONENT_TYPE_MISMATCH"
    COMPONENT_BINDING_MISMATCH = "THS_ACQUISITION_COMPONENT_BINDING_MISMATCH"
    COVERAGE_MISMATCH = "THS_ACQUISITION_COVERAGE_MISMATCH"
    CLOSED_SESSION = "THS_ACQUISITION_CLOSED_SESSION"
    UNSUPPORTED_ADJUSTMENT = "THS_ACQUISITION_UNSUPPORTED_ADJUSTMENT"
    OWNER_IDENTITY_UNSUPPORTED = "THS_ACQUISITION_OWNER_IDENTITY_UNSUPPORTED"
    OWNER_PREVALIDATION_FAILED = "THS_ACQUISITION_OWNER_PREVALIDATION_FAILED"
    MARKET_PERSISTENCE_FAILED = "THS_ACQUISITION_MARKET_PERSISTENCE_FAILED"
    BENCHMARK_PERSISTENCE_FAILED = "THS_ACQUISITION_BENCHMARK_PERSISTENCE_FAILED"


@dataclass(frozen=True, slots=True)
class PersistedComponentReceipt:
    component_key: str
    owner: str
    ingestion_run_id: int
    batch_identifier: str
    series_key: str
    information_cutoff_date: str
    rows_received: int
    rows_written: int
    idempotent: bool

    def stable_identity_payload(self) -> dict[str, object]:
        return {
            "component_key": self.component_key,
            "owner": self.owner,
            "ingestion_run_id": self.ingestion_run_id,
            "batch_identifier": self.batch_identifier,
            "series_key": self.series_key,
            "information_cutoff_date": self.information_cutoff_date,
            "rows_received": self.rows_received,
        }

    def public_payload(self) -> dict[str, object]:
        return {
            **self.stable_identity_payload(),
            "rows_written": self.rows_written,
            "idempotent": self.idempotent,
        }


class DailyMarketAcquisitionError(RuntimeError):
    def __init__(
        self,
        message: str,
        reason_code: AcquisitionFailureCode,
        *,
        persisted_market: PersistedComponentReceipt | None = None,
    ) -> None:
        self.reason_code = reason_code
        self.persisted_market = persisted_market
        super().__init__(message)


@dataclass(frozen=True, slots=True)
class ValidatedAcquisitionComponent:
    selector: LiveDailyMarketSelector
    plan: DailyMarketRequestPlan
    response: ValidatedLiveResponse

    def __post_init__(self) -> None:
        if not isinstance(self.plan, DailyMarketRequestPlan):
            raise DailyMarketAcquisitionError(
                "component plan must be a DailyMarketRequestPlan",
                AcquisitionFailureCode.COMPONENT_TYPE_MISMATCH,
            )
        if not isinstance(self.response, ValidatedLiveResponse):
            raise DailyMarketAcquisitionError(
                "component response must be a ValidatedLiveResponse",
                AcquisitionFailureCode.COMPONENT_TYPE_MISMATCH,
            )
        if self.plan.selector_fingerprint != self.selector.selector_fingerprint:
            raise DailyMarketAcquisitionError(
                "component plan is not bound to the exact selector",
                AcquisitionFailureCode.COMPONENT_BINDING_MISMATCH,
            )
        if self.plan.capability is not self.selector.capability:
            raise DailyMarketAcquisitionError(
                "component plan capability does not match the selector",
                AcquisitionFailureCode.COMPONENT_BINDING_MISMATCH,
            )
        if self.response.capability is not self.selector.capability:
            raise DailyMarketAcquisitionError(
                "component response capability does not match the selector",
                AcquisitionFailureCode.COMPONENT_BINDING_MISMATCH,
            )
        if self.plan.source_key != SOURCE_KEY or self.response.source_key != SOURCE_KEY:
            raise DailyMarketAcquisitionError(
                "component source does not match the selected source authority",
                AcquisitionFailureCode.COMPONENT_BINDING_MISMATCH,
            )
        if self.plan.source_policy_fingerprint != DEFAULT_LIVE_SOURCE_POLICY.policy_fingerprint:
            raise DailyMarketAcquisitionError(
                "component plan does not use the reviewed source policy",
                AcquisitionFailureCode.COMPONENT_BINDING_MISMATCH,
            )
        if self.plan.remote_executable:
            raise DailyMarketAcquisitionError(
                "persistence accepts reviewed logical plans, not mutable executable plan state",
                AcquisitionFailureCode.COMPONENT_BINDING_MISMATCH,
            )

    def fingerprint_payload(self) -> dict[str, object]:
        return {
            "capability": self.selector.capability.value,
            "selector_fingerprint": self.selector.selector_fingerprint,
            "plan_fingerprint": self.plan.plan_fingerprint,
            "request_fingerprint": self.plan.request_fingerprint,
            "response_fingerprint": self.response.content_fingerprint,
            "covered_sessions": self.response.covered_sessions,
        }


@dataclass(frozen=True, slots=True)
class DailyMarketFoundationInput:
    listed_instruments: ValidatedAcquisitionComponent
    trading_calendar: ValidatedAcquisitionComponent
    a_share_daily_raw: ValidatedAcquisitionComponent
    benchmark_daily: ValidatedAcquisitionComponent
    information_cutoff_date: date

    def __post_init__(self) -> None:
        if not isinstance(self.information_cutoff_date, date):
            raise DailyMarketAcquisitionError(
                "information_cutoff_date must be a date",
                AcquisitionFailureCode.COMPONENT_TYPE_MISMATCH,
            )

    @property
    def components(self) -> tuple[ValidatedAcquisitionComponent, ...]:
        return (
            self.listed_instruments,
            self.trading_calendar,
            self.a_share_daily_raw,
            self.benchmark_daily,
        )

    @property
    def acquisition_fingerprint(self) -> str:
        return canonical_sha256(
            {
                "acquisition_contract_version": ACQUISITION_CONTRACT_VERSION,
                "source_key": SOURCE_KEY,
                "source_policy_fingerprint": DEFAULT_LIVE_SOURCE_POLICY.policy_fingerprint,
                "information_cutoff_date": self.information_cutoff_date.isoformat(),
                "components": tuple(component.fingerprint_payload() for component in self.components),
            }
        )


@dataclass(frozen=True, slots=True)
class DailyMarketFoundationReceipt:
    source_key: str
    acquisition_contract_version: str
    acquisition_fingerprint: str
    information_cutoff_date: str
    covered_sessions: tuple[str, ...]
    stock_codes: tuple[str, ...]
    index_codes: tuple[str, ...]
    market: PersistedComponentReceipt
    benchmark: PersistedComponentReceipt

    @property
    def receipt_fingerprint(self) -> str:
        return canonical_sha256(
            {
                "source_key": self.source_key,
                "acquisition_contract_version": self.acquisition_contract_version,
                "acquisition_fingerprint": self.acquisition_fingerprint,
                "information_cutoff_date": self.information_cutoff_date,
                "covered_sessions": self.covered_sessions,
                "stock_codes": self.stock_codes,
                "index_codes": self.index_codes,
                "market": self.market.stable_identity_payload(),
                "benchmark": self.benchmark.stable_identity_payload(),
            }
        )

    def public_summary(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "source_key": self.source_key,
                "acquisition_contract_version": self.acquisition_contract_version,
                "acquisition_fingerprint": self.acquisition_fingerprint,
                "receipt_fingerprint": self.receipt_fingerprint,
                "information_cutoff_date": self.information_cutoff_date,
                "covered_sessions": self.covered_sessions,
                "stock_codes": self.stock_codes,
                "index_codes": self.index_codes,
                "market": self.market.public_payload(),
                "benchmark": self.benchmark.public_payload(),
            }
        )


@dataclass(frozen=True, slots=True)
class _PreparedPersistence:
    market_bundle: MarketDataBundle
    benchmark_bundle: BenchmarkIndexBundle
    requested_start_date: str
    requested_end_date: str
    information_cutoff_date: str
    market_scope: dict[str, object]
    benchmark_scope: dict[str, object]
    provider_metadata: dict[str, object]
    compatibility_parameters: dict[str, object]
    stock_codes: tuple[str, ...]
    index_codes: tuple[str, ...]
    covered_sessions: tuple[str, ...]


def _require_component(
    component: ValidatedAcquisitionComponent,
    selector_type: type[LiveDailyMarketSelector],
    capability: DailyMarketCapability,
    field_name: str,
) -> None:
    if not isinstance(component, ValidatedAcquisitionComponent) or not isinstance(
        component.selector, selector_type
    ):
        raise DailyMarketAcquisitionError(
            f"{field_name} uses an unexpected selector type",
            AcquisitionFailureCode.COMPONENT_TYPE_MISMATCH,
        )
    if component.selector.capability is not capability:
        raise DailyMarketAcquisitionError(
            f"{field_name} uses an unexpected capability",
            AcquisitionFailureCode.COMPONENT_BINDING_MISMATCH,
        )
    planned_sessions = tuple(component.plan.requested_sessions)
    selected_sessions = tuple(item.isoformat() for item in component.selector.requested_sessions)
    if planned_sessions != selected_sessions or component.response.covered_sessions != selected_sessions:
        raise DailyMarketAcquisitionError(
            f"{field_name} selector, plan and response session coverage differ",
            AcquisitionFailureCode.COVERAGE_MISMATCH,
        )


def _date_value(value: object, field_name: str) -> date:
    if not isinstance(value, str):
        raise DailyMarketAcquisitionError(
            f"{field_name} is not a canonical date string",
            AcquisitionFailureCode.COMPONENT_BINDING_MISMATCH,
        )
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise DailyMarketAcquisitionError(
            f"{field_name} is not a canonical date string",
            AcquisitionFailureCode.COMPONENT_BINDING_MISMATCH,
        ) from exc


def _prepare(value: DailyMarketFoundationInput) -> _PreparedPersistence:
    _require_component(
        value.listed_instruments,
        ListedInstrumentSelector,
        DailyMarketCapability.LISTED_INSTRUMENT_IDENTITY,
        "listed_instruments",
    )
    _require_component(
        value.trading_calendar,
        TradingCalendarSelector,
        DailyMarketCapability.TRADING_CALENDAR,
        "trading_calendar",
    )
    _require_component(
        value.a_share_daily_raw,
        AShareDailySelector,
        DailyMarketCapability.A_SHARE_DAILY_RAW,
        "a_share_daily_raw",
    )
    _require_component(
        value.benchmark_daily,
        BenchmarkDailySelector,
        DailyMarketCapability.BENCHMARK_INDEX_DAILY,
        "benchmark_daily",
    )

    listed_selector = value.listed_instruments.selector
    calendar_selector = value.trading_calendar.selector
    daily_selector = value.a_share_daily_raw.selector
    benchmark_selector = value.benchmark_daily.selector
    assert isinstance(listed_selector, ListedInstrumentSelector)
    assert isinstance(calendar_selector, TradingCalendarSelector)
    assert isinstance(daily_selector, AShareDailySelector)
    assert isinstance(benchmark_selector, BenchmarkDailySelector)

    cutoff = value.information_cutoff_date
    if listed_selector.as_of_date != cutoff:
        raise DailyMarketAcquisitionError(
            "listed instrument as_of_date must equal information_cutoff_date",
            AcquisitionFailureCode.COVERAGE_MISMATCH,
        )
    for selector in (listed_selector, calendar_selector, daily_selector, benchmark_selector):
        if selector.provider_horizon_reference_date != cutoff:
            raise DailyMarketAcquisitionError(
                "all selectors must bind the same provider horizon reference date",
                AcquisitionFailureCode.COVERAGE_MISMATCH,
            )
    if listed_selector.identities != daily_selector.identities:
        raise DailyMarketAcquisitionError(
            "listed instrument and A-share daily identity scopes must match exactly",
            AcquisitionFailureCode.COVERAGE_MISMATCH,
        )
    if daily_selector.adjustment.value != "":
        raise DailyMarketAcquisitionError(
            "foundation persistence requires the exact raw daily series",
            AcquisitionFailureCode.UNSUPPORTED_ADJUSTMENT,
        )
    if calendar_selector.requested_dates != daily_selector.requested_sessions:
        raise DailyMarketAcquisitionError(
            "trade calendar dates must equal A-share requested sessions",
            AcquisitionFailureCode.COVERAGE_MISMATCH,
        )
    if benchmark_selector.requested_sessions != daily_selector.requested_sessions:
        raise DailyMarketAcquisitionError(
            "benchmark and A-share requested sessions must match exactly",
            AcquisitionFailureCode.COVERAGE_MISMATCH,
        )

    calendar_items = value.trading_calendar.response.items_as_dicts()
    closed_dates = sorted(
        str(item["trade_date"]) for item in calendar_items if item["is_open"] is not True
    )
    if closed_dates:
        raise DailyMarketAcquisitionError(
            f"daily observations cannot be persisted for closed sessions: {closed_dates}",
            AcquisitionFailureCode.CLOSED_SESSION,
        )

    stock_codes = tuple(identity.stock_code for identity in daily_selector.identities)
    index_codes = tuple(identity.index_code for identity in benchmark_selector.identities)
    unsupported_index_codes = sorted(code for code in index_codes if not _INDEX_OWNER_CODE.fullmatch(code))
    if unsupported_index_codes:
        raise DailyMarketAcquisitionError(
            "benchmark identity cannot be represented by the existing six-digit owner",
            AcquisitionFailureCode.OWNER_IDENTITY_UNSUPPORTED,
        )

    listed_rows: list[dict[str, object]] = []
    for row in value.listed_instruments.response.items_as_dicts():
        listing_date = row["listing_date"]
        listed_rows.append(
            {
                "stock_code": row["stock_code"],
                "stock_name": row["stock_name"],
                "exchange": row["exchange"],
                "industry": "",
                "listing_date": None if listing_date is None else _date_value(listing_date, "listing_date"),
                "status": row["status"],
                "source": SOURCE_KEY,
            }
        )
    daily_rows: list[dict[str, object]] = []
    for row in value.a_share_daily_raw.response.items_as_dicts():
        daily_rows.append(
            {
                "trade_date": _date_value(row["trade_date"], "daily trade_date"),
                "stock_code": row["stock_code"],
                "open": row["open"],
                "high": row["high"],
                "low": row["low"],
                "close": row["close"],
                "volume": row["volume"],
                "amount": row["amount"],
                "adjust_type": row["adjust_type"],
                "source": SOURCE_KEY,
            }
        )
    calendar_rows = [
        {
            "trade_date": _date_value(row["trade_date"], "calendar trade_date"),
            "is_open": row["is_open"],
            "source": SOURCE_KEY,
        }
        for row in calendar_items
    ]
    benchmark_rows = [
        {
            "source": SOURCE_KEY,
            "index_code": row["index_code"],
            "trade_date": _date_value(row["trade_date"], "benchmark trade_date"),
            "open": row["open"],
            "high": row["high"],
            "low": row["low"],
            "close": row["close"],
            "volume": row["volume"],
            "amount": row["amount"],
        }
        for row in value.benchmark_daily.response.items_as_dicts()
    ]

    market_bundle = MarketDataBundle(
        stock_basic=pd.DataFrame(listed_rows, columns=STOCK_BASIC_COLUMNS),
        daily_price=pd.DataFrame(daily_rows, columns=DAILY_PRICE_COLUMNS),
        trade_calendar=pd.DataFrame(calendar_rows, columns=TRADE_CALENDAR_COLUMNS),
    )
    benchmark_bundle = BenchmarkIndexBundle(
        benchmark_index_daily=pd.DataFrame(
            benchmark_rows,
            columns=BENCHMARK_INDEX_DAILY_COLUMNS,
        )
    )
    first_session = daily_selector.requested_sessions[0]
    last_session = daily_selector.requested_sessions[-1]
    compact_cutoff = cutoff.strftime("%Y%m%d")
    compact_start = first_session.strftime("%Y%m%d")
    compact_end = last_session.strftime("%Y%m%d")
    market_scope: dict[str, object] = {
        "datasets": ["stock_basic", "daily_price", "trade_calendar"],
        "stock_codes": list(stock_codes),
        "stock_code_semantics": "exact",
        "snapshot_mode": "complete",
    }
    benchmark_scope: dict[str, object] = {
        "datasets": ["benchmark_index_daily"],
        "index_codes": list(index_codes),
        "index_code_semantics": "exact",
    }
    component_plans = {
        component.selector.capability.value: component.plan.plan_fingerprint
        for component in value.components
    }
    component_responses = {
        component.selector.capability.value: component.response.content_fingerprint
        for component in value.components
    }
    operation_keys = {
        component.selector.capability.value: component.plan.operation_key
        for component in value.components
    }
    provider_metadata: dict[str, object] = {
        "acquisition_contract_version": ACQUISITION_CONTRACT_VERSION,
        "acquisition_fingerprint": value.acquisition_fingerprint,
        "source_policy_fingerprint": DEFAULT_LIVE_SOURCE_POLICY.policy_fingerprint,
        "plan_fingerprints": component_plans,
        "response_fingerprints": component_responses,
        "operation_keys": operation_keys,
        "calendar_exchange": calendar_selector.exchange.value,
    }
    compatibility_parameters: dict[str, object] = {
        "acquisition_contract_version": ACQUISITION_CONTRACT_VERSION,
        "source_policy_fingerprint": DEFAULT_LIVE_SOURCE_POLICY.policy_fingerprint,
        "calendar_exchange": calendar_selector.exchange.value,
    }

    try:
        validate_market_data_bundle(
            market_bundle,
            provider=SOURCE_KEY,
            requested_start_date=compact_start,
            requested_end_date=compact_end,
            information_cutoff_date=compact_cutoff,
            requested_scope=market_scope,
            adjust_type="",
            compatibility_parameters=compatibility_parameters,
            contract_version=MARKET_CONTRACT_VERSION,
        )
        validate_benchmark_bundle(
            benchmark_bundle,
            provider=SOURCE_KEY,
            requested_start_date=compact_start,
            requested_end_date=compact_end,
            information_cutoff_date=compact_cutoff,
            requested_scope=benchmark_scope,
            endpoint=value.benchmark_daily.plan.operation_key,
            adapter_compatibility_version=ACQUISITION_ADAPTER_VERSION,
            contract_version=BENCHMARK_CONTRACT_VERSION,
            compatibility_parameters=compatibility_parameters,
        )
    except Exception as exc:
        raise DailyMarketAcquisitionError(
            "validated Provider responses cannot be represented by the existing owners",
            AcquisitionFailureCode.OWNER_PREVALIDATION_FAILED,
        ) from exc

    return _PreparedPersistence(
        market_bundle=market_bundle,
        benchmark_bundle=benchmark_bundle,
        requested_start_date=compact_start,
        requested_end_date=compact_end,
        information_cutoff_date=compact_cutoff,
        market_scope=market_scope,
        benchmark_scope=benchmark_scope,
        provider_metadata=provider_metadata,
        compatibility_parameters=compatibility_parameters,
        stock_codes=stock_codes,
        index_codes=index_codes,
        covered_sessions=tuple(item.isoformat() for item in daily_selector.requested_sessions),
    )


def _market_receipt(result: IngestionResult) -> PersistedComponentReceipt:
    return PersistedComponentReceipt(
        component_key=MARKET_DATA_COMPONENT_KEY,
        owner="MarketDataPersistenceService",
        ingestion_run_id=result.ingestion_run_id,
        batch_identifier=result.batch_identifier,
        series_key=result.series_key,
        information_cutoff_date=result.information_cutoff_date,
        rows_received=result.rows_received,
        rows_written=result.rows_written,
        idempotent=result.idempotent,
    )


def _benchmark_receipt(result: BenchmarkIngestionResult) -> PersistedComponentReceipt:
    return PersistedComponentReceipt(
        component_key=BENCHMARK_INDEX_DAILY_COMPONENT_KEY,
        owner="BenchmarkPersistenceService",
        ingestion_run_id=result.ingestion_run_id,
        batch_identifier=result.batch_identifier,
        series_key=result.series_key,
        information_cutoff_date=result.information_cutoff_date,
        rows_received=result.rows_received,
        rows_written=result.rows_written,
        idempotent=result.idempotent,
    )


class DailyMarketAcquisitionPersistenceService:
    """Persist one complete validated foundation through existing immutable owners."""

    def __init__(
        self,
        market_persistence: MarketDataPersistenceService,
        benchmark_persistence: BenchmarkPersistenceService,
    ) -> None:
        if not isinstance(market_persistence, MarketDataPersistenceService):
            raise TypeError("market_persistence must be MarketDataPersistenceService")
        if not isinstance(benchmark_persistence, BenchmarkPersistenceService):
            raise TypeError("benchmark_persistence must be BenchmarkPersistenceService")
        self._market_persistence = market_persistence
        self._benchmark_persistence = benchmark_persistence

    def persist_foundation(
        self,
        value: DailyMarketFoundationInput,
    ) -> DailyMarketFoundationReceipt:
        if not isinstance(value, DailyMarketFoundationInput):
            raise DailyMarketAcquisitionError(
                "value must be DailyMarketFoundationInput",
                AcquisitionFailureCode.COMPONENT_TYPE_MISMATCH,
            )
        prepared = _prepare(value)
        try:
            market_result = self._market_persistence.ingest_bundle(
                prepared.market_bundle,
                provider=SOURCE_KEY,
                requested_start_date=prepared.requested_start_date,
                requested_end_date=prepared.requested_end_date,
                information_cutoff_date=prepared.information_cutoff_date,
                requested_scope=prepared.market_scope,
                contract_version=MARKET_CONTRACT_VERSION,
                adjust_type="",
                compatibility_parameters=prepared.compatibility_parameters,
                provider_request_metadata=prepared.provider_metadata,
                adapter_version=ACQUISITION_ADAPTER_VERSION,
            )
        except Exception as exc:
            raise DailyMarketAcquisitionError(
                "market-data owner rejected the complete validated component",
                AcquisitionFailureCode.MARKET_PERSISTENCE_FAILED,
            ) from exc
        market_receipt = _market_receipt(market_result)

        try:
            benchmark_result = self._benchmark_persistence.ingest_bundle(
                prepared.benchmark_bundle,
                provider=SOURCE_KEY,
                requested_start_date=prepared.requested_start_date,
                requested_end_date=prepared.requested_end_date,
                information_cutoff_date=prepared.information_cutoff_date,
                requested_scope=prepared.benchmark_scope,
                endpoint=value.benchmark_daily.plan.operation_key,
                adapter_compatibility_version=ACQUISITION_ADAPTER_VERSION,
                provider_request_metadata=prepared.provider_metadata,
                adapter_version=ACQUISITION_ADAPTER_VERSION,
                contract_version=BENCHMARK_CONTRACT_VERSION,
                compatibility_parameters=prepared.compatibility_parameters,
            )
        except Exception as exc:
            raise DailyMarketAcquisitionError(
                "benchmark owner failed after a valid market component was persisted; no complete acquisition was published",
                AcquisitionFailureCode.BENCHMARK_PERSISTENCE_FAILED,
                persisted_market=market_receipt,
            ) from exc
        benchmark_receipt = _benchmark_receipt(benchmark_result)

        return DailyMarketFoundationReceipt(
            source_key=SOURCE_KEY,
            acquisition_contract_version=ACQUISITION_CONTRACT_VERSION,
            acquisition_fingerprint=value.acquisition_fingerprint,
            information_cutoff_date=prepared.information_cutoff_date,
            covered_sessions=prepared.covered_sessions,
            stock_codes=prepared.stock_codes,
            index_codes=prepared.index_codes,
            market=market_receipt,
            benchmark=benchmark_receipt,
        )


FoundationSelector: TypeAlias = (
    ListedInstrumentSelector
    | TradingCalendarSelector
    | AShareDailySelector
    | BenchmarkDailySelector
)
