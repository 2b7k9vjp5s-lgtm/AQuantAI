"""In-memory Today Market refresh orchestration for the deterministic Mock slice."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from datetime import date

from .contracts import (
    SYNTHETIC_SOURCE_KEY,
    CapabilityFamily,
    FailureCategory,
    OrchestrationState,
    PlanningState,
    Retryability,
    SnapshotReference,
    TodayMarketAcquisitionError,
    TodayMarketAcquisitionFailure,
    TodayMarketRefreshIntent,
    TodayMarketRefreshOutcome,
)
from .planner import build_refresh_plan
from .port import TodayMarketAcquisitionPort
from .projection import CandidateValidationError, build_demo_projection


def _failure_message(failure: TodayMarketAcquisitionFailure) -> str:
    if failure.category is FailureCategory.ASSUMPTION_BUDGET_EXHAUSTED:
        return "模拟额度已用尽，未影响真实数据源状态"
    if failure.category is FailureCategory.CONCURRENCY_CONFLICT:
        return "已有模拟更新正在执行，已保留上一次完整结果"
    if failure.category is FailureCategory.SCHEMA_MISMATCH:
        return "模拟数据结构不符合合同，未发布更新"
    if failure.category is FailureCategory.COVERAGE_INCOMPLETE:
        return "部分模拟数据不完整，已保留上一次完整结果"
    if failure.category is FailureCategory.APPLICATION_SHUTDOWN:
        return "应用已关闭，更新未继续执行"
    return "模拟更新失败，已保留上一次完整结果"


def _validation_failure(
    refresh_attempt_id: str,
    *,
    code: str,
    category: FailureCategory,
) -> TodayMarketAcquisitionFailure:
    return TodayMarketAcquisitionFailure(
        failure_code=code,
        category=category,
        refresh_attempt_id=refresh_attempt_id,
        source_key=SYNTHETIC_SOURCE_KEY,
        redacted_details=(code,),
        retryability=Retryability.EXPLICIT_USER_RETRY,
    )


def run_mock_refresh(
    *,
    intent: TodayMarketRefreshIntent,
    expected_completed_sessions: Iterable[date],
    prior_snapshot: SnapshotReference | None,
    capability_set: Iterable[CapabilityFamily],
    port: TodayMarketAcquisitionPort,
    shutdown_requested: Callable[[], bool] | None = None,
) -> TodayMarketRefreshOutcome:
    """Run one deterministic in-memory refresh attempt without persistence."""

    decision = build_refresh_plan(
        intent,
        expected_completed_sessions=expected_completed_sessions,
        prior_snapshot=prior_snapshot,
        capability_set=capability_set,
    )
    if decision.state is PlanningState.CURRENT:
        return TodayMarketRefreshOutcome(
            state=OrchestrationState.NO_REFRESH_NEEDED,
            prior_snapshot=prior_snapshot,
            candidate_projection=None,
            plan=None,
            failure=None,
            message_zh=decision.message_zh,
        )
    if decision.state is PlanningState.MANUAL_CATCHUP_REQUIRED:
        return TodayMarketRefreshOutcome(
            state=OrchestrationState.MANUAL_CATCHUP_REQUIRED,
            prior_snapshot=prior_snapshot,
            candidate_projection=None,
            plan=None,
            failure=None,
            message_zh=decision.message_zh,
        )
    if decision.state is PlanningState.NOT_INITIALIZED:
        return TodayMarketRefreshOutcome(
            state=OrchestrationState.NOT_INITIALIZED,
            prior_snapshot=None,
            candidate_projection=None,
            plan=None,
            failure=None,
            message_zh=decision.message_zh,
        )

    plan = decision.plan
    if plan is None:
        raise RuntimeError("acquisition-required decision must include a plan")
    try:
        batch = port.acquire(plan)
    except TodayMarketAcquisitionError as exc:
        return TodayMarketRefreshOutcome(
            state=OrchestrationState.FAILED_RETAINED_PRIOR,
            prior_snapshot=prior_snapshot,
            candidate_projection=None,
            plan=plan,
            failure=exc.failure,
            message_zh=_failure_message(exc.failure),
        )

    if shutdown_requested is not None and shutdown_requested():
        failure = _validation_failure(
            plan.refresh_attempt_id,
            code="application_shutdown_before_publish",
            category=FailureCategory.APPLICATION_SHUTDOWN,
        )
        return TodayMarketRefreshOutcome(
            state=OrchestrationState.CANCELLED_RETAINED_PRIOR,
            prior_snapshot=prior_snapshot,
            candidate_projection=None,
            plan=plan,
            failure=failure,
            message_zh=_failure_message(failure),
        )

    try:
        projection = build_demo_projection(batch)
    except CandidateValidationError as exc:
        message = str(exc)
        category = (
            FailureCategory.SCHEMA_MISMATCH
            if "invalid" in message or "fingerprint" in message
            else FailureCategory.COVERAGE_INCOMPLETE
        )
        failure = _validation_failure(
            plan.refresh_attempt_id,
            code="mock_candidate_validation_failed",
            category=category,
        )
        return TodayMarketRefreshOutcome(
            state=OrchestrationState.FAILED_RETAINED_PRIOR,
            prior_snapshot=prior_snapshot,
            candidate_projection=None,
            plan=plan,
            failure=failure,
            message_zh=_failure_message(failure),
        )

    return TodayMarketRefreshOutcome(
        state=OrchestrationState.PUBLISHED_DEMO,
        prior_snapshot=prior_snapshot,
        candidate_projection=projection,
        plan=plan,
        failure=None,
        message_zh=projection.message_zh,
    )
