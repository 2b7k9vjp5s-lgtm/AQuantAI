"""Deterministic zero-network acquisition adapter backed by synthetic fixtures."""

from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path
from typing import Any, Mapping

from .contracts import (
    ADAPTER_CONTRACT_VERSION,
    DEFAULT_MOCK_ASSUMPTION,
    SYNTHETIC_SOURCE_KEY,
    CapabilityFamily,
    CoverageStatus,
    FailureCategory,
    MockPlanningAssumption,
    MockScenario,
    Retryability,
    SourceMode,
    TodayMarketAcquisitionBatch,
    TodayMarketAcquisitionError,
    TodayMarketAcquisitionFailure,
    TodayMarketCoverage,
    TodayMarketFamilyResult,
    TodayMarketRefreshPlan,
    TodayMarketSourceProvenance,
    ValidationStatus,
)
from .fingerprint import canonical_sha256

_FIXTURE_MARKER = "synthetic"
_FIXTURE_NAMES = {
    MockScenario.STALE_SUCCESS: "complete_index_led.synthetic.json",
    MockScenario.PARTIAL_FAMILY_FAILURE: "partial_family.synthetic.json",
    MockScenario.SCHEMA_MISMATCH: "schema_mismatch.synthetic.json",
    MockScenario.COVERAGE_INCOMPLETE: "coverage_incomplete.synthetic.json",
    MockScenario.SYNTHETIC_CORRECTION_REVISION: "correction_revision.synthetic.json",
}


@dataclass(slots=True)
class MockUsageState:
    active_requests: int = 0
    daily_requests: dict[str, int] = field(default_factory=dict)
    second_requests: dict[int, int] = field(default_factory=dict)


def _failure(
    plan: TodayMarketRefreshPlan,
    *,
    code: str,
    category: FailureCategory,
    retryability: Retryability,
) -> TodayMarketAcquisitionError:
    return TodayMarketAcquisitionError(
        TodayMarketAcquisitionFailure(
            failure_code=code,
            category=category,
            refresh_attempt_id=plan.refresh_attempt_id,
            source_key=SYNTHETIC_SOURCE_KEY,
            redacted_details=(code,),
            retryability=retryability,
        )
    )


def _load_fixture(path: Path) -> tuple[Mapping[str, Any], str]:
    raw = path.read_bytes()
    value = json.loads(raw.decode("utf-8"))
    if not isinstance(value, dict):
        raise ValueError("synthetic fixture root must be an object")
    if value.get("_aquantai_fixture_kind") != _FIXTURE_MARKER:
        raise ValueError("synthetic fixture marker is required")
    if set(value) != {"_aquantai_fixture_kind", "schema_version", "families"}:
        raise ValueError("synthetic fixture contains unknown top-level fields")
    if not isinstance(value["schema_version"], str) or not value["schema_version"]:
        raise ValueError("synthetic fixture schema_version is required")
    if not isinstance(value["families"], dict):
        raise ValueError("synthetic fixture families must be an object")
    return value, canonical_sha256(value)


class DeterministicTodayMarketMock:
    """Synchronous deterministic test double with no network or credential path."""

    def __init__(
        self,
        *,
        fixture_root: Path,
        scenario: MockScenario = MockScenario.STALE_SUCCESS,
        assumption: MockPlanningAssumption = DEFAULT_MOCK_ASSUMPTION,
        usage_state: MockUsageState | None = None,
    ) -> None:
        self._fixture_root = fixture_root
        self._scenario = scenario
        self._assumption = assumption
        self._usage = usage_state or MockUsageState()
        self.call_count = 0

    @property
    def scenario(self) -> MockScenario:
        return self._scenario

    def _enter_usage(self, plan: TodayMarketRefreshPlan) -> None:
        if self._usage.active_requests >= self._assumption.mock_concurrency:
            raise _failure(
                plan,
                code="mock_concurrency_exceeded",
                category=FailureCategory.CONCURRENCY_CONFLICT,
                retryability=Retryability.EXPLICIT_USER_RETRY,
            )
        second_key = int(plan.recorded_at_utc.timestamp())
        second_count = self._usage.second_requests.get(second_key, 0)
        if second_count >= self._assumption.mock_qps:
            raise _failure(
                plan,
                code="mock_qps_exceeded",
                category=FailureCategory.ASSUMPTION_BUDGET_EXHAUSTED,
                retryability=Retryability.EXPLICIT_USER_RETRY,
            )
        day_key = plan.recorded_at_utc.date().isoformat()
        day_count = self._usage.daily_requests.get(day_key, 0)
        if day_count >= self._assumption.mock_daily_request_budget:
            raise _failure(
                plan,
                code="mock_daily_budget_exhausted",
                category=FailureCategory.ASSUMPTION_BUDGET_EXHAUSTED,
                retryability=Retryability.EXPLICIT_USER_RETRY,
            )
        self._usage.active_requests += 1
        self._usage.second_requests[second_key] = second_count + 1
        self._usage.daily_requests[day_key] = day_count + 1

    def acquire(self, plan: TodayMarketRefreshPlan) -> TodayMarketAcquisitionBatch:
        if not plan.verify_fingerprint():
            raise _failure(
                plan,
                code="mock_plan_fingerprint_invalid",
                category=FailureCategory.PLAN_INVALID,
                retryability=Retryability.NONE,
            )
        if plan.assumption_profile_id != self._assumption.profile_id:
            raise _failure(
                plan,
                code="mock_assumption_profile_mismatch",
                category=FailureCategory.PLAN_INVALID,
                retryability=Retryability.NONE,
            )
        if self._scenario is MockScenario.QUOTA_ASSUMPTION_EXHAUSTED:
            raise _failure(
                plan,
                code="mock_daily_budget_exhausted",
                category=FailureCategory.ASSUMPTION_BUDGET_EXHAUSTED,
                retryability=Retryability.EXPLICIT_USER_RETRY,
            )

        self._enter_usage(plan)
        self.call_count += 1
        try:
            fixture_name = _FIXTURE_NAMES.get(self._scenario)
            if fixture_name is None:
                raise _failure(
                    plan,
                    code="mock_scenario_unsupported",
                    category=FailureCategory.INTERNAL_VALIDATION_FAILED,
                    retryability=Retryability.NONE,
                )
            fixture, fixture_fingerprint = _load_fixture(
                self._fixture_root / fixture_name
            )
            return self._build_batch(plan, fixture, fixture_fingerprint)
        finally:
            self._usage.active_requests -= 1

    def _build_batch(
        self,
        plan: TodayMarketRefreshPlan,
        fixture: Mapping[str, Any],
        fixture_fingerprint: str,
    ) -> TodayMarketAcquisitionBatch:
        fixture_families = fixture["families"]
        results: list[TodayMarketFamilyResult] = []
        complete: list[CapabilityFamily] = []
        missing: list[CapabilityFamily] = []
        covered_union = set(plan.requested_completed_sessions)

        for family in plan.capability_set:
            raw_family = fixture_families.get(family.value)
            if raw_family is None:
                missing.append(family)
                continue
            validation = ValidationStatus.VALID
            reasons: tuple[str, ...] = ()
            payload: Mapping[str, Any]
            if (
                not isinstance(raw_family, dict)
                or set(raw_family) != {"schema_version", "payload", "item_count"}
                or not isinstance(raw_family.get("schema_version"), str)
                or not isinstance(raw_family.get("item_count"), int)
                or not isinstance(raw_family.get("payload"), dict)
            ):
                validation = ValidationStatus.INVALID
                reasons = ("mock_schema_mismatch",)
                payload = {}
                item_count = 0
            else:
                payload = raw_family["payload"]
                item_count = raw_family["item_count"]

            covered_sessions = plan.requested_completed_sessions
            if (
                self._scenario is MockScenario.COVERAGE_INCOMPLETE
                and family is plan.capability_set[-1]
            ):
                covered_sessions = plan.requested_completed_sessions[:-1]
                covered_union.intersection_update(covered_sessions)
                reasons = (*reasons, "mock_coverage_incomplete")
            if (
                validation is ValidationStatus.VALID
                and covered_sessions == plan.requested_completed_sessions
            ):
                complete.append(family)
            else:
                missing.append(family)

            content_payload = {
                "family_key": family,
                "schema_version": (
                    raw_family.get("schema_version", "invalid")
                    if isinstance(raw_family, dict)
                    else "invalid"
                ),
                "requested_sessions": plan.requested_completed_sessions,
                "covered_sessions": covered_sessions,
                "item_count": item_count,
                "synthetic": True,
                "source_key": SYNTHETIC_SOURCE_KEY,
                "payload": payload,
            }
            results.append(
                TodayMarketFamilyResult(
                    family_key=family,
                    schema_version=content_payload["schema_version"],
                    requested_sessions=plan.requested_completed_sessions,
                    covered_sessions=covered_sessions,
                    item_count=item_count,
                    synthetic=True,
                    source_key=SYNTHETIC_SOURCE_KEY,
                    content_fingerprint=canonical_sha256(content_payload),
                    validation_status=validation,
                    reason_codes=reasons,
                    payload=payload,
                )
            )

        complete_tuple = tuple(sorted(set(complete), key=lambda value: value.value))
        missing_tuple = tuple(sorted(set(missing), key=lambda value: value.value))
        covered_sessions = tuple(
            session
            for session in plan.requested_completed_sessions
            if session in covered_union
        )
        status = (
            CoverageStatus.COMPLETE
            if not missing_tuple
            and covered_sessions == plan.requested_completed_sessions
            else CoverageStatus.PARTIAL
        )
        reason_codes = (
            ()
            if status is CoverageStatus.COMPLETE
            else tuple(
                sorted(
                    {
                        "mock_batch_incomplete",
                        *(
                            code
                            for result in results
                            for code in result.reason_codes
                        ),
                    }
                )
            )
        )
        coverage = TodayMarketCoverage(
            status=status,
            requested_sessions=plan.requested_completed_sessions,
            covered_sessions=covered_sessions,
            required_families=plan.capability_set,
            complete_families=complete_tuple,
            missing_families=missing_tuple,
            excluded_items=(),
            coverage_reason_codes=reason_codes,
        )
        provenance = TodayMarketSourceProvenance(
            source_key=SYNTHETIC_SOURCE_KEY,
            adapter_contract_version=ADAPTER_CONTRACT_VERSION,
            source_contract_fingerprints=(fixture_fingerprint,),
            source_mode=SourceMode.SYNTHETIC_MOCK,
            observed_at_utc=plan.recorded_at_utc,
            provider_confirmed=False,
        )
        scenario_id = f"{self._scenario.value}-{fixture_fingerprint[:16]}"
        diagnostics = (
            "synthetic_engineering_scenario",
            "provider_confirmed=false",
            "production_live_source_ready=false",
        )
        batch_payload = {
            "refresh_attempt_id": plan.refresh_attempt_id,
            "scenario_or_source_attempt_id": scenario_id,
            "source_provenance": provenance,
            "requested_sessions": plan.requested_completed_sessions,
            "data_through_session": plan.requested_completed_sessions[-1],
            "coverage": coverage,
            "family_results": tuple(results),
            "redacted_diagnostics": diagnostics,
        }
        batch = TodayMarketAcquisitionBatch(
            refresh_attempt_id=plan.refresh_attempt_id,
            scenario_or_source_attempt_id=scenario_id,
            source_provenance=provenance,
            requested_sessions=plan.requested_completed_sessions,
            data_through_session=plan.requested_completed_sessions[-1],
            coverage=coverage,
            family_results=tuple(results),
            redacted_diagnostics=diagnostics,
            batch_fingerprint=canonical_sha256(batch_payload),
        )
        if not batch.verify_fingerprint():
            raise RuntimeError("constructed Mock batch fingerprint is inconsistent")
        return batch
