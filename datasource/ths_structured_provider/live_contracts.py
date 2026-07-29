"""Secret-free live source policy for Today Market daily-market acquisition.

This module freezes only reviewed/public source facts and the explicit project-owner
provisional assumptions accepted by Issue #272. It performs no credential lookup,
network access, persistence, endpoint discovery, or runtime activation.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from types import MappingProxyType
from typing import Mapping

from .contracts import SOURCE_KEY
from .fingerprint import canonical_sha256

LIVE_SOURCE_POLICY_VERSION = "aquantai.ths-daily-market-live-source-policy.v1"
PROVIDER_PRODUCT_NAME = "THS / iFinD Data Interface"
PRIMARY_HTTPS_HOST = "quantapi.51ifind.com"
BACKUP_HTTPS_HOST = "ft.10jqka.com.cn"
AUTHENTICATION_REFERENCE_TYPE = "runtime_credential_reference"
RETENTION_POLICY_BASIS = "project_owner_provisional_assumption_2026_07_28"
PUBLIC_FIXTURE_POLICY = "synthetic_only"
COMPLETION_TIMEZONE = "Asia/Shanghai"
A_SHARE_DAILY_COMPLETION_REFERENCE = "around_15_07_local_time"
HISTORICAL_QUERY_YEARS = 10
PER_FUNCTION_QPS = 10
ACCOUNT_TOTAL_QPS = 20


class DailyMarketCapability(str, Enum):
    """Closed source capabilities eligible for Slice A planning."""

    LISTED_INSTRUMENT_IDENTITY = "listed_instrument_identity"
    TRADING_CALENDAR = "trading_calendar"
    A_SHARE_DAILY_RAW = "a_share_daily_raw"
    A_SHARE_DAILY_ADJUSTED = "a_share_daily_adjusted"
    BENCHMARK_INDEX_DAILY = "benchmark_index_daily"
    HISTORICAL_BLOCK_SNAPSHOT = "historical_block_snapshot"


FOUNDATION_REQUIRED_CAPABILITIES = (
    DailyMarketCapability.A_SHARE_DAILY_RAW,
    DailyMarketCapability.BENCHMARK_INDEX_DAILY,
    DailyMarketCapability.LISTED_INSTRUMENT_IDENTITY,
    DailyMarketCapability.TRADING_CALENDAR,
)
OPTIONAL_FAIL_CLOSED_CAPABILITIES = (
    DailyMarketCapability.A_SHARE_DAILY_ADJUSTED,
    DailyMarketCapability.HISTORICAL_BLOCK_SNAPSHOT,
)


class EvidenceBasis(str, Enum):
    """How one readiness fact became usable by this project."""

    PROVIDER_PUBLIC_DOCUMENTATION = "provider_public_documentation"
    PROJECT_OWNER_PROVISIONAL_ASSUMPTION = "project_owner_provisional_assumption"
    FAIL_CLOSED_AT_REQUEST = "fail_closed_at_request"


class ReadinessDisposition(str, Enum):
    """Closed readiness state used without inferring Provider meaning."""

    CONFIRMED = "confirmed"
    PROVISIONAL = "provisional"
    VALIDATE_PER_REQUEST = "validate_per_request"
    DISABLED = "disabled"


@dataclass(frozen=True, slots=True)
class ReadinessFact:
    fact_key: str
    disposition: ReadinessDisposition
    evidence_basis: EvidenceBasis
    detail: str

    def __post_init__(self) -> None:
        if not isinstance(self.fact_key, str) or not self.fact_key.strip():
            raise ValueError("fact_key must be a non-empty string")
        if not isinstance(self.detail, str) or not self.detail.strip():
            raise ValueError("detail must be a non-empty string")

    def fingerprint_payload(self) -> dict[str, str]:
        return {
            "fact_key": self.fact_key,
            "disposition": self.disposition.value,
            "evidence_basis": self.evidence_basis.value,
            "detail": self.detail,
        }


@dataclass(frozen=True, slots=True)
class LiveDailyMarketSourcePolicy:
    """Exact, immutable Slice A source policy.

    The constructor is deliberately closed to the reviewed v1 profile. Callers may
    select capabilities and dates later, but may not replace hosts, quota, retention,
    history, authentication, or activation semantics through runtime dictionaries.
    """

    policy_version: str = LIVE_SOURCE_POLICY_VERSION
    source_key: str = SOURCE_KEY
    provider_product_name: str = PROVIDER_PRODUCT_NAME
    authorized_https_hosts: tuple[str, ...] = (PRIMARY_HTTPS_HOST, BACKUP_HTTPS_HOST)
    authentication_reference_type: str = AUTHENTICATION_REFERENCE_TYPE
    per_function_qps: int = PER_FUNCTION_QPS
    account_total_qps: int = ACCOUNT_TOTAL_QPS
    historical_query_years: int = HISTORICAL_QUERY_YEARS
    completion_timezone: str = COMPLETION_TIMEZONE
    a_share_daily_completion_reference: str = A_SHARE_DAILY_COMPLETION_REFERENCE
    retention_policy_basis: str = RETENTION_POLICY_BASIS
    private_local_retention: str = "indefinite_for_project_use"
    public_fixture_policy: str = PUBLIC_FIXTURE_POLICY
    remote_execution_default: bool = False
    runtime_provider_fallback: bool = False
    cross_provider_row_mixing: bool = False

    def __post_init__(self) -> None:
        reviewed_profile = (
            LIVE_SOURCE_POLICY_VERSION,
            SOURCE_KEY,
            PROVIDER_PRODUCT_NAME,
            (PRIMARY_HTTPS_HOST, BACKUP_HTTPS_HOST),
            AUTHENTICATION_REFERENCE_TYPE,
            PER_FUNCTION_QPS,
            ACCOUNT_TOTAL_QPS,
            HISTORICAL_QUERY_YEARS,
            COMPLETION_TIMEZONE,
            A_SHARE_DAILY_COMPLETION_REFERENCE,
            RETENTION_POLICY_BASIS,
            "indefinite_for_project_use",
            PUBLIC_FIXTURE_POLICY,
            False,
            False,
            False,
        )
        supplied_profile = (
            self.policy_version,
            self.source_key,
            self.provider_product_name,
            self.authorized_https_hosts,
            self.authentication_reference_type,
            self.per_function_qps,
            self.account_total_qps,
            self.historical_query_years,
            self.completion_timezone,
            self.a_share_daily_completion_reference,
            self.retention_policy_basis,
            self.private_local_retention,
            self.public_fixture_policy,
            self.remote_execution_default,
            self.runtime_provider_fallback,
            self.cross_provider_row_mixing,
        )
        if supplied_profile != reviewed_profile:
            raise ValueError("live source policy must equal the exact reviewed Slice A v1 profile")

    def fingerprint_payload(self) -> dict[str, object]:
        return {
            "policy_version": self.policy_version,
            "source_key": self.source_key,
            "provider_product_name": self.provider_product_name,
            "authorized_https_hosts": self.authorized_https_hosts,
            "authentication_reference_type": self.authentication_reference_type,
            "per_function_qps": self.per_function_qps,
            "account_total_qps": self.account_total_qps,
            "historical_query_years": self.historical_query_years,
            "completion_timezone": self.completion_timezone,
            "a_share_daily_completion_reference": self.a_share_daily_completion_reference,
            "retention_policy_basis": self.retention_policy_basis,
            "private_local_retention": self.private_local_retention,
            "public_fixture_policy": self.public_fixture_policy,
            "remote_execution_default": self.remote_execution_default,
            "runtime_provider_fallback": self.runtime_provider_fallback,
            "cross_provider_row_mixing": self.cross_provider_row_mixing,
        }

    @property
    def policy_fingerprint(self) -> str:
        return canonical_sha256(self.fingerprint_payload())

    def assert_authorized_host(self, host: str) -> str:
        if not isinstance(host, str) or not host.strip():
            raise ValueError("host must be a non-empty string")
        normalized = host.strip().lower()
        if normalized not in self.authorized_https_hosts:
            raise ValueError("host is outside the reviewed THS/iFinD host family")
        return normalized

    def assert_capability(self, capability: DailyMarketCapability) -> DailyMarketCapability:
        if not isinstance(capability, DailyMarketCapability):
            raise TypeError("capability must be a DailyMarketCapability")
        return capability


DEFAULT_LIVE_SOURCE_POLICY = LiveDailyMarketSourcePolicy()


_READINESS_FACTS = (
    ReadinessFact(
        fact_key="source_selection",
        disposition=ReadinessDisposition.CONFIRMED,
        evidence_basis=EvidenceBasis.PROVIDER_PUBLIC_DOCUMENTATION,
        detail="one explicit THS/iFinD source authority; no runtime fallback",
    ),
    ReadinessFact(
        fact_key="quota_and_qps",
        disposition=ReadinessDisposition.CONFIRMED,
        evidence_basis=EvidenceBasis.PROVIDER_PUBLIC_DOCUMENTATION,
        detail="per-function QPS 10 and account-total QPS 20",
    ),
    ReadinessFact(
        fact_key="credential_lifecycle_boundary",
        disposition=ReadinessDisposition.CONFIRMED,
        evidence_basis=EvidenceBasis.PROVIDER_PUBLIC_DOCUMENTATION,
        detail="runtime credential reference only; credential values are never contract data",
    ),
    ReadinessFact(
        fact_key="a_share_daily_completion_reference",
        disposition=ReadinessDisposition.CONFIRMED,
        evidence_basis=EvidenceBasis.PROVIDER_PUBLIC_DOCUMENTATION,
        detail="A-share daily data reference around 15:07 Asia/Shanghai",
    ),
    ReadinessFact(
        fact_key="private_local_retention",
        disposition=ReadinessDisposition.PROVISIONAL,
        evidence_basis=EvidenceBasis.PROJECT_OWNER_PROVISIONAL_ASSUMPTION,
        detail="private local project data may be retained indefinitely",
    ),
    ReadinessFact(
        fact_key="historical_query_horizon",
        disposition=ReadinessDisposition.PROVISIONAL,
        evidence_basis=EvidenceBasis.PROJECT_OWNER_PROVISIONAL_ASSUMPTION,
        detail="Provider historical acquisition is bounded to a rolling ten-year horizon",
    ),
    ReadinessFact(
        fact_key="historical_taxonomy_date",
        disposition=ReadinessDisposition.VALIDATE_PER_REQUEST,
        evidence_basis=EvidenceBasis.FAIL_CLOSED_AT_REQUEST,
        detail="unsupported or unknown taxonomy/date pairs are unavailable and never backfilled",
    ),
    ReadinessFact(
        fact_key="remote_execution",
        disposition=ReadinessDisposition.DISABLED,
        evidence_basis=EvidenceBasis.FAIL_CLOSED_AT_REQUEST,
        detail="transport remains disabled unless later explicit runtime configuration is valid",
    ),
)

LIVE_READINESS_FACTS: tuple[ReadinessFact, ...] = tuple(
    sorted(_READINESS_FACTS, key=lambda fact: fact.fact_key)
)
LIVE_READINESS_BY_KEY: Mapping[str, ReadinessFact] = MappingProxyType(
    {fact.fact_key: fact for fact in LIVE_READINESS_FACTS}
)


def readiness_fingerprint() -> str:
    """Return a deterministic fingerprint over secret-free readiness facts."""

    return canonical_sha256(tuple(fact.fingerprint_payload() for fact in LIVE_READINESS_FACTS))


def public_contract_snapshot() -> Mapping[str, object]:
    """Expose immutable, secret-free contract metadata for diagnostics/tests."""

    snapshot = {
        "source_policy": DEFAULT_LIVE_SOURCE_POLICY.fingerprint_payload(),
        "source_policy_fingerprint": DEFAULT_LIVE_SOURCE_POLICY.policy_fingerprint,
        "readiness_facts": tuple(fact.fingerprint_payload() for fact in LIVE_READINESS_FACTS),
        "readiness_fingerprint": readiness_fingerprint(),
        "required_capabilities": tuple(value.value for value in FOUNDATION_REQUIRED_CAPABILITIES),
        "optional_fail_closed_capabilities": tuple(
            value.value for value in OPTIONAL_FAIL_CLOSED_CAPABILITIES
        ),
    }
    return MappingProxyType(snapshot)
