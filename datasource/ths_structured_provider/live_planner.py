"""Deterministic, credential-free request planning for THS daily-market Slice A."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from types import MappingProxyType
from typing import Mapping

from .fingerprint import canonical_sha256
from .live_contracts import (
    DEFAULT_LIVE_SOURCE_POLICY,
    DailyMarketCapability,
    LiveDailyMarketSourcePolicy,
)
from .live_selectors import (
    AShareDailySelector,
    BenchmarkDailySelector,
    HistoricalBlockSnapshotSelector,
    ListedInstrumentSelector,
    LiveDailyMarketSelector,
    TradingCalendarSelector,
)


LIVE_PLANNING_POLICY_VERSION = "aquantai.ths-daily-market-request-planning.v1"


class RequestPlanningFailureCode(str, Enum):
    POLICY_MISMATCH = "THS_DAILY_MARKET_POLICY_MISMATCH"
    UNSUPPORTED_CAPABILITY = "THS_DAILY_MARKET_UNSUPPORTED_CAPABILITY"
    CALL_BUDGET_EXCEEDED = "THS_DAILY_MARKET_CALL_BUDGET_EXCEEDED"
    CELL_BUDGET_EXCEEDED = "THS_DAILY_MARKET_CELL_BUDGET_EXCEEDED"
    QPS_BUDGET_INVALID = "THS_DAILY_MARKET_QPS_BUDGET_INVALID"


class RequestPlanningError(ValueError):
    def __init__(self, message: str, reason_code: RequestPlanningFailureCode) -> None:
        self.reason_code = reason_code
        super().__init__(message)


class CallCountStrategy(str, Enum):
    ONE_LOGICAL_REQUEST = "one_logical_request"
    ONE_REQUEST_PER_IDENTITY = "one_request_per_identity"


@dataclass(frozen=True, slots=True)
class CapabilityPlanningContract:
    capability: DailyMarketCapability
    operation_key: str
    selector_schema_version: str
    response_schema_version: str
    field_count_for_budget: int
    call_count_strategy: CallCountStrategy
    persistence_owner: str
    transport_mapping_status: str = "deferred_to_m4_reviewed_mapping"

    def __post_init__(self) -> None:
        if not isinstance(self.capability, DailyMarketCapability):
            raise ValueError("capability must be a DailyMarketCapability")
        if not self.operation_key:
            raise ValueError("operation_key must not be empty")
        if self.field_count_for_budget <= 0:
            raise ValueError("field_count_for_budget must be positive")
        if not isinstance(self.call_count_strategy, CallCountStrategy):
            raise ValueError("call_count_strategy must be a CallCountStrategy")
        if self.transport_mapping_status != "deferred_to_m4_reviewed_mapping":
            raise ValueError("transport mapping must remain deferred during M2")

    def fingerprint_payload(self) -> dict[str, object]:
        return {
            "capability": self.capability.value,
            "operation_key": self.operation_key,
            "selector_schema_version": self.selector_schema_version,
            "response_schema_version": self.response_schema_version,
            "field_count_for_budget": self.field_count_for_budget,
            "call_count_strategy": self.call_count_strategy.value,
            "persistence_owner": self.persistence_owner,
            "transport_mapping_status": self.transport_mapping_status,
        }

    @property
    def contract_fingerprint(self) -> str:
        return canonical_sha256(self.fingerprint_payload())


_CAPABILITY_CONTRACTS = (
    CapabilityPlanningContract(
        capability=DailyMarketCapability.LISTED_INSTRUMENT_IDENTITY,
        operation_key="ths.daily-market.listed-instrument-identity.v1",
        selector_schema_version="aquantai.ths-listed-instrument-selector.v1",
        response_schema_version="aquantai.ths-listed-instrument-response.v1",
        field_count_for_budget=6,
        call_count_strategy=CallCountStrategy.ONE_LOGICAL_REQUEST,
        persistence_owner="StockBasicRecord",
    ),
    CapabilityPlanningContract(
        capability=DailyMarketCapability.TRADING_CALENDAR,
        operation_key="ths.daily-market.trading-calendar.v1",
        selector_schema_version="aquantai.ths-trading-calendar-selector.v1",
        response_schema_version="aquantai.ths-trading-calendar-response.v1",
        field_count_for_budget=3,
        call_count_strategy=CallCountStrategy.ONE_LOGICAL_REQUEST,
        persistence_owner="TradeCalendarRecord",
    ),
    CapabilityPlanningContract(
        capability=DailyMarketCapability.A_SHARE_DAILY_RAW,
        operation_key="ths.daily-market.a-share-daily-raw.v1",
        selector_schema_version="aquantai.ths-a-share-daily-selector.v1",
        response_schema_version="aquantai.ths-a-share-daily-response.v1",
        field_count_for_budget=11,
        call_count_strategy=CallCountStrategy.ONE_REQUEST_PER_IDENTITY,
        persistence_owner="DailyPriceRecord.adjust_type=raw",
    ),
    CapabilityPlanningContract(
        capability=DailyMarketCapability.A_SHARE_DAILY_ADJUSTED,
        operation_key="ths.daily-market.a-share-daily-adjusted.v1",
        selector_schema_version="aquantai.ths-a-share-daily-selector.v1",
        response_schema_version="aquantai.ths-a-share-daily-response.v1",
        field_count_for_budget=11,
        call_count_strategy=CallCountStrategy.ONE_REQUEST_PER_IDENTITY,
        persistence_owner="DailyPriceRecord.adjust_type=qfq|hfq",
    ),
    CapabilityPlanningContract(
        capability=DailyMarketCapability.BENCHMARK_INDEX_DAILY,
        operation_key="ths.daily-market.benchmark-index-daily.v1",
        selector_schema_version="aquantai.ths-benchmark-daily-selector.v1",
        response_schema_version="aquantai.ths-benchmark-daily-response.v1",
        field_count_for_budget=10,
        call_count_strategy=CallCountStrategy.ONE_REQUEST_PER_IDENTITY,
        persistence_owner="BenchmarkIndexDailyRecord",
    ),
    CapabilityPlanningContract(
        capability=DailyMarketCapability.HISTORICAL_BLOCK_SNAPSHOT,
        operation_key="ths.daily-market.historical-block-snapshot.v1",
        selector_schema_version="aquantai.ths-historical-block-snapshot-selector.v1",
        response_schema_version="unavailable_until_exact_taxonomy_schema_review",
        field_count_for_budget=4,
        call_count_strategy=CallCountStrategy.ONE_LOGICAL_REQUEST,
        persistence_owner="none_validation_only",
    ),
)
CAPABILITY_PLANNING_REGISTRY: Mapping[
    DailyMarketCapability, CapabilityPlanningContract
] = MappingProxyType({item.capability: item for item in _CAPABILITY_CONTRACTS})


@dataclass(frozen=True, slots=True)
class AcquisitionQuotaBudget:
    """Explicit, secret-free request budget snapshot.

    The caller owns the budget revision. No account identifier, credential, plan
    name, or pricing information is accepted.
    """

    budget_revision_id: str
    remaining_calls: int
    remaining_cells: int
    per_function_qps: int
    account_total_qps: int

    def __post_init__(self) -> None:
        if not isinstance(self.budget_revision_id, str) or not self.budget_revision_id.strip():
            raise RequestPlanningError(
                "budget_revision_id must be a non-empty string",
                RequestPlanningFailureCode.QPS_BUDGET_INVALID,
            )
        for field_name, value in (
            ("remaining_calls", self.remaining_calls),
            ("remaining_cells", self.remaining_cells),
            ("per_function_qps", self.per_function_qps),
            ("account_total_qps", self.account_total_qps),
        ):
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise RequestPlanningError(
                    f"{field_name} must be a non-negative integer",
                    RequestPlanningFailureCode.QPS_BUDGET_INVALID,
                )

    def assert_compatible(self, policy: LiveDailyMarketSourcePolicy) -> None:
        if self.per_function_qps > policy.per_function_qps:
            raise RequestPlanningError(
                "per_function_qps exceeds the reviewed source policy",
                RequestPlanningFailureCode.QPS_BUDGET_INVALID,
            )
        if self.account_total_qps > policy.account_total_qps:
            raise RequestPlanningError(
                "account_total_qps exceeds the reviewed source policy",
                RequestPlanningFailureCode.QPS_BUDGET_INVALID,
            )

    def fingerprint_payload(self) -> dict[str, object]:
        return {
            "budget_revision_id": self.budget_revision_id,
            "remaining_calls": self.remaining_calls,
            "remaining_cells": self.remaining_cells,
            "per_function_qps": self.per_function_qps,
            "account_total_qps": self.account_total_qps,
        }

    @property
    def budget_fingerprint(self) -> str:
        return canonical_sha256(self.fingerprint_payload())


@dataclass(frozen=True, slots=True)
class DailyMarketRequestPlan:
    planning_policy_version: str
    source_key: str
    source_policy_fingerprint: str
    capability: DailyMarketCapability
    operation_key: str
    capability_contract_fingerprint: str
    selector_schema_version: str
    selector_fingerprint: str
    ordered_parameters: tuple[tuple[str, str], ...]
    requested_sessions: tuple[str, ...]
    item_count: int
    estimated_cells: int
    planned_calls: int
    budget_revision_id: str
    budget_fingerprint: str
    request_fingerprint: str
    plan_fingerprint: str
    transport_mapping_status: str
    remote_executable: bool = False

    def public_summary(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "planning_policy_version": self.planning_policy_version,
                "source_key": self.source_key,
                "source_policy_fingerprint": self.source_policy_fingerprint,
                "capability": self.capability.value,
                "operation_key": self.operation_key,
                "capability_contract_fingerprint": self.capability_contract_fingerprint,
                "selector_schema_version": self.selector_schema_version,
                "selector_fingerprint": self.selector_fingerprint,
                "ordered_parameters": self.ordered_parameters,
                "requested_sessions": self.requested_sessions,
                "item_count": self.item_count,
                "estimated_cells": self.estimated_cells,
                "planned_calls": self.planned_calls,
                "budget_revision_id": self.budget_revision_id,
                "budget_fingerprint": self.budget_fingerprint,
                "request_fingerprint": self.request_fingerprint,
                "plan_fingerprint": self.plan_fingerprint,
                "transport_mapping_status": self.transport_mapping_status,
                "remote_executable": self.remote_executable,
            }
        )


def _identity_count(selector: LiveDailyMarketSelector) -> int:
    if isinstance(selector, (ListedInstrumentSelector, AShareDailySelector, BenchmarkDailySelector)):
        return len(selector.identities)
    return 1


def _planned_calls(
    selector: LiveDailyMarketSelector,
    contract: CapabilityPlanningContract,
) -> int:
    if contract.call_count_strategy is CallCountStrategy.ONE_LOGICAL_REQUEST:
        return 1
    if contract.call_count_strategy is CallCountStrategy.ONE_REQUEST_PER_IDENTITY:
        return _identity_count(selector)
    raise RequestPlanningError(
        "unsupported call-count strategy",
        RequestPlanningFailureCode.UNSUPPORTED_CAPABILITY,
    )


def _estimated_cells(
    selector: LiveDailyMarketSelector,
    contract: CapabilityPlanningContract,
) -> int:
    if isinstance(selector, TradingCalendarSelector):
        logical_rows = len(selector.requested_dates)
    elif isinstance(selector, ListedInstrumentSelector):
        logical_rows = len(selector.identities)
    elif isinstance(selector, (AShareDailySelector, BenchmarkDailySelector)):
        logical_rows = len(selector.expected_observations)
    elif isinstance(selector, HistoricalBlockSnapshotSelector):
        logical_rows = selector.expected_member_count
    else:
        raise RequestPlanningError(
            "unsupported selector type",
            RequestPlanningFailureCode.UNSUPPORTED_CAPABILITY,
        )
    return logical_rows * contract.field_count_for_budget


def build_live_request_plan(
    selector: LiveDailyMarketSelector,
    quota_budget: AcquisitionQuotaBudget,
    *,
    policy: LiveDailyMarketSourcePolicy = DEFAULT_LIVE_SOURCE_POLICY,
) -> DailyMarketRequestPlan:
    if policy != DEFAULT_LIVE_SOURCE_POLICY:
        raise RequestPlanningError(
            "planning requires the exact reviewed live source policy",
            RequestPlanningFailureCode.POLICY_MISMATCH,
        )
    if not isinstance(
        selector,
        (
            ListedInstrumentSelector,
            TradingCalendarSelector,
            AShareDailySelector,
            BenchmarkDailySelector,
            HistoricalBlockSnapshotSelector,
        ),
    ):
        raise RequestPlanningError(
            "selector type is not authorized",
            RequestPlanningFailureCode.UNSUPPORTED_CAPABILITY,
        )
    policy.assert_capability(selector.capability)
    try:
        contract = CAPABILITY_PLANNING_REGISTRY[selector.capability]
    except KeyError as exc:
        raise RequestPlanningError(
            "capability is not present in the closed planning registry",
            RequestPlanningFailureCode.UNSUPPORTED_CAPABILITY,
        ) from exc
    if selector.schema_version != contract.selector_schema_version:
        raise RequestPlanningError(
            "selector schema does not match the closed capability contract",
            RequestPlanningFailureCode.POLICY_MISMATCH,
        )
    quota_budget.assert_compatible(policy)

    planned_calls = _planned_calls(selector, contract)
    estimated_cells = _estimated_cells(selector, contract)
    if planned_calls > quota_budget.remaining_calls:
        raise RequestPlanningError(
            "planned calls exceed the explicit remaining call budget",
            RequestPlanningFailureCode.CALL_BUDGET_EXCEEDED,
        )
    if estimated_cells > quota_budget.remaining_cells:
        raise RequestPlanningError(
            "estimated cells exceed the explicit remaining cell budget",
            RequestPlanningFailureCode.CELL_BUDGET_EXCEEDED,
        )

    request_payload = {
        "planning_policy_version": LIVE_PLANNING_POLICY_VERSION,
        "source_key": policy.source_key,
        "source_policy_fingerprint": policy.policy_fingerprint,
        "capability_contract_fingerprint": contract.contract_fingerprint,
        "selector_fingerprint": selector.selector_fingerprint,
        "operation_key": contract.operation_key,
        "ordered_parameters": selector.ordered_parameters(),
    }
    request_fingerprint = canonical_sha256(request_payload)
    plan_payload = {
        **request_payload,
        "planned_calls": planned_calls,
        "estimated_cells": estimated_cells,
        "budget_revision_id": quota_budget.budget_revision_id,
        "budget_fingerprint": quota_budget.budget_fingerprint,
        "remote_executable": False,
    }
    return DailyMarketRequestPlan(
        planning_policy_version=LIVE_PLANNING_POLICY_VERSION,
        source_key=policy.source_key,
        source_policy_fingerprint=policy.policy_fingerprint,
        capability=selector.capability,
        operation_key=contract.operation_key,
        capability_contract_fingerprint=contract.contract_fingerprint,
        selector_schema_version=selector.schema_version,
        selector_fingerprint=selector.selector_fingerprint,
        ordered_parameters=selector.ordered_parameters(),
        requested_sessions=tuple(item.isoformat() for item in selector.requested_sessions),
        item_count=selector.item_count,
        estimated_cells=estimated_cells,
        planned_calls=planned_calls,
        budget_revision_id=quota_budget.budget_revision_id,
        budget_fingerprint=quota_budget.budget_fingerprint,
        request_fingerprint=request_fingerprint,
        plan_fingerprint=canonical_sha256(plan_payload),
        transport_mapping_status=contract.transport_mapping_status,
        remote_executable=False,
    )
