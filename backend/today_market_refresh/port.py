"""Provider-neutral application ports for Today Market acquisition.

The accepted Mock port remains unchanged. Slice A adds a separate live handoff contract that
projects already-persisted source receipts into completeness/provenance-only application values.
It does not activate runtime networking, publish a snapshot, or calculate market/sector truth.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from enum import Enum
from types import MappingProxyType
from typing import Mapping, Protocol, runtime_checkable

from .contracts import (
    CoverageStatus,
    FailureCategory,
    RefreshTrigger,
    Retryability,
    SourceMode,
    TodayMarketAcquisitionBatch,
    TodayMarketAcquisitionFailure,
    TodayMarketRefreshPlan,
    TodayMarketSourceProvenance,
)
from .fingerprint import canonical_sha256

LIVE_HANDOFF_CONTRACT_VERSION = "aquantai.today-market-live-acquisition-handoff.v1"
LIVE_ADAPTER_CONTRACT_VERSION = "aquantai.today-market-live-acquisition-port.v1"


@runtime_checkable
class TodayMarketAcquisitionPort(Protocol):
    def acquire(self, plan: TodayMarketRefreshPlan) -> TodayMarketAcquisitionBatch:
        """Return one complete Mock batch or raise a typed application error."""


class LiveComponentKey(str, Enum):
    MARKET_DATA_BUNDLE = "market_data_bundle"
    BENCHMARK_INDEX_DAILY = "benchmark_index_daily"


REQUIRED_LIVE_COMPONENTS = tuple(sorted(LiveComponentKey, key=lambda item: item.value))


class LiveHandoffFailureCode(str, Enum):
    REQUEST_INVALID = "TODAY_MARKET_LIVE_HANDOFF_REQUEST_INVALID"
    SOURCE_MISMATCH = "TODAY_MARKET_LIVE_HANDOFF_SOURCE_MISMATCH"
    ACQUISITION_MISMATCH = "TODAY_MARKET_LIVE_HANDOFF_ACQUISITION_MISMATCH"
    COVERAGE_MISMATCH = "TODAY_MARKET_LIVE_HANDOFF_COVERAGE_MISMATCH"
    COMPONENT_MISMATCH = "TODAY_MARKET_LIVE_HANDOFF_COMPONENT_MISMATCH"
    SENSITIVE_DIAGNOSTIC = "TODAY_MARKET_LIVE_HANDOFF_SENSITIVE_DIAGNOSTIC"


class LiveHandoffValidationError(ValueError):
    def __init__(self, message: str, reason_code: LiveHandoffFailureCode) -> None:
        self.reason_code = reason_code
        super().__init__(message)


def _required_text(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise LiveHandoffValidationError(
            f"{field_name} must be a non-empty string",
            LiveHandoffFailureCode.REQUEST_INVALID,
        )
    return value.strip()


def _sha256(value: object, field_name: str) -> str:
    normalized = _required_text(value, field_name)
    if len(normalized) != 64 or any(character not in "0123456789abcdef" for character in normalized):
        raise LiveHandoffValidationError(
            f"{field_name} must be a lowercase SHA-256 digest",
            LiveHandoffFailureCode.REQUEST_INVALID,
        )
    return normalized


def _aware(value: datetime, field_name: str) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise LiveHandoffValidationError(
            f"{field_name} must be timezone-aware",
            LiveHandoffFailureCode.REQUEST_INVALID,
        )
    return value


def _sorted_sessions(values: tuple[date, ...], field_name: str) -> tuple[date, ...]:
    if not isinstance(values, tuple) or not values or any(not isinstance(item, date) for item in values):
        raise LiveHandoffValidationError(
            f"{field_name} must be a non-empty date tuple",
            LiveHandoffFailureCode.REQUEST_INVALID,
        )
    if tuple(sorted(set(values))) != values:
        raise LiveHandoffValidationError(
            f"{field_name} must be sorted and unique",
            LiveHandoffFailureCode.REQUEST_INVALID,
        )
    return values


@dataclass(frozen=True, slots=True)
class TodayMarketLiveHandoffRequest:
    scope_revision_id: str
    refresh_attempt_id: str
    trigger: RefreshTrigger
    prior_snapshot_id: str | None
    requested_sessions: tuple[date, ...]
    information_cutoff: date
    recorded_at_utc: datetime
    source_key: str
    source_policy_fingerprint: str
    expected_acquisition_fingerprint: str
    handoff_contract_version: str
    request_fingerprint: str

    def __post_init__(self) -> None:
        _required_text(self.scope_revision_id, "scope_revision_id")
        _required_text(self.refresh_attempt_id, "refresh_attempt_id")
        if not isinstance(self.trigger, RefreshTrigger):
            raise LiveHandoffValidationError(
                "trigger must be a RefreshTrigger",
                LiveHandoffFailureCode.REQUEST_INVALID,
            )
        if self.prior_snapshot_id is not None:
            _required_text(self.prior_snapshot_id, "prior_snapshot_id")
        _sorted_sessions(self.requested_sessions, "requested_sessions")
        if self.information_cutoff != self.requested_sessions[-1]:
            raise LiveHandoffValidationError(
                "information_cutoff must equal the latest requested session",
                LiveHandoffFailureCode.COVERAGE_MISMATCH,
            )
        _aware(self.recorded_at_utc, "recorded_at_utc")
        if _required_text(self.source_key, "source_key") == "aquantai-synthetic-today-market-v1":
            raise LiveHandoffValidationError(
                "live handoff cannot use the synthetic source key",
                LiveHandoffFailureCode.SOURCE_MISMATCH,
            )
        _sha256(self.source_policy_fingerprint, "source_policy_fingerprint")
        _sha256(self.expected_acquisition_fingerprint, "expected_acquisition_fingerprint")
        if self.handoff_contract_version != LIVE_HANDOFF_CONTRACT_VERSION:
            raise LiveHandoffValidationError(
                "handoff contract version is not reviewed",
                LiveHandoffFailureCode.REQUEST_INVALID,
            )
        _sha256(self.request_fingerprint, "request_fingerprint")
        if not self.verify_fingerprint():
            raise LiveHandoffValidationError(
                "request_fingerprint does not match the exact live request",
                LiveHandoffFailureCode.REQUEST_INVALID,
            )

    def fingerprint_payload(self) -> Mapping[str, object]:
        return {
            "scope_revision_id": self.scope_revision_id,
            "refresh_attempt_id": self.refresh_attempt_id,
            "trigger": self.trigger,
            "prior_snapshot_id": self.prior_snapshot_id,
            "requested_sessions": self.requested_sessions,
            "information_cutoff": self.information_cutoff,
            "recorded_at_utc": self.recorded_at_utc,
            "source_key": self.source_key,
            "source_policy_fingerprint": self.source_policy_fingerprint,
            "expected_acquisition_fingerprint": self.expected_acquisition_fingerprint,
            "handoff_contract_version": self.handoff_contract_version,
        }

    def verify_fingerprint(self) -> bool:
        return canonical_sha256(self.fingerprint_payload()) == self.request_fingerprint


@dataclass(frozen=True, slots=True)
class TodayMarketLiveComponentResult:
    component_key: LiveComponentKey
    owner: str
    source_key: str
    ingestion_run_id: int
    batch_identifier: str
    series_key: str
    information_cutoff: date
    rows_received: int

    def __post_init__(self) -> None:
        if not isinstance(self.component_key, LiveComponentKey):
            raise LiveHandoffValidationError(
                "component_key must be a LiveComponentKey",
                LiveHandoffFailureCode.COMPONENT_MISMATCH,
            )
        expected_owner = {
            LiveComponentKey.MARKET_DATA_BUNDLE: "MarketDataPersistenceService",
            LiveComponentKey.BENCHMARK_INDEX_DAILY: "BenchmarkPersistenceService",
        }[self.component_key]
        if self.owner != expected_owner:
            raise LiveHandoffValidationError(
                "component owner does not match its provider-neutral key",
                LiveHandoffFailureCode.COMPONENT_MISMATCH,
            )
        _required_text(self.source_key, "component.source_key")
        if isinstance(self.ingestion_run_id, bool) or not isinstance(self.ingestion_run_id, int) or self.ingestion_run_id <= 0:
            raise LiveHandoffValidationError(
                "ingestion_run_id must be a positive integer",
                LiveHandoffFailureCode.COMPONENT_MISMATCH,
            )
        _sha256(self.batch_identifier, "component.batch_identifier")
        _sha256(self.series_key, "component.series_key")
        if not isinstance(self.information_cutoff, date):
            raise LiveHandoffValidationError(
                "component information_cutoff must be a date",
                LiveHandoffFailureCode.COMPONENT_MISMATCH,
            )
        if isinstance(self.rows_received, bool) or not isinstance(self.rows_received, int) or self.rows_received <= 0:
            raise LiveHandoffValidationError(
                "component rows_received must be positive",
                LiveHandoffFailureCode.COMPONENT_MISMATCH,
            )

    def fingerprint_payload(self) -> Mapping[str, object]:
        return {
            "component_key": self.component_key,
            "owner": self.owner,
            "source_key": self.source_key,
            "ingestion_run_id": self.ingestion_run_id,
            "batch_identifier": self.batch_identifier,
            "series_key": self.series_key,
            "information_cutoff": self.information_cutoff,
            "rows_received": self.rows_received,
        }


@dataclass(frozen=True, slots=True)
class TodayMarketLiveCoverage:
    status: CoverageStatus
    requested_sessions: tuple[date, ...]
    covered_sessions: tuple[date, ...]
    required_components: tuple[LiveComponentKey, ...]
    complete_components: tuple[LiveComponentKey, ...]
    missing_components: tuple[LiveComponentKey, ...]

    def __post_init__(self) -> None:
        _sorted_sessions(self.requested_sessions, "coverage.requested_sessions")
        _sorted_sessions(self.covered_sessions, "coverage.covered_sessions")
        if self.status is not CoverageStatus.COMPLETE:
            raise LiveHandoffValidationError(
                "Slice A handoff may expose only complete persisted coverage",
                LiveHandoffFailureCode.COVERAGE_MISMATCH,
            )
        if self.covered_sessions != self.requested_sessions:
            raise LiveHandoffValidationError(
                "live covered sessions must equal requested sessions",
                LiveHandoffFailureCode.COVERAGE_MISMATCH,
            )
        if self.required_components != REQUIRED_LIVE_COMPONENTS:
            raise LiveHandoffValidationError(
                "required live component set is not exact",
                LiveHandoffFailureCode.COMPONENT_MISMATCH,
            )
        if self.complete_components != REQUIRED_LIVE_COMPONENTS or self.missing_components:
            raise LiveHandoffValidationError(
                "complete live component set is not exact",
                LiveHandoffFailureCode.COMPONENT_MISMATCH,
            )


@dataclass(frozen=True, slots=True)
class TodayMarketLiveAcquisitionBatch:
    live_adapter_contract_version: str
    refresh_attempt_id: str
    source_attempt_id: str
    source_provenance: TodayMarketSourceProvenance
    request_fingerprint: str
    acquisition_fingerprint: str
    receipt_fingerprint: str
    requested_sessions: tuple[date, ...]
    data_through_session: date
    coverage: TodayMarketLiveCoverage
    components: tuple[TodayMarketLiveComponentResult, ...]
    redacted_diagnostics: tuple[str, ...]
    batch_fingerprint: str

    def __post_init__(self) -> None:
        if self.live_adapter_contract_version != LIVE_ADAPTER_CONTRACT_VERSION:
            raise LiveHandoffValidationError(
                "live adapter contract version is not reviewed",
                LiveHandoffFailureCode.REQUEST_INVALID,
            )
        _required_text(self.refresh_attempt_id, "refresh_attempt_id")
        _sha256(self.source_attempt_id, "source_attempt_id")
        if self.source_provenance.source_mode is not SourceMode.SOURCE_SPECIFIC_LIVE:
            raise LiveHandoffValidationError(
                "live batch provenance must use SOURCE_SPECIFIC_LIVE",
                LiveHandoffFailureCode.SOURCE_MISMATCH,
            )
        _sha256(self.request_fingerprint, "request_fingerprint")
        _sha256(self.acquisition_fingerprint, "acquisition_fingerprint")
        _sha256(self.receipt_fingerprint, "receipt_fingerprint")
        _sorted_sessions(self.requested_sessions, "requested_sessions")
        if self.data_through_session != self.requested_sessions[-1]:
            raise LiveHandoffValidationError(
                "data_through_session must equal the latest requested session",
                LiveHandoffFailureCode.COVERAGE_MISMATCH,
            )
        component_keys = tuple(component.component_key for component in self.components)
        if component_keys != REQUIRED_LIVE_COMPONENTS:
            raise LiveHandoffValidationError(
                "live batch must contain the exact sorted persisted component set",
                LiveHandoffFailureCode.COMPONENT_MISMATCH,
            )
        if any(component.source_key != self.source_provenance.source_key for component in self.components):
            raise LiveHandoffValidationError(
                "component source differs from live provenance",
                LiveHandoffFailureCode.SOURCE_MISMATCH,
            )
        _sha256(self.batch_fingerprint, "batch_fingerprint")
        if not self.verify_fingerprint():
            raise LiveHandoffValidationError(
                "batch_fingerprint does not match the live acquisition batch",
                LiveHandoffFailureCode.REQUEST_INVALID,
            )

    def fingerprint_payload(self) -> Mapping[str, object]:
        return {
            "live_adapter_contract_version": self.live_adapter_contract_version,
            "refresh_attempt_id": self.refresh_attempt_id,
            "source_attempt_id": self.source_attempt_id,
            "source_provenance": self.source_provenance,
            "request_fingerprint": self.request_fingerprint,
            "acquisition_fingerprint": self.acquisition_fingerprint,
            "receipt_fingerprint": self.receipt_fingerprint,
            "requested_sessions": self.requested_sessions,
            "data_through_session": self.data_through_session,
            "coverage": self.coverage,
            "components": self.components,
            "redacted_diagnostics": self.redacted_diagnostics,
        }

    def verify_fingerprint(self) -> bool:
        return canonical_sha256(self.fingerprint_payload()) == self.batch_fingerprint

    def public_summary(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "live_adapter_contract_version": self.live_adapter_contract_version,
                "refresh_attempt_id": self.refresh_attempt_id,
                "source_attempt_id": self.source_attempt_id,
                "source_key": self.source_provenance.source_key,
                "source_mode": self.source_provenance.source_mode.value,
                "request_fingerprint": self.request_fingerprint,
                "acquisition_fingerprint": self.acquisition_fingerprint,
                "receipt_fingerprint": self.receipt_fingerprint,
                "requested_sessions": tuple(item.isoformat() for item in self.requested_sessions),
                "data_through_session": self.data_through_session.isoformat(),
                "coverage_status": self.coverage.status.value,
                "components": tuple(
                    {
                        "component_key": component.component_key.value,
                        "ingestion_run_id": component.ingestion_run_id,
                        "batch_identifier": component.batch_identifier,
                        "series_key": component.series_key,
                        "rows_received": component.rows_received,
                    }
                    for component in self.components
                ),
                "batch_fingerprint": self.batch_fingerprint,
            }
        )


@runtime_checkable
class LiveFoundationReceipt(Protocol):
    source_key: str
    acquisition_contract_version: str
    acquisition_fingerprint: str
    information_cutoff_date: str
    covered_sessions: tuple[str, ...]
    receipt_fingerprint: str
    market: object
    benchmark: object


@runtime_checkable
class TodayMarketLiveAcquisitionPort(Protocol):
    def project_live(
        self,
        request: TodayMarketLiveHandoffRequest,
        receipt: LiveFoundationReceipt,
        *,
        observed_at_utc: datetime,
    ) -> TodayMarketLiveAcquisitionBatch:
        """Project one complete persisted source receipt without running network or persistence."""


def build_live_handoff_request(
    *,
    scope_revision_id: str,
    refresh_attempt_id: str,
    trigger: RefreshTrigger,
    prior_snapshot_id: str | None,
    requested_sessions: tuple[date, ...],
    information_cutoff: date,
    recorded_at_utc: datetime,
    source_key: str,
    source_policy_fingerprint: str,
    expected_acquisition_fingerprint: str,
) -> TodayMarketLiveHandoffRequest:
    payload = {
        "scope_revision_id": scope_revision_id,
        "refresh_attempt_id": refresh_attempt_id,
        "trigger": trigger,
        "prior_snapshot_id": prior_snapshot_id,
        "requested_sessions": requested_sessions,
        "information_cutoff": information_cutoff,
        "recorded_at_utc": recorded_at_utc,
        "source_key": source_key,
        "source_policy_fingerprint": source_policy_fingerprint,
        "expected_acquisition_fingerprint": expected_acquisition_fingerprint,
        "handoff_contract_version": LIVE_HANDOFF_CONTRACT_VERSION,
    }
    return TodayMarketLiveHandoffRequest(
        **payload,
        request_fingerprint=canonical_sha256(payload),
    )


def _parse_compact_date(value: object, field_name: str) -> date:
    normalized = _required_text(value, field_name)
    if len(normalized) != 8 or not normalized.isdigit():
        raise LiveHandoffValidationError(
            f"{field_name} must use YYYYMMDD",
            LiveHandoffFailureCode.COVERAGE_MISMATCH,
        )
    try:
        return date(int(normalized[0:4]), int(normalized[4:6]), int(normalized[6:8]))
    except ValueError as exc:
        raise LiveHandoffValidationError(
            f"{field_name} is not a valid date",
            LiveHandoffFailureCode.COVERAGE_MISMATCH,
        ) from exc


def _parse_iso_sessions(values: object) -> tuple[date, ...]:
    if not isinstance(values, tuple):
        raise LiveHandoffValidationError(
            "receipt covered_sessions must be a tuple",
            LiveHandoffFailureCode.COVERAGE_MISMATCH,
        )
    try:
        parsed = tuple(date.fromisoformat(_required_text(item, "covered_session")) for item in values)
    except ValueError as exc:
        raise LiveHandoffValidationError(
            "receipt covered_sessions must use canonical ISO dates",
            LiveHandoffFailureCode.COVERAGE_MISMATCH,
        ) from exc
    return _sorted_sessions(parsed, "receipt.covered_sessions")


def _component_from_receipt(
    component_key: LiveComponentKey,
    value: object,
    *,
    source_key: str,
    information_cutoff: date,
) -> TodayMarketLiveComponentResult:
    try:
        owner = value.owner
        ingestion_run_id = value.ingestion_run_id
        batch_identifier = value.batch_identifier
        series_key = value.series_key
        component_cutoff = _parse_compact_date(
            value.information_cutoff_date,
            "component.information_cutoff_date",
        )
        rows_received = value.rows_received
    except AttributeError as exc:
        raise LiveHandoffValidationError(
            "receipt component is missing required persisted identity fields",
            LiveHandoffFailureCode.COMPONENT_MISMATCH,
        ) from exc
    if component_cutoff != information_cutoff:
        raise LiveHandoffValidationError(
            "component cutoff differs from the live handoff cutoff",
            LiveHandoffFailureCode.COVERAGE_MISMATCH,
        )
    return TodayMarketLiveComponentResult(
        component_key=component_key,
        owner=owner,
        source_key=source_key,
        ingestion_run_id=ingestion_run_id,
        batch_identifier=batch_identifier,
        series_key=series_key,
        information_cutoff=component_cutoff,
        rows_received=rows_received,
    )


def project_live_foundation_receipt(
    request: TodayMarketLiveHandoffRequest,
    receipt: LiveFoundationReceipt,
    *,
    observed_at_utc: datetime,
) -> TodayMarketLiveAcquisitionBatch:
    if not isinstance(request, TodayMarketLiveHandoffRequest) or not request.verify_fingerprint():
        raise LiveHandoffValidationError(
            "live request is invalid",
            LiveHandoffFailureCode.REQUEST_INVALID,
        )
    _aware(observed_at_utc, "observed_at_utc")
    if not isinstance(receipt, LiveFoundationReceipt):
        raise LiveHandoffValidationError(
            "receipt does not implement the complete foundation contract",
            LiveHandoffFailureCode.COMPONENT_MISMATCH,
        )
    if receipt.source_key != request.source_key:
        raise LiveHandoffValidationError(
            "receipt source does not match the live request",
            LiveHandoffFailureCode.SOURCE_MISMATCH,
        )
    acquisition_fingerprint = _sha256(
        receipt.acquisition_fingerprint,
        "receipt.acquisition_fingerprint",
    )
    if acquisition_fingerprint != request.expected_acquisition_fingerprint:
        raise LiveHandoffValidationError(
            "receipt acquisition fingerprint differs from the expected source attempt",
            LiveHandoffFailureCode.ACQUISITION_MISMATCH,
        )
    receipt_fingerprint = _sha256(receipt.receipt_fingerprint, "receipt.receipt_fingerprint")
    covered_sessions = _parse_iso_sessions(receipt.covered_sessions)
    information_cutoff = _parse_compact_date(
        receipt.information_cutoff_date,
        "receipt.information_cutoff_date",
    )
    if covered_sessions != request.requested_sessions or information_cutoff != request.information_cutoff:
        raise LiveHandoffValidationError(
            "receipt coverage differs from the exact live request",
            LiveHandoffFailureCode.COVERAGE_MISMATCH,
        )
    components = tuple(
        sorted(
            (
                _component_from_receipt(
                    LiveComponentKey.MARKET_DATA_BUNDLE,
                    receipt.market,
                    source_key=receipt.source_key,
                    information_cutoff=information_cutoff,
                ),
                _component_from_receipt(
                    LiveComponentKey.BENCHMARK_INDEX_DAILY,
                    receipt.benchmark,
                    source_key=receipt.source_key,
                    information_cutoff=information_cutoff,
                ),
            ),
            key=lambda component: component.component_key.value,
        )
    )
    coverage = TodayMarketLiveCoverage(
        status=CoverageStatus.COMPLETE,
        requested_sessions=request.requested_sessions,
        covered_sessions=covered_sessions,
        required_components=REQUIRED_LIVE_COMPONENTS,
        complete_components=REQUIRED_LIVE_COMPONENTS,
        missing_components=(),
    )
    provenance = TodayMarketSourceProvenance(
        source_key=receipt.source_key,
        adapter_contract_version=LIVE_ADAPTER_CONTRACT_VERSION,
        source_contract_fingerprints=tuple(
            sorted(
                (
                    request.source_policy_fingerprint,
                    canonical_sha256(
                        {"acquisition_contract_version": receipt.acquisition_contract_version}
                    ),
                )
            )
        ),
        source_mode=SourceMode.SOURCE_SPECIFIC_LIVE,
        observed_at_utc=observed_at_utc,
        provider_confirmed=False,
    )
    batch_payload = {
        "live_adapter_contract_version": LIVE_ADAPTER_CONTRACT_VERSION,
        "refresh_attempt_id": request.refresh_attempt_id,
        "source_attempt_id": acquisition_fingerprint,
        "source_provenance": provenance,
        "request_fingerprint": request.request_fingerprint,
        "acquisition_fingerprint": acquisition_fingerprint,
        "receipt_fingerprint": receipt_fingerprint,
        "requested_sessions": request.requested_sessions,
        "data_through_session": information_cutoff,
        "coverage": coverage,
        "components": components,
        "redacted_diagnostics": (),
    }
    return TodayMarketLiveAcquisitionBatch(
        **batch_payload,
        batch_fingerprint=canonical_sha256(batch_payload),
    )


def project_live_acquisition_failure(
    *,
    failure_code: str,
    category: FailureCategory,
    refresh_attempt_id: str,
    source_key: str,
    redacted_details: tuple[str, ...],
    retryability: Retryability,
) -> TodayMarketAcquisitionFailure:
    sensitive_terms = ("token", "secret", "password", "api_key", "credential")
    if any(term in detail.lower() for detail in redacted_details for term in sensitive_terms):
        raise LiveHandoffValidationError(
            "live failure diagnostics contain a sensitive term",
            LiveHandoffFailureCode.SENSITIVE_DIAGNOSTIC,
        )
    if not isinstance(category, FailureCategory) or not isinstance(retryability, Retryability):
        raise LiveHandoffValidationError(
            "live failure category or retryability is invalid",
            LiveHandoffFailureCode.REQUEST_INVALID,
        )
    return TodayMarketAcquisitionFailure(
        failure_code=_required_text(failure_code, "failure_code"),
        category=category,
        refresh_attempt_id=_required_text(refresh_attempt_id, "refresh_attempt_id"),
        source_key=_required_text(source_key, "source_key"),
        redacted_details=tuple(_required_text(detail, "redacted_detail") for detail in redacted_details),
        retryability=retryability,
    )


class DeterministicLiveReceiptProjector:
    """Zero-network adapter implementing the separate live handoff port."""

    def project_live(
        self,
        request: TodayMarketLiveHandoffRequest,
        receipt: LiveFoundationReceipt,
        *,
        observed_at_utc: datetime,
    ) -> TodayMarketLiveAcquisitionBatch:
        return project_live_foundation_receipt(
            request,
            receipt,
            observed_at_utc=observed_at_utc,
        )
