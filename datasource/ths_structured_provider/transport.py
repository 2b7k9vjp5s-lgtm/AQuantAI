"""Default-disabled THS transport boundary for reviewed daily-market operations.

The module contains no concrete network client. A runtime-specific executor must be injected
explicitly. This keeps normal imports, tests, demos, and CI zero-network while freezing host,
operation, timeout, credential, retry, and failure semantics for a later local live adapter.
"""

from __future__ import annotations

import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from types import MappingProxyType
from typing import Protocol, runtime_checkable

from .credentials import (
    CredentialReference,
    CredentialResolver,
    CredentialResolutionError,
    resolve_runtime_credential,
)
from .fingerprint import canonical_sha256
from .live_contracts import (
    DEFAULT_LIVE_SOURCE_POLICY,
    PRIMARY_HTTPS_HOST,
    DailyMarketCapability,
    LiveDailyMarketSourcePolicy,
)
from .live_planner import DailyMarketRequestPlan

THS_TRANSPORT_POLICY_VERSION = "aquantai.ths-daily-market-transport.v1"
EXPECTED_PLANNING_MAPPING_STATUS = "deferred_to_m4_reviewed_mapping"


class TransportFailureCode(str, Enum):
    REMOTE_EXECUTION_DISABLED = "THS_TRANSPORT_REMOTE_EXECUTION_DISABLED"
    POLICY_MISMATCH = "THS_TRANSPORT_POLICY_MISMATCH"
    HOST_NOT_AUTHORIZED = "THS_TRANSPORT_HOST_NOT_AUTHORIZED"
    OPERATION_NOT_AUTHORIZED = "THS_TRANSPORT_OPERATION_NOT_AUTHORIZED"
    CREDENTIAL_UNAVAILABLE = "THS_TRANSPORT_CREDENTIAL_UNAVAILABLE"
    AUTHENTICATION_FAILED = "THS_TRANSPORT_AUTHENTICATION_FAILED"
    RATE_LIMITED = "THS_TRANSPORT_RATE_LIMITED"
    TIMEOUT = "THS_TRANSPORT_TIMEOUT"
    PROVIDER_UNAVAILABLE = "THS_TRANSPORT_PROVIDER_UNAVAILABLE"
    INVALID_EXECUTOR_RESPONSE = "THS_TRANSPORT_INVALID_EXECUTOR_RESPONSE"


class TransportExecutionError(RuntimeError):
    def __init__(self, message: str, reason_code: TransportFailureCode) -> None:
        self.reason_code = reason_code
        super().__init__(message)


class ExecutorAuthenticationError(RuntimeError):
    """Executor reports a rejected or expired Provider credential."""


class ExecutorRateLimitError(RuntimeError):
    """Executor reports Provider quota or QPS rejection."""


class ExecutorTimeoutError(RuntimeError):
    """Executor reports one bounded request timeout."""


class ExecutorTransientError(RuntimeError):
    """Executor reports one retryable Provider/service failure."""


@dataclass(frozen=True, slots=True)
class TransportOperationContract:
    capability: DailyMarketCapability
    operation_key: str
    executor_operation: str
    response_schema_version: str
    host: str = PRIMARY_HTTPS_HOST
    planning_mapping_status: str = EXPECTED_PLANNING_MAPPING_STATUS

    def __post_init__(self) -> None:
        if not isinstance(self.capability, DailyMarketCapability):
            raise ValueError("transport capability must be a DailyMarketCapability")
        if not self.operation_key or not self.executor_operation:
            raise ValueError("transport operation identifiers must not be empty")
        if self.planning_mapping_status != EXPECTED_PLANNING_MAPPING_STATUS:
            raise ValueError("transport contract must bind the reviewed M4 mapping status")
        DEFAULT_LIVE_SOURCE_POLICY.assert_authorized_host(self.host)

    def fingerprint_payload(self) -> dict[str, str]:
        return {
            "capability": self.capability.value,
            "operation_key": self.operation_key,
            "executor_operation": self.executor_operation,
            "response_schema_version": self.response_schema_version,
            "host": self.host,
            "planning_mapping_status": self.planning_mapping_status,
        }

    @property
    def contract_fingerprint(self) -> str:
        return canonical_sha256(self.fingerprint_payload())


_OPERATION_CONTRACTS = (
    TransportOperationContract(
        capability=DailyMarketCapability.LISTED_INSTRUMENT_IDENTITY,
        operation_key="ths.daily-market.listed-instrument-identity.v1",
        executor_operation="listed_instrument_identity",
        response_schema_version="aquantai.ths-listed-instrument-response.v1",
    ),
    TransportOperationContract(
        capability=DailyMarketCapability.TRADING_CALENDAR,
        operation_key="ths.daily-market.trading-calendar.v1",
        executor_operation="trading_calendar",
        response_schema_version="aquantai.ths-trading-calendar-response.v1",
    ),
    TransportOperationContract(
        capability=DailyMarketCapability.A_SHARE_DAILY_RAW,
        operation_key="ths.daily-market.a-share-daily-raw.v1",
        executor_operation="a_share_daily_raw",
        response_schema_version="aquantai.ths-a-share-daily-response.v1",
    ),
    TransportOperationContract(
        capability=DailyMarketCapability.A_SHARE_DAILY_ADJUSTED,
        operation_key="ths.daily-market.a-share-daily-adjusted.v1",
        executor_operation="a_share_daily_adjusted",
        response_schema_version="aquantai.ths-a-share-daily-response.v1",
    ),
    TransportOperationContract(
        capability=DailyMarketCapability.BENCHMARK_INDEX_DAILY,
        operation_key="ths.daily-market.benchmark-index-daily.v1",
        executor_operation="benchmark_index_daily",
        response_schema_version="aquantai.ths-benchmark-daily-response.v1",
    ),
)
TRANSPORT_OPERATION_REGISTRY: Mapping[str, TransportOperationContract] = MappingProxyType(
    {contract.operation_key: contract for contract in _OPERATION_CONTRACTS}
)


@dataclass(frozen=True, slots=True)
class TransportExecutionConfig:
    enabled: bool = False
    host: str = PRIMARY_HTTPS_HOST
    timeout_seconds: float = 20.0
    max_attempts: int = 1
    retry_delay_seconds: float = 0.0

    def __post_init__(self) -> None:
        if not isinstance(self.enabled, bool):
            raise ValueError("transport enabled must be boolean")
        DEFAULT_LIVE_SOURCE_POLICY.assert_authorized_host(self.host)
        if isinstance(self.timeout_seconds, bool) or not 0 < float(self.timeout_seconds) <= 120:
            raise ValueError("timeout_seconds must be in (0, 120]")
        if isinstance(self.max_attempts, bool) or not isinstance(self.max_attempts, int):
            raise ValueError("max_attempts must be an integer")
        if not 1 <= self.max_attempts <= 3:
            raise ValueError("max_attempts must be between 1 and 3")
        if isinstance(self.retry_delay_seconds, bool) or not 0 <= float(self.retry_delay_seconds) <= 5:
            raise ValueError("retry_delay_seconds must be in [0, 5]")

    def fingerprint_payload(self) -> dict[str, object]:
        return {
            "transport_policy_version": THS_TRANSPORT_POLICY_VERSION,
            "enabled": self.enabled,
            "host": self.host,
            "timeout_seconds": float(self.timeout_seconds),
            "max_attempts": self.max_attempts,
            "retry_delay_seconds": float(self.retry_delay_seconds),
        }

    @property
    def config_fingerprint(self) -> str:
        return canonical_sha256(self.fingerprint_payload())


@dataclass(frozen=True, slots=True)
class TransportOperationRequest:
    transport_policy_version: str
    host: str
    executor_operation: str
    operation_key: str
    capability: DailyMarketCapability
    ordered_parameters: tuple[tuple[str, str], ...]
    request_fingerprint: str
    plan_fingerprint: str
    operation_contract_fingerprint: str
    credential_reference_fingerprint: str
    timeout_seconds: float

    def safe_payload(self) -> dict[str, object]:
        return {
            "transport_policy_version": self.transport_policy_version,
            "host": self.host,
            "executor_operation": self.executor_operation,
            "operation_key": self.operation_key,
            "capability": self.capability.value,
            "ordered_parameters": self.ordered_parameters,
            "request_fingerprint": self.request_fingerprint,
            "plan_fingerprint": self.plan_fingerprint,
            "operation_contract_fingerprint": self.operation_contract_fingerprint,
            "credential_reference_fingerprint": self.credential_reference_fingerprint,
            "timeout_seconds": self.timeout_seconds,
        }


@dataclass(frozen=True, slots=True)
class TransportExecutionResult:
    request: TransportOperationRequest
    response_payload: Mapping[str, object]
    attempts: int

    def public_summary(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                **self.request.safe_payload(),
                "attempts": self.attempts,
                "response_payload_fingerprint": canonical_sha256(dict(self.response_payload)),
            }
        )


@runtime_checkable
class ThsOperationExecutor(Protocol):
    def execute(
        self,
        request: TransportOperationRequest,
        *,
        credential_value: str,
    ) -> Mapping[str, object]:
        """Execute one reviewed logical THS operation."""


def build_transport_request(
    plan: DailyMarketRequestPlan,
    credential_reference: CredentialReference,
    config: TransportExecutionConfig,
    *,
    policy: LiveDailyMarketSourcePolicy = DEFAULT_LIVE_SOURCE_POLICY,
) -> TransportOperationRequest:
    if policy != DEFAULT_LIVE_SOURCE_POLICY:
        raise TransportExecutionError(
            "transport requires the exact reviewed source policy",
            TransportFailureCode.POLICY_MISMATCH,
        )
    if not isinstance(plan, DailyMarketRequestPlan):
        raise TransportExecutionError(
            "transport requires a DailyMarketRequestPlan",
            TransportFailureCode.POLICY_MISMATCH,
        )
    if plan.source_key != policy.source_key or plan.source_policy_fingerprint != policy.policy_fingerprint:
        raise TransportExecutionError(
            "request plan does not match the reviewed source policy",
            TransportFailureCode.POLICY_MISMATCH,
        )
    if plan.transport_mapping_status != EXPECTED_PLANNING_MAPPING_STATUS:
        raise TransportExecutionError(
            "request plan transport mapping status is not reviewed",
            TransportFailureCode.POLICY_MISMATCH,
        )
    try:
        contract = TRANSPORT_OPERATION_REGISTRY[plan.operation_key]
    except KeyError as exc:
        raise TransportExecutionError(
            "request plan operation is not authorized for live transport",
            TransportFailureCode.OPERATION_NOT_AUTHORIZED,
        ) from exc
    if contract.capability is not plan.capability:
        raise TransportExecutionError(
            "request plan capability does not match its transport operation",
            TransportFailureCode.POLICY_MISMATCH,
        )
    normalized_host = policy.assert_authorized_host(config.host)
    if normalized_host != contract.host:
        raise TransportExecutionError(
            "configured host does not match the reviewed operation contract",
            TransportFailureCode.HOST_NOT_AUTHORIZED,
        )
    return TransportOperationRequest(
        transport_policy_version=THS_TRANSPORT_POLICY_VERSION,
        host=normalized_host,
        executor_operation=contract.executor_operation,
        operation_key=contract.operation_key,
        capability=contract.capability,
        ordered_parameters=plan.ordered_parameters,
        request_fingerprint=plan.request_fingerprint,
        plan_fingerprint=plan.plan_fingerprint,
        operation_contract_fingerprint=contract.contract_fingerprint,
        credential_reference_fingerprint=credential_reference.reference_fingerprint,
        timeout_seconds=float(config.timeout_seconds),
    )


class ThsDailyMarketTransport:
    """Execute one logical plan through an injected executor with bounded retries."""

    def __init__(
        self,
        *,
        credential_resolver: CredentialResolver,
        executor: ThsOperationExecutor,
        config: TransportExecutionConfig | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        if not isinstance(credential_resolver, CredentialResolver):
            raise TypeError("credential_resolver must implement CredentialResolver")
        if not isinstance(executor, ThsOperationExecutor):
            raise TypeError("executor must implement ThsOperationExecutor")
        self._credential_resolver = credential_resolver
        self._executor = executor
        self.config = config or TransportExecutionConfig()
        self._sleep = sleep

    def execute(
        self,
        plan: DailyMarketRequestPlan,
        credential_reference: CredentialReference,
        *,
        now: datetime,
    ) -> TransportExecutionResult:
        if not self.config.enabled:
            raise TransportExecutionError(
                "remote THS transport is disabled by default",
                TransportFailureCode.REMOTE_EXECUTION_DISABLED,
            )
        request = build_transport_request(plan, credential_reference, self.config)
        try:
            credential = resolve_runtime_credential(
                credential_reference,
                self._credential_resolver,
                now=now,
            )
        except CredentialResolutionError as exc:
            raise TransportExecutionError(
                "runtime credential is unavailable",
                TransportFailureCode.CREDENTIAL_UNAVAILABLE,
            ) from exc

        for attempt in range(1, self.config.max_attempts + 1):
            try:
                payload = self._executor.execute(
                    request,
                    credential_value=credential.reveal_for_transport(),
                )
                if not isinstance(payload, Mapping):
                    raise TransportExecutionError(
                        "transport executor returned a non-mapping payload",
                        TransportFailureCode.INVALID_EXECUTOR_RESPONSE,
                    )
                return TransportExecutionResult(
                    request=request,
                    response_payload=MappingProxyType(dict(payload)),
                    attempts=attempt,
                )
            except ExecutorAuthenticationError as exc:
                raise TransportExecutionError(
                    "THS authentication was rejected",
                    TransportFailureCode.AUTHENTICATION_FAILED,
                ) from exc
            except ExecutorRateLimitError as exc:
                raise TransportExecutionError(
                    "THS quota or QPS limit rejected the request",
                    TransportFailureCode.RATE_LIMITED,
                ) from exc
            except ExecutorTimeoutError as exc:
                if attempt >= self.config.max_attempts:
                    raise TransportExecutionError(
                        "THS request exceeded the bounded timeout",
                        TransportFailureCode.TIMEOUT,
                    ) from exc
            except ExecutorTransientError as exc:
                if attempt >= self.config.max_attempts:
                    raise TransportExecutionError(
                        "THS service remained unavailable after bounded attempts",
                        TransportFailureCode.PROVIDER_UNAVAILABLE,
                    ) from exc
            except TransportExecutionError:
                raise
            except Exception as exc:
                raise TransportExecutionError(
                    "THS executor failed without exposing Provider details",
                    TransportFailureCode.PROVIDER_UNAVAILABLE,
                ) from exc
            if self.config.retry_delay_seconds:
                self._sleep(float(self.config.retry_delay_seconds))

        raise AssertionError("bounded transport loop ended without a result or typed failure")
