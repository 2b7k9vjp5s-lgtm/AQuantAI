"""Immutable provider-neutral contracts for deterministic Today Market refresh tests."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time
from enum import Enum
from types import MappingProxyType
from typing import Any, Mapping

from .fingerprint import canonical_sha256

SYNTHETIC_SOURCE_KEY = "aquantai-synthetic-today-market-v1"
MOCK_ASSUMPTION_PROFILE_ID = "aquantai.today-market.mock-planning-assumption.v1"
PLANNING_POLICY_VERSION = "aquantai.today-market-refresh-planning.v1"
ADAPTER_CONTRACT_VERSION = "aquantai.today-market-acquisition-port.v1"
PROJECTION_VERSION = "aquantai.today-market-mock-projection.v1"
OVERALL_LIVE_GATE = "blocked_quota_contract"


class RefreshTrigger(str, Enum):
    APPLICATION_START = "application_start"
    FIRST_TODAY_MARKET_ENTRY = "first_today_market_entry"
    EXPLICIT_USER_RETRY = "explicit_user_retry"
    EXPLICIT_MANUAL_CATCHUP = "explicit_manual_catchup"


class CapabilityFamily(str, Enum):
    TRADING_CALENDAR = "trading_calendar"
    CORE_INDEX_DAILY_HISTORY = "core_index_daily_history"
    INDUSTRY_INDEX_DAILY_HISTORY = "industry_index_daily_history"
    CONCEPT_INDEX_DAILY_HISTORY = "concept_index_daily_history"
    CURRENT_CONSTITUENTS = "current_constituents"
    LIMIT_UP_POOL = "limit_up_pool"
    LIMIT_UP_LADDER = "limit_up_ladder"
    MARKET_ATTENTION_CANDIDATES = "market_attention_candidates"


REQUIRED_CAPABILITY_FAMILIES = tuple(sorted(CapabilityFamily, key=lambda value: value.value))


class SourceMode(str, Enum):
    SYNTHETIC_MOCK = "synthetic_mock"
    SOURCE_SPECIFIC_LIVE = "source_specific_live"


class CoverageStatus(str, Enum):
    COMPLETE = "complete"
    PARTIAL = "partial"
    EMPTY = "empty"
    INCOMPATIBLE = "incompatible"


class ValidationStatus(str, Enum):
    VALID = "valid"
    INVALID = "invalid"


class Retryability(str, Enum):
    NONE = "none"
    EXPLICIT_USER_RETRY = "explicit_user_retry"
    MANUAL_CATCHUP = "manual_catchup"


class FailureCategory(str, Enum):
    PLAN_INVALID = "plan_invalid"
    ASSUMPTION_BUDGET_EXHAUSTED = "assumption_budget_exhausted"
    CONCURRENCY_CONFLICT = "concurrency_conflict"
    CAPABILITY_UNAVAILABLE = "capability_unavailable"
    SCHEMA_MISMATCH = "schema_mismatch"
    COVERAGE_INCOMPLETE = "coverage_incomplete"
    SOURCE_UNAVAILABLE = "source_unavailable"
    APPLICATION_SHUTDOWN = "application_shutdown"
    INTERNAL_VALIDATION_FAILED = "internal_validation_failed"


class PlanningState(str, Enum):
    ACQUISITION_REQUIRED = "acquisition_required"
    CURRENT = "current"
    MANUAL_CATCHUP_REQUIRED = "manual_catchup_required"
    NOT_INITIALIZED = "not_initialized"


class OrchestrationState(str, Enum):
    NO_REFRESH_NEEDED = "no_refresh_needed"
    MANUAL_CATCHUP_REQUIRED = "manual_catchup_required"
    NOT_INITIALIZED = "not_initialized"
    PUBLISHED_DEMO = "published_demo"
    FAILED_RETAINED_PRIOR = "failed_retained_prior"
    CANCELLED_RETAINED_PRIOR = "cancelled_retained_prior"


class MockScenario(str, Enum):
    STALE_SUCCESS = "stale_success"
    QUOTA_ASSUMPTION_EXHAUSTED = "quota_assumption_exhausted"
    PARTIAL_FAMILY_FAILURE = "partial_family_failure"
    SCHEMA_MISMATCH = "schema_mismatch"
    COVERAGE_INCOMPLETE = "coverage_incomplete"
    SYNTHETIC_CORRECTION_REVISION = "synthetic_correction_revision"


def _freeze_json(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType(
            {str(key): _freeze_json(value[key]) for key in sorted(value, key=str)}
        )
    if isinstance(value, list):
        return tuple(_freeze_json(item) for item in value)
    if isinstance(value, tuple):
        return tuple(_freeze_json(item) for item in value)
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise TypeError(f"payload contains unsupported value type: {type(value).__name__}")


def _require_non_empty(value: str, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string")
    return value.strip()


def _require_aware(value: datetime, field_name: str) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must be timezone-aware")
    return value


def _require_sorted_unique_dates(values: tuple[date, ...], field_name: str) -> tuple[date, ...]:
    if any(not isinstance(item, date) for item in values):
        raise TypeError(f"{field_name} must contain date values")
    if tuple(sorted(set(values))) != values:
        raise ValueError(f"{field_name} must be sorted and unique")
    return values


@dataclass(frozen=True, slots=True)
class MockPlanningAssumption:
    profile_id: str = MOCK_ASSUMPTION_PROFILE_ID
    assumption_class: str = "synthetic_engineering_scenario"
    mock_qps: int = 5
    mock_concurrency: int = 2
    mock_daily_request_budget: int = 50_000
    mock_completion_after_local_time: time = time(18, 0)
    mock_timezone: str = "Asia/Shanghai"
    provider_confirmed: bool = False
    production_eligible: bool = False

    def __post_init__(self) -> None:
        reviewed_profile = (
            MOCK_ASSUMPTION_PROFILE_ID,
            "synthetic_engineering_scenario",
            5,
            2,
            50_000,
            time(18, 0),
            "Asia/Shanghai",
            False,
            False,
        )
        supplied_profile = (
            self.profile_id,
            self.assumption_class,
            self.mock_qps,
            self.mock_concurrency,
            self.mock_daily_request_budget,
            self.mock_completion_after_local_time,
            self.mock_timezone,
            self.provider_confirmed,
            self.production_eligible,
        )
        if supplied_profile != reviewed_profile:
            raise ValueError(
                "mock assumption must equal the exact reviewed synthetic profile"
            )


DEFAULT_MOCK_ASSUMPTION = MockPlanningAssumption()


@dataclass(frozen=True, slots=True)
class TodayMarketRefreshIntent:
    scope_revision_id: str
    trigger: RefreshTrigger
    prior_snapshot_id: str | None
    local_clock_utc: datetime
    planning_policy_version: str = PLANNING_POLICY_VERSION

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "scope_revision_id",
            _require_non_empty(self.scope_revision_id, "scope_revision_id"),
        )
        if self.prior_snapshot_id is not None:
            object.__setattr__(
                self,
                "prior_snapshot_id",
                _require_non_empty(self.prior_snapshot_id, "prior_snapshot_id"),
            )
        _require_aware(self.local_clock_utc, "local_clock_utc")
        _require_non_empty(self.planning_policy_version, "planning_policy_version")


@dataclass(frozen=True, slots=True)
class TodayMarketRefreshPlan:
    scope_revision_id: str
    refresh_attempt_id: str
    trigger: RefreshTrigger
    prior_snapshot_id: str | None
    requested_completed_sessions: tuple[date, ...]
    capability_set: tuple[CapabilityFamily, ...]
    family_bounds: tuple[tuple[str, int], ...]
    information_cutoff: date
    recorded_at_utc: datetime
    planning_policy_version: str
    assumption_profile_id: str
    plan_fingerprint: str

    def __post_init__(self) -> None:
        _require_non_empty(self.scope_revision_id, "scope_revision_id")
        _require_non_empty(self.refresh_attempt_id, "refresh_attempt_id")
        _require_sorted_unique_dates(
            self.requested_completed_sessions, "requested_completed_sessions"
        )
        if not self.requested_completed_sessions:
            raise ValueError("requested_completed_sessions must not be empty")
        if tuple(sorted(set(self.capability_set), key=lambda value: value.value)) != self.capability_set:
            raise ValueError("capability_set must be sorted and unique")
        if self.information_cutoff != self.requested_completed_sessions[-1]:
            raise ValueError(
                "information_cutoff must equal the latest requested session"
            )
        _require_aware(self.recorded_at_utc, "recorded_at_utc")
        if self.assumption_profile_id != MOCK_ASSUMPTION_PROFILE_ID:
            raise ValueError(
                "only the reviewed synthetic Mock assumption profile is allowed"
            )
        if len(self.plan_fingerprint) != 64:
            raise ValueError("plan_fingerprint must be a SHA-256 hex digest")

    def fingerprint_payload(self) -> Mapping[str, Any]:
        return {
            "scope_revision_id": self.scope_revision_id,
            "refresh_attempt_id": self.refresh_attempt_id,
            "trigger": self.trigger,
            "prior_snapshot_id": self.prior_snapshot_id,
            "requested_completed_sessions": self.requested_completed_sessions,
            "capability_set": self.capability_set,
            "family_bounds": self.family_bounds,
            "information_cutoff": self.information_cutoff,
            "recorded_at_utc": self.recorded_at_utc,
            "planning_policy_version": self.planning_policy_version,
            "assumption_profile_id": self.assumption_profile_id,
        }

    def verify_fingerprint(self) -> bool:
        return canonical_sha256(self.fingerprint_payload()) == self.plan_fingerprint


@dataclass(frozen=True, slots=True)
class TodayMarketSourceProvenance:
    source_key: str
    adapter_contract_version: str
    source_contract_fingerprints: tuple[str, ...]
    source_mode: SourceMode
    observed_at_utc: datetime
    provider_confirmed: bool

    def __post_init__(self) -> None:
        _require_non_empty(self.source_key, "source_key")
        _require_non_empty(self.adapter_contract_version, "adapter_contract_version")
        _require_aware(self.observed_at_utc, "observed_at_utc")
        if self.source_mode is SourceMode.SYNTHETIC_MOCK:
            if self.source_key != SYNTHETIC_SOURCE_KEY:
                raise ValueError(
                    "Mock provenance must use the dedicated synthetic source key"
                )
            if self.provider_confirmed:
                raise ValueError("Mock provenance can never be Provider-confirmed")
        for value in self.source_contract_fingerprints:
            if len(value) != 64:
                raise ValueError(
                    "source_contract_fingerprints must contain SHA-256 values"
                )


@dataclass(frozen=True, slots=True)
class TodayMarketFamilyResult:
    family_key: CapabilityFamily
    schema_version: str
    requested_sessions: tuple[date, ...]
    covered_sessions: tuple[date, ...]
    item_count: int
    synthetic: bool
    source_key: str
    content_fingerprint: str
    validation_status: ValidationStatus
    reason_codes: tuple[str, ...]
    payload: Mapping[str, Any]

    def __post_init__(self) -> None:
        _require_non_empty(self.schema_version, "schema_version")
        _require_sorted_unique_dates(self.requested_sessions, "requested_sessions")
        _require_sorted_unique_dates(self.covered_sessions, "covered_sessions")
        if self.item_count < 0:
            raise ValueError("item_count must not be negative")
        if not self.synthetic or self.source_key != SYNTHETIC_SOURCE_KEY:
            raise ValueError("Mock family results must remain explicitly synthetic")
        if len(self.content_fingerprint) != 64:
            raise ValueError("content_fingerprint must be a SHA-256 hex digest")
        object.__setattr__(self, "payload", _freeze_json(self.payload))


@dataclass(frozen=True, slots=True)
class TodayMarketCoverage:
    status: CoverageStatus
    requested_sessions: tuple[date, ...]
    covered_sessions: tuple[date, ...]
    required_families: tuple[CapabilityFamily, ...]
    complete_families: tuple[CapabilityFamily, ...]
    missing_families: tuple[CapabilityFamily, ...]
    excluded_items: tuple[str, ...]
    coverage_reason_codes: tuple[str, ...]

    def __post_init__(self) -> None:
        _require_sorted_unique_dates(self.requested_sessions, "requested_sessions")
        _require_sorted_unique_dates(self.covered_sessions, "covered_sessions")


@dataclass(frozen=True, slots=True)
class TodayMarketAcquisitionBatch:
    refresh_attempt_id: str
    scenario_or_source_attempt_id: str
    source_provenance: TodayMarketSourceProvenance
    requested_sessions: tuple[date, ...]
    data_through_session: date
    coverage: TodayMarketCoverage
    family_results: tuple[TodayMarketFamilyResult, ...]
    redacted_diagnostics: tuple[str, ...]
    batch_fingerprint: str

    def __post_init__(self) -> None:
        _require_non_empty(self.refresh_attempt_id, "refresh_attempt_id")
        _require_non_empty(
            self.scenario_or_source_attempt_id, "scenario_or_source_attempt_id"
        )
        _require_sorted_unique_dates(self.requested_sessions, "requested_sessions")
        if len(self.batch_fingerprint) != 64:
            raise ValueError("batch_fingerprint must be a SHA-256 hex digest")

    def fingerprint_payload(self) -> Mapping[str, Any]:
        return {
            "refresh_attempt_id": self.refresh_attempt_id,
            "scenario_or_source_attempt_id": self.scenario_or_source_attempt_id,
            "source_provenance": self.source_provenance,
            "requested_sessions": self.requested_sessions,
            "data_through_session": self.data_through_session,
            "coverage": self.coverage,
            "family_results": self.family_results,
            "redacted_diagnostics": self.redacted_diagnostics,
        }

    def verify_fingerprint(self) -> bool:
        return canonical_sha256(self.fingerprint_payload()) == self.batch_fingerprint


@dataclass(frozen=True, slots=True)
class TodayMarketAcquisitionFailure:
    failure_code: str
    category: FailureCategory
    refresh_attempt_id: str
    source_key: str | None
    redacted_details: tuple[str, ...]
    retryability: Retryability

    def __post_init__(self) -> None:
        _require_non_empty(self.failure_code, "failure_code")
        _require_non_empty(self.refresh_attempt_id, "refresh_attempt_id")


class TodayMarketAcquisitionError(RuntimeError):
    def __init__(self, failure: TodayMarketAcquisitionFailure) -> None:
        super().__init__(failure.failure_code)
        self.failure = failure


@dataclass(frozen=True, slots=True)
class SnapshotReference:
    snapshot_id: str
    data_through_session: date
    content_fingerprint: str

    def __post_init__(self) -> None:
        _require_non_empty(self.snapshot_id, "snapshot_id")
        if len(self.content_fingerprint) != 64:
            raise ValueError("content_fingerprint must be a SHA-256 hex digest")


@dataclass(frozen=True, slots=True)
class RefreshPlanningDecision:
    state: PlanningState
    plan: TodayMarketRefreshPlan | None
    missing_sessions: tuple[date, ...]
    message_zh: str


@dataclass(frozen=True, slots=True)
class TodayMarketDemoProjection:
    projection_version: str
    is_synthetic: bool
    source_label: str
    production_live_source_ready: bool
    overall_live_gate: str
    message_zh: str
    data_through_session: date
    family_item_counts: tuple[tuple[str, int], ...]
    projection_fingerprint: str


@dataclass(frozen=True, slots=True)
class TodayMarketRefreshOutcome:
    state: OrchestrationState
    prior_snapshot: SnapshotReference | None
    candidate_projection: TodayMarketDemoProjection | None
    plan: TodayMarketRefreshPlan | None
    failure: TodayMarketAcquisitionFailure | None
    message_zh: str
