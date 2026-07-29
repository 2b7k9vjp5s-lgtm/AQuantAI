"""Closed live selectors for THS Today Market daily-market acquisition.

Selectors contain only explicit, reviewed request facts. They never infer an
exchange from a security code, derive sessions from wall-clock weekdays, read
credentials, or select a transport endpoint.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import Enum
import re
from typing import TypeAlias

from .fingerprint import canonical_sha256
from .live_contracts import DailyMarketCapability, HISTORICAL_QUERY_YEARS


_STOCK_CODE_RE = re.compile(r"^[0-9]{6}$")
_INDEX_CODE_RE = re.compile(r"^[A-Z0-9._-]{2,32}$")
_PROVIDER_SYMBOL_RE = re.compile(r"^[A-Z0-9._:-]{3,64}$")
_BLOCK_ID_RE = re.compile(r"^[A-Z0-9._:-]{2,64}$")


class LiveSelectorError(ValueError):
    """Raised when an explicit source selector is incomplete or out of bounds."""


class Exchange(str, Enum):
    SSE = "SSE"
    SZSE = "SZSE"
    BSE = "BSE"


class DailyAdjustment(str, Enum):
    RAW = ""
    QFQ = "qfq"
    HFQ = "hfq"


class BlockTaxonomy(str, Enum):
    INDUSTRY = "industry"
    CONCEPT = "concept"


def _required_text(value: str, field_name: str, pattern: re.Pattern[str] | None = None) -> str:
    if not isinstance(value, str) or not value.strip():
        raise LiveSelectorError(f"{field_name} must be a non-empty string")
    normalized = value.strip()
    if pattern is not None and not pattern.fullmatch(normalized):
        raise LiveSelectorError(f"{field_name} has an invalid closed format")
    return normalized


def _require_date(value: date, field_name: str) -> date:
    if not isinstance(value, date):
        raise LiveSelectorError(f"{field_name} must be a date")
    return value


def _horizon_floor(reference_date: date) -> date:
    try:
        return reference_date.replace(year=reference_date.year - HISTORICAL_QUERY_YEARS)
    except ValueError:
        return reference_date.replace(
            year=reference_date.year - HISTORICAL_QUERY_YEARS,
            month=2,
            day=28,
        )


def _validate_horizon(value: date, reference_date: date, field_name: str) -> None:
    floor = _horizon_floor(reference_date)
    if value < floor:
        raise LiveSelectorError(
            f"{field_name} is older than the rolling {HISTORICAL_QUERY_YEARS}-year Provider horizon"
        )
    if value > reference_date:
        raise LiveSelectorError(f"{field_name} must not exceed provider_horizon_reference_date")


def _validate_sessions(
    values: tuple[date, ...],
    reference_date: date,
    field_name: str,
    *,
    maximum: int | None = None,
) -> tuple[date, ...]:
    if not isinstance(values, tuple) or not values:
        raise LiveSelectorError(f"{field_name} must be a non-empty tuple")
    if any(not isinstance(item, date) for item in values):
        raise LiveSelectorError(f"{field_name} must contain date values")
    if tuple(sorted(set(values))) != values:
        raise LiveSelectorError(f"{field_name} must be sorted and unique")
    if maximum is not None and len(values) > maximum:
        raise LiveSelectorError(f"{field_name} exceeds the maximum of {maximum}")
    for item in values:
        _validate_horizon(item, reference_date, field_name)
    return values


@dataclass(frozen=True, slots=True)
class EquityIdentity:
    provider_symbol: str
    stock_code: str
    exchange: Exchange

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "provider_symbol",
            _required_text(self.provider_symbol, "provider_symbol", _PROVIDER_SYMBOL_RE),
        )
        object.__setattr__(
            self,
            "stock_code",
            _required_text(self.stock_code, "stock_code", _STOCK_CODE_RE),
        )
        if not isinstance(self.exchange, Exchange):
            raise LiveSelectorError("exchange must be an Exchange")

    @property
    def identity_key(self) -> str:
        return f"{self.exchange.value}:{self.stock_code}:{self.provider_symbol}"

    def fingerprint_payload(self) -> dict[str, str]:
        return {
            "provider_symbol": self.provider_symbol,
            "stock_code": self.stock_code,
            "exchange": self.exchange.value,
        }


@dataclass(frozen=True, slots=True)
class BenchmarkIdentity:
    provider_symbol: str
    index_code: str
    exchange: Exchange

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "provider_symbol",
            _required_text(self.provider_symbol, "provider_symbol", _PROVIDER_SYMBOL_RE),
        )
        object.__setattr__(
            self,
            "index_code",
            _required_text(self.index_code, "index_code", _INDEX_CODE_RE),
        )
        if not isinstance(self.exchange, Exchange):
            raise LiveSelectorError("exchange must be an Exchange")

    @property
    def identity_key(self) -> str:
        return f"{self.exchange.value}:{self.index_code}:{self.provider_symbol}"

    def fingerprint_payload(self) -> dict[str, str]:
        return {
            "provider_symbol": self.provider_symbol,
            "index_code": self.index_code,
            "exchange": self.exchange.value,
        }


@dataclass(frozen=True, slots=True)
class ExpectedObservation:
    identity_key: str
    trade_date: date

    def __post_init__(self) -> None:
        object.__setattr__(self, "identity_key", _required_text(self.identity_key, "identity_key"))
        _require_date(self.trade_date, "trade_date")

    def fingerprint_payload(self) -> dict[str, str]:
        return {
            "identity_key": self.identity_key,
            "trade_date": self.trade_date.isoformat(),
        }


def _validate_equity_identities(values: tuple[EquityIdentity, ...]) -> tuple[EquityIdentity, ...]:
    if not isinstance(values, tuple) or not values:
        raise LiveSelectorError("identities must be a non-empty tuple")
    if any(not isinstance(item, EquityIdentity) for item in values):
        raise LiveSelectorError("identities must contain EquityIdentity values")
    keys = tuple(item.identity_key for item in values)
    if tuple(sorted(set(keys))) != keys:
        raise LiveSelectorError("identities must be sorted by identity_key and unique")
    return values


def _validate_benchmark_identities(
    values: tuple[BenchmarkIdentity, ...],
) -> tuple[BenchmarkIdentity, ...]:
    if not isinstance(values, tuple) or not values:
        raise LiveSelectorError("identities must be a non-empty tuple")
    if any(not isinstance(item, BenchmarkIdentity) for item in values):
        raise LiveSelectorError("identities must contain BenchmarkIdentity values")
    keys = tuple(item.identity_key for item in values)
    if tuple(sorted(set(keys))) != keys:
        raise LiveSelectorError("identities must be sorted by identity_key and unique")
    return values


def _validate_expected_observations(
    values: tuple[ExpectedObservation, ...],
    *,
    identity_keys: set[str],
    requested_sessions: tuple[date, ...],
) -> tuple[ExpectedObservation, ...]:
    if not isinstance(values, tuple) or not values:
        raise LiveSelectorError("expected_observations must be a non-empty tuple")
    if any(not isinstance(item, ExpectedObservation) for item in values):
        raise LiveSelectorError("expected_observations must contain ExpectedObservation values")
    keys = tuple((item.trade_date, item.identity_key) for item in values)
    if tuple(sorted(set(keys))) != keys:
        raise LiveSelectorError(
            "expected_observations must be sorted by trade_date/identity_key and unique"
        )
    unknown_identities = sorted({item.identity_key for item in values} - identity_keys)
    if unknown_identities:
        raise LiveSelectorError(
            f"expected_observations reference unknown identities: {unknown_identities}"
        )
    unknown_dates = sorted({item.trade_date for item in values} - set(requested_sessions))
    if unknown_dates:
        raise LiveSelectorError(
            "expected_observations contain dates outside requested_sessions"
        )
    covered_sessions = {item.trade_date for item in values}
    if covered_sessions != set(requested_sessions):
        raise LiveSelectorError("every requested session must have an expected observation")
    covered_identities = {item.identity_key for item in values}
    if covered_identities != identity_keys:
        raise LiveSelectorError("every selected identity must have an expected observation")
    return values


@dataclass(frozen=True, slots=True)
class ListedInstrumentSelector:
    identities: tuple[EquityIdentity, ...]
    as_of_date: date
    provider_horizon_reference_date: date
    schema_version: str = "aquantai.ths-listed-instrument-selector.v1"

    def __post_init__(self) -> None:
        _validate_equity_identities(self.identities)
        _require_date(self.as_of_date, "as_of_date")
        _require_date(self.provider_horizon_reference_date, "provider_horizon_reference_date")
        _validate_horizon(
            self.as_of_date,
            self.provider_horizon_reference_date,
            "as_of_date",
        )

    @property
    def capability(self) -> DailyMarketCapability:
        return DailyMarketCapability.LISTED_INSTRUMENT_IDENTITY

    @property
    def requested_sessions(self) -> tuple[date, ...]:
        return (self.as_of_date,)

    @property
    def item_count(self) -> int:
        return len(self.identities)

    def ordered_parameters(self) -> tuple[tuple[str, str], ...]:
        return (
            ("as_of_date", self.as_of_date.isoformat()),
            ("identity_keys", ",".join(item.identity_key for item in self.identities)),
        )

    def fingerprint_payload(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "capability": self.capability.value,
            "identities": tuple(item.fingerprint_payload() for item in self.identities),
            "as_of_date": self.as_of_date.isoformat(),
            "provider_horizon_reference_date": self.provider_horizon_reference_date.isoformat(),
        }

    @property
    def selector_fingerprint(self) -> str:
        return canonical_sha256(self.fingerprint_payload())


@dataclass(frozen=True, slots=True)
class TradingCalendarSelector:
    exchange: Exchange
    requested_dates: tuple[date, ...]
    provider_horizon_reference_date: date
    schema_version: str = "aquantai.ths-trading-calendar-selector.v1"

    def __post_init__(self) -> None:
        if not isinstance(self.exchange, Exchange):
            raise LiveSelectorError("exchange must be an Exchange")
        _require_date(self.provider_horizon_reference_date, "provider_horizon_reference_date")
        _validate_sessions(
            self.requested_dates,
            self.provider_horizon_reference_date,
            "requested_dates",
        )

    @property
    def capability(self) -> DailyMarketCapability:
        return DailyMarketCapability.TRADING_CALENDAR

    @property
    def requested_sessions(self) -> tuple[date, ...]:
        return self.requested_dates

    @property
    def item_count(self) -> int:
        return 1

    def ordered_parameters(self) -> tuple[tuple[str, str], ...]:
        return (
            ("exchange", self.exchange.value),
            ("requested_dates", ",".join(item.isoformat() for item in self.requested_dates)),
        )

    def fingerprint_payload(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "capability": self.capability.value,
            "exchange": self.exchange.value,
            "requested_dates": tuple(item.isoformat() for item in self.requested_dates),
            "provider_horizon_reference_date": self.provider_horizon_reference_date.isoformat(),
        }

    @property
    def selector_fingerprint(self) -> str:
        return canonical_sha256(self.fingerprint_payload())


@dataclass(frozen=True, slots=True)
class AShareDailySelector:
    identities: tuple[EquityIdentity, ...]
    requested_sessions: tuple[date, ...]
    expected_observations: tuple[ExpectedObservation, ...]
    adjustment: DailyAdjustment
    provider_horizon_reference_date: date
    schema_version: str = "aquantai.ths-a-share-daily-selector.v1"

    def __post_init__(self) -> None:
        _validate_equity_identities(self.identities)
        _require_date(self.provider_horizon_reference_date, "provider_horizon_reference_date")
        _validate_sessions(
            self.requested_sessions,
            self.provider_horizon_reference_date,
            "requested_sessions",
            maximum=10,
        )
        if not isinstance(self.adjustment, DailyAdjustment):
            raise LiveSelectorError("adjustment must be a DailyAdjustment")
        _validate_expected_observations(
            self.expected_observations,
            identity_keys={item.identity_key for item in self.identities},
            requested_sessions=self.requested_sessions,
        )

    @property
    def capability(self) -> DailyMarketCapability:
        if self.adjustment is DailyAdjustment.RAW:
            return DailyMarketCapability.A_SHARE_DAILY_RAW
        return DailyMarketCapability.A_SHARE_DAILY_ADJUSTED

    @property
    def item_count(self) -> int:
        return len(self.expected_observations)

    def ordered_parameters(self) -> tuple[tuple[str, str], ...]:
        return (
            ("adjustment", self.adjustment.value or "raw"),
            ("identity_keys", ",".join(item.identity_key for item in self.identities)),
            ("requested_sessions", ",".join(item.isoformat() for item in self.requested_sessions)),
        )

    def fingerprint_payload(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "capability": self.capability.value,
            "identities": tuple(item.fingerprint_payload() for item in self.identities),
            "requested_sessions": tuple(item.isoformat() for item in self.requested_sessions),
            "expected_observations": tuple(
                item.fingerprint_payload() for item in self.expected_observations
            ),
            "adjustment": self.adjustment.value,
            "provider_horizon_reference_date": self.provider_horizon_reference_date.isoformat(),
        }

    @property
    def selector_fingerprint(self) -> str:
        return canonical_sha256(self.fingerprint_payload())


@dataclass(frozen=True, slots=True)
class BenchmarkDailySelector:
    identities: tuple[BenchmarkIdentity, ...]
    requested_sessions: tuple[date, ...]
    expected_observations: tuple[ExpectedObservation, ...]
    provider_horizon_reference_date: date
    schema_version: str = "aquantai.ths-benchmark-daily-selector.v1"

    def __post_init__(self) -> None:
        _validate_benchmark_identities(self.identities)
        _require_date(self.provider_horizon_reference_date, "provider_horizon_reference_date")
        _validate_sessions(
            self.requested_sessions,
            self.provider_horizon_reference_date,
            "requested_sessions",
            maximum=10,
        )
        _validate_expected_observations(
            self.expected_observations,
            identity_keys={item.identity_key for item in self.identities},
            requested_sessions=self.requested_sessions,
        )

    @property
    def capability(self) -> DailyMarketCapability:
        return DailyMarketCapability.BENCHMARK_INDEX_DAILY

    @property
    def item_count(self) -> int:
        return len(self.expected_observations)

    def ordered_parameters(self) -> tuple[tuple[str, str], ...]:
        return (
            ("identity_keys", ",".join(item.identity_key for item in self.identities)),
            ("requested_sessions", ",".join(item.isoformat() for item in self.requested_sessions)),
        )

    def fingerprint_payload(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "capability": self.capability.value,
            "identities": tuple(item.fingerprint_payload() for item in self.identities),
            "requested_sessions": tuple(item.isoformat() for item in self.requested_sessions),
            "expected_observations": tuple(
                item.fingerprint_payload() for item in self.expected_observations
            ),
            "provider_horizon_reference_date": self.provider_horizon_reference_date.isoformat(),
        }

    @property
    def selector_fingerprint(self) -> str:
        return canonical_sha256(self.fingerprint_payload())


@dataclass(frozen=True, slots=True)
class HistoricalBlockSnapshotSelector:
    taxonomy: BlockTaxonomy
    block_id: str
    snapshot_date: date
    expected_member_count: int
    provider_horizon_reference_date: date
    schema_version: str = "aquantai.ths-historical-block-snapshot-selector.v1"

    def __post_init__(self) -> None:
        if not isinstance(self.taxonomy, BlockTaxonomy):
            raise LiveSelectorError("taxonomy must be a BlockTaxonomy")
        object.__setattr__(
            self,
            "block_id",
            _required_text(self.block_id, "block_id", _BLOCK_ID_RE),
        )
        _require_date(self.snapshot_date, "snapshot_date")
        _require_date(self.provider_horizon_reference_date, "provider_horizon_reference_date")
        _validate_horizon(
            self.snapshot_date,
            self.provider_horizon_reference_date,
            "snapshot_date",
        )
        if isinstance(self.expected_member_count, bool) or not isinstance(
            self.expected_member_count, int
        ):
            raise LiveSelectorError("expected_member_count must be an integer")
        if self.expected_member_count < 0:
            raise LiveSelectorError("expected_member_count must not be negative")

    @property
    def capability(self) -> DailyMarketCapability:
        return DailyMarketCapability.HISTORICAL_BLOCK_SNAPSHOT

    @property
    def requested_sessions(self) -> tuple[date, ...]:
        return (self.snapshot_date,)

    @property
    def item_count(self) -> int:
        return self.expected_member_count

    def ordered_parameters(self) -> tuple[tuple[str, str], ...]:
        return (
            ("taxonomy", self.taxonomy.value),
            ("block_id", self.block_id),
            ("snapshot_date", self.snapshot_date.isoformat()),
        )

    def fingerprint_payload(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "capability": self.capability.value,
            "taxonomy": self.taxonomy.value,
            "block_id": self.block_id,
            "snapshot_date": self.snapshot_date.isoformat(),
            "expected_member_count": self.expected_member_count,
            "provider_horizon_reference_date": self.provider_horizon_reference_date.isoformat(),
        }

    @property
    def selector_fingerprint(self) -> str:
        return canonical_sha256(self.fingerprint_payload())


LiveDailyMarketSelector: TypeAlias = (
    ListedInstrumentSelector
    | TradingCalendarSelector
    | AShareDailySelector
    | BenchmarkDailySelector
    | HistoricalBlockSnapshotSelector
)
