"""Deterministic, zero-network refresh planning."""

from __future__ import annotations

from datetime import date
from typing import Iterable

from .contracts import (
    DEFAULT_MOCK_ASSUMPTION,
    MOCK_ASSUMPTION_PROFILE_ID,
    CapabilityFamily,
    PlanningState,
    RefreshPlanningDecision,
    SnapshotReference,
    TodayMarketRefreshIntent,
    TodayMarketRefreshPlan,
)
from .fingerprint import canonical_sha256

AUTOMATIC_SESSION_CEILING = 10

_MESSAGES = {
    PlanningState.CURRENT: "当前本地市场数据已是最新",
    PlanningState.MANUAL_CATCHUP_REQUIRED: "缺失交易日超过自动更新上限，需要手动补齐",
    PlanningState.NOT_INITIALIZED: "今日市场尚未初始化，需要先执行明确的初始化流程",
    PlanningState.ACQUISITION_REQUIRED: "正在使用模拟数据验证更新流程",
}


def _normalize_sessions(values: Iterable[date]) -> tuple[date, ...]:
    sessions = tuple(values)
    if any(not isinstance(value, date) for value in sessions):
        raise TypeError("expected_completed_sessions must contain date values")
    normalized = tuple(sorted(set(sessions)))
    if normalized != sessions:
        raise ValueError("expected_completed_sessions must be sorted and unique")
    return normalized


def _normalize_capabilities(
    values: Iterable[CapabilityFamily],
) -> tuple[CapabilityFamily, ...]:
    raw_values = tuple(values)
    capabilities: list[CapabilityFamily] = []
    for value in raw_values:
        candidate = getattr(value, "value", value)
        try:
            capabilities.append(CapabilityFamily(candidate))
        except (TypeError, ValueError) as exc:
            raise TypeError("capability_set contains an unsupported value") from exc
    normalized = tuple(sorted(set(capabilities), key=lambda value: value.value))
    if normalized != tuple(capabilities):
        raise ValueError("capability_set must be sorted and unique")
    if not capabilities:
        raise ValueError("capability_set must not be empty")
    return tuple(capabilities)


def _missing_sessions(
    sessions: tuple[date, ...], prior_snapshot: SnapshotReference | None
) -> tuple[date, ...]:
    if prior_snapshot is None:
        return sessions
    return tuple(
        session for session in sessions if session > prior_snapshot.data_through_session
    )


def build_refresh_plan(
    intent: TodayMarketRefreshIntent,
    *,
    expected_completed_sessions: Iterable[date],
    prior_snapshot: SnapshotReference | None,
    capability_set: Iterable[CapabilityFamily],
) -> RefreshPlanningDecision:
    """Build one exact Mock-only plan or a non-acquisition planning state."""

    sessions = _normalize_sessions(expected_completed_sessions)
    capabilities = _normalize_capabilities(capability_set)

    if prior_snapshot is None:
        return RefreshPlanningDecision(
            state=PlanningState.NOT_INITIALIZED,
            plan=None,
            missing_sessions=sessions,
            message_zh=_MESSAGES[PlanningState.NOT_INITIALIZED],
        )
    if intent.prior_snapshot_id != prior_snapshot.snapshot_id:
        raise ValueError(
            "intent prior_snapshot_id does not match the supplied prior snapshot"
        )
    missing = _missing_sessions(sessions, prior_snapshot)
    if not missing:
        return RefreshPlanningDecision(
            state=PlanningState.CURRENT,
            plan=None,
            missing_sessions=(),
            message_zh=_MESSAGES[PlanningState.CURRENT],
        )
    if len(missing) > AUTOMATIC_SESSION_CEILING:
        return RefreshPlanningDecision(
            state=PlanningState.MANUAL_CATCHUP_REQUIRED,
            plan=None,
            missing_sessions=missing,
            message_zh=_MESSAGES[PlanningState.MANUAL_CATCHUP_REQUIRED],
        )

    attempt_seed = {
        "scope_revision_id": intent.scope_revision_id,
        "trigger": intent.trigger,
        "prior_snapshot_id": intent.prior_snapshot_id,
        "requested_completed_sessions": missing,
        "capability_set": capabilities,
        "recorded_at_utc": intent.local_clock_utc,
        "planning_policy_version": intent.planning_policy_version,
        "assumption_profile_id": MOCK_ASSUMPTION_PROFILE_ID,
    }
    refresh_attempt_id = f"mock-refresh-{canonical_sha256(attempt_seed)[:20]}"
    family_bounds = tuple((family.value, len(missing)) for family in capabilities)
    fingerprint_payload = {
        "scope_revision_id": intent.scope_revision_id,
        "refresh_attempt_id": refresh_attempt_id,
        "trigger": intent.trigger,
        "prior_snapshot_id": intent.prior_snapshot_id,
        "requested_completed_sessions": missing,
        "capability_set": capabilities,
        "family_bounds": family_bounds,
        "information_cutoff": missing[-1],
        "recorded_at_utc": intent.local_clock_utc,
        "planning_policy_version": intent.planning_policy_version,
        "assumption_profile_id": DEFAULT_MOCK_ASSUMPTION.profile_id,
    }
    plan = TodayMarketRefreshPlan(
        scope_revision_id=intent.scope_revision_id,
        refresh_attempt_id=refresh_attempt_id,
        trigger=intent.trigger,
        prior_snapshot_id=intent.prior_snapshot_id,
        requested_completed_sessions=missing,
        capability_set=capabilities,
        family_bounds=family_bounds,
        information_cutoff=missing[-1],
        recorded_at_utc=intent.local_clock_utc,
        planning_policy_version=intent.planning_policy_version,
        assumption_profile_id=DEFAULT_MOCK_ASSUMPTION.profile_id,
        plan_fingerprint=canonical_sha256(fingerprint_payload),
    )
    if not plan.verify_fingerprint():
        raise RuntimeError("constructed refresh plan fingerprint is inconsistent")
    return RefreshPlanningDecision(
        state=PlanningState.ACQUISITION_REQUIRED,
        plan=plan,
        missing_sessions=missing,
        message_zh=_MESSAGES[PlanningState.ACQUISITION_REQUIRED],
    )
