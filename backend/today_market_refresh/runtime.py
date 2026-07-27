"""Process-local Mock-only Today Market runtime integration."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from threading import RLock
from typing import Any

from .contracts import (
    PLANNING_POLICY_VERSION,
    REQUIRED_CAPABILITY_FAMILIES,
    MockScenario,
    OrchestrationState,
    RefreshTrigger,
    SnapshotReference,
    TodayMarketRefreshIntent,
)
from .fingerprint import canonical_sha256
from .mock import DeterministicTodayMarketMock
from .orchestrator import run_mock_refresh
from .port import TodayMarketAcquisitionPort

RUNTIME_SCOPE_VERSION = "aquantai.today-market-runtime-scope.v1"
RUNTIME_STATUS_VERSION = "aquantai.today-market-runtime-status.v1"
MOCK_CONFIGURATION_VERSION = "aquantai.today-market-mock-runtime-configuration.v1"

_ALLOWED_TRIGGERS = {
    RefreshTrigger.FIRST_TODAY_MARKET_ENTRY,
    RefreshTrigger.EXPLICIT_USER_RETRY,
}


@dataclass(frozen=True, slots=True)
class TodayMarketMockRuntimeConfigurationV1:
    configuration_version: str = MOCK_CONFIGURATION_VERSION
    mock_enabled: bool = False
    mock_scenario_id: str | None = None

    def __post_init__(self) -> None:
        if self.configuration_version != MOCK_CONFIGURATION_VERSION:
            raise ValueError("unsupported Today Market Mock configuration version")
        if self.mock_enabled:
            if self.mock_scenario_id is None:
                raise ValueError("enabled Mock runtime requires one reviewed scenario")
            MockScenario(self.mock_scenario_id)
        elif self.mock_scenario_id is not None:
            raise ValueError("disabled Mock runtime must use a null scenario")


@dataclass(frozen=True, slots=True)
class TodayMarketPriorSnapshotContext:
    snapshot_reference: SnapshotReference
    identity_payload: Mapping[str, Any]
    content_payload: Mapping[str, Any]
    projected_snapshot: Mapping[str, Any]


@dataclass(frozen=True, slots=True)
class TodayMarketRuntimeScopeV1:
    payload: Mapping[str, Any]
    runtime_scope_revision_id: str

    def to_dict(self) -> dict[str, Any]:
        return {**dict(self.payload), "runtime_scope_revision_id": self.runtime_scope_revision_id}


@dataclass(slots=True)
class _RuntimeState:
    runtime_status_revision: int = 0
    phase: str = "prior_snapshot_ready"
    refresh_state: str = "not_started"
    automatic_attempt_state: str = "not_attempted"
    active_attempt_id: str | None = None
    plan_fingerprint: str | None = None
    candidate_projection: dict[str, Any] | None = None
    failure: dict[str, Any] | None = None
    last_command_key: str | None = None


class RuntimeStatusConflict(RuntimeError):
    pass


class RuntimeScopeConflict(RuntimeError):
    pass


PortFactory = Callable[
    [TodayMarketMockRuntimeConfigurationV1], TodayMarketAcquisitionPort
]


class TodayMarketRuntimeCoordinator:
    """One synchronous process-local state owner keyed by exact scope revision."""

    def __init__(self, *, port_factory: PortFactory | None = None) -> None:
        self._lock = RLock()
        self._states: dict[str, _RuntimeState] = {}
        self._active_scopes: set[str] = set()
        self._port_factory = port_factory

    def get_status(
        self,
        scope: TodayMarketRuntimeScopeV1,
        configuration: TodayMarketMockRuntimeConfigurationV1,
    ) -> dict[str, Any]:
        with self._lock:
            state = self._states.get(scope.runtime_scope_revision_id)
            if state is None:
                state = _RuntimeState(
                    phase=(
                        "prior_snapshot_ready"
                        if configuration.mock_enabled
                        else "mock_not_enabled"
                    ),
                    refresh_state=(
                        "ready"
                        if configuration.mock_enabled
                        else "not_configured"
                    ),
                )
                self._states[scope.runtime_scope_revision_id] = state
            return _status_dict(scope, configuration, state)

    def execute(
        self,
        *,
        scope: TodayMarketRuntimeScopeV1,
        configuration: TodayMarketMockRuntimeConfigurationV1,
        expected_runtime_status_fingerprint: str,
        trigger: RefreshTrigger,
        fixture_root: Path | None,
    ) -> dict[str, Any]:
        if trigger not in _ALLOWED_TRIGGERS:
            raise ValueError("runtime trigger is not allowed")
        scope_id = scope.runtime_scope_revision_id
        with self._lock:
            current = self.get_status(scope, configuration)
            state = self._states[scope_id]
            command_key = canonical_sha256(
                {
                    "runtime_scope_revision_id": scope_id,
                    "expected_runtime_status_fingerprint": (
                        expected_runtime_status_fingerprint
                    ),
                    "trigger": trigger,
                }
            )
            if state.last_command_key == command_key and state.phase in {
                "no_refresh_needed",
                "not_initialized",
                "manual_catchup_required",
                "demo_published",
                "failed_retained_prior",
                "cancelled_retained_prior",
            }:
                return current
            if current["runtime_status_fingerprint"] != expected_runtime_status_fingerprint:
                raise RuntimeStatusConflict("runtime status generation changed")
            if scope_id in self._active_scopes:
                raise RuntimeStatusConflict("runtime command already active")
            if not configuration.mock_enabled:
                raise RuntimeScopeConflict("Mock runtime is not enabled")
            if (
                trigger is RefreshTrigger.FIRST_TODAY_MARKET_ENTRY
                and state.automatic_attempt_state != "not_attempted"
            ):
                raise RuntimeStatusConflict("automatic attempt already consumed")
            if (
                trigger is RefreshTrigger.EXPLICIT_USER_RETRY
                and state.phase
                not in {"failed_retained_prior", "cancelled_retained_prior"}
            ):
                raise ValueError("explicit retry is not available for current state")
            if fixture_root is None:
                raise RuntimeError("enabled Mock runtime requires a fixture root")

            state.runtime_status_revision += 1
            state.phase = "refresh_in_progress"
            state.refresh_state = "in_progress"
            state.active_attempt_id = command_key
            state.automatic_attempt_state = (
                "attempted"
                if trigger is RefreshTrigger.FIRST_TODAY_MARKET_ENTRY
                else state.automatic_attempt_state
            )
            self._active_scopes.add(scope_id)

            intent_scope_id = canonical_sha256(
                {
                    "runtime_scope_revision_id": scope_id,
                    "expected_runtime_status_fingerprint": (
                        expected_runtime_status_fingerprint
                    ),
                    "trigger": trigger,
                }
            )
            prior = SnapshotReference(
                snapshot_id=str(scope.payload["prior_snapshot_id"]),
                data_through_session=date.fromisoformat(
                    str(scope.payload["prior_snapshot_data_through_session"])
                ),
                content_fingerprint=str(
                    scope.payload["prior_snapshot_content_fingerprint"]
                ),
            )
            intent = TodayMarketRefreshIntent(
                scope_revision_id=intent_scope_id,
                trigger=trigger,
                prior_snapshot_id=prior.snapshot_id,
                local_clock_utc=_parse_utc(
                    str(scope.payload["planning_recorded_at_utc"])
                ),
            )
            expected_sessions = _expected_completed_sessions(
                prior.data_through_session,
                date.fromisoformat(str(scope.payload["as_of_cutoff"])),
            )

        try:
            port = (
                self._port_factory(configuration)
                if self._port_factory is not None
                else DeterministicTodayMarketMock(
                    fixture_root=fixture_root,
                    scenario=MockScenario(str(configuration.mock_scenario_id)),
                )
            )
            outcome = run_mock_refresh(
                intent=intent,
                expected_completed_sessions=expected_sessions,
                prior_snapshot=prior,
                capability_set=REQUIRED_CAPABILITY_FAMILIES,
                port=port,
            )
        except Exception:
            with self._lock:
                self._active_scopes.discard(scope_id)
                state = self._states[scope_id]
                state.runtime_status_revision += 1
                state.phase = "failed_retained_prior"
                state.refresh_state = "failed"
                state.active_attempt_id = None
                state.plan_fingerprint = None
                state.candidate_projection = None
                state.failure = {
                    "failure_code": "runtime_internal_validation_failed",
                    "category": "internal_validation_failed",
                    "refresh_attempt_id": command_key,
                    "source_key": None,
                    "redacted_details": ["runtime_internal_validation_failed"],
                    "retryability": "explicit_user_retry",
                }
                state.last_command_key = command_key
            raise

        with self._lock:
            state = self._states[scope_id]
            state.active_attempt_id = (
                outcome.plan.refresh_attempt_id if outcome.plan is not None else None
            )
            state.plan_fingerprint = (
                outcome.plan.plan_fingerprint if outcome.plan is not None else None
            )
            state.candidate_projection = _serialize_projection(
                outcome.candidate_projection
            )
            state.failure = _serialize_failure(outcome.failure)
            state.phase, state.refresh_state = _phase_from_outcome(outcome.state)
            state.runtime_status_revision += 1
            state.last_command_key = command_key
            self._active_scopes.discard(scope_id)
            return _status_dict(scope, configuration, state)


def install_today_market_runtime(
    app: Any,
    *,
    configuration: TodayMarketMockRuntimeConfigurationV1 | None = None,
    fixture_root: Path | None = None,
    coordinator: TodayMarketRuntimeCoordinator | None = None,
) -> None:
    """Install immutable application-instance runtime dependencies."""

    resolved = configuration or TodayMarketMockRuntimeConfigurationV1()
    if resolved.mock_enabled and fixture_root is None:
        raise ValueError("enabled Mock runtime requires an explicit fixture root")
    app.state.today_market_runtime_configuration = resolved
    app.state.today_market_runtime_fixture_root = fixture_root
    app.state.today_market_runtime_coordinator = (
        coordinator or TodayMarketRuntimeCoordinator()
    )


def build_runtime_scope(
    *,
    request: TodayMarketSnapshotRequest,
    prior: TodayMarketPriorSnapshotContext,
    configuration: TodayMarketMockRuntimeConfigurationV1,
) -> TodayMarketRuntimeScopeV1:
    payload = {
        "runtime_scope_version": RUNTIME_SCOPE_VERSION,
        "as_of_cutoff": request.boundaries.cutoff.isoformat(),
        "as_of_recorded_at_utc": request.boundaries.recorded_at_iso,
        "equity_series_key": request.equity_series_key,
        "benchmark_series_key": request.benchmark_series_key,
        "sector_series_key": request.sector_series_key,
        "prior_snapshot_id": prior.snapshot_reference.snapshot_id,
        "prior_snapshot_content_fingerprint": (
            prior.snapshot_reference.content_fingerprint
        ),
        "prior_snapshot_data_through_session": (
            prior.snapshot_reference.data_through_session.isoformat()
        ),
        "required_capability_set": [
            family.value for family in REQUIRED_CAPABILITY_FAMILIES
        ],
        "planning_policy_version": PLANNING_POLICY_VERSION,
        "planning_recorded_at_utc": request.boundaries.recorded_at_iso,
        "mock_configuration_version": configuration.configuration_version,
        "mock_enabled": configuration.mock_enabled,
        "mock_scenario_id": configuration.mock_scenario_id,
    }
    return TodayMarketRuntimeScopeV1(
        payload=payload,
        runtime_scope_revision_id=canonical_sha256(payload),
    )


def _status_dict(
    scope: TodayMarketRuntimeScopeV1,
    configuration: TodayMarketMockRuntimeConfigurationV1,
    state: _RuntimeState,
) -> dict[str, Any]:
    explanation = _state_explanation(state.phase)
    allowed_actions: list[str] = []
    if (
        configuration.mock_enabled
        and state.automatic_attempt_state == "not_attempted"
        and state.phase == "prior_snapshot_ready"
    ):
        allowed_actions.append("automatic_first_entry")
    if state.phase in {"failed_retained_prior", "cancelled_retained_prior"}:
        allowed_actions.append("explicit_user_retry")
    candidate_fingerprint = (
        None
        if state.candidate_projection is None
        else state.candidate_projection["projection_fingerprint"]
    )
    failure_code = None if state.failure is None else state.failure["failure_code"]
    failure_category = (
        None if state.failure is None else state.failure["category"]
    )
    retryability = (
        None if state.failure is None else state.failure["retryability"]
    )
    fingerprint_payload = {
        "runtime_status_version": RUNTIME_STATUS_VERSION,
        "runtime_scope_revision_id": scope.runtime_scope_revision_id,
        "runtime_status_revision": state.runtime_status_revision,
        "phase": state.phase,
        "prior_snapshot_state": "available",
        "refresh_state": state.refresh_state,
        "source_mode": "synthetic_mock" if configuration.mock_enabled else "none",
        "is_synthetic": bool(state.candidate_projection),
        "mock_enabled": configuration.mock_enabled,
        "mock_scenario_id": configuration.mock_scenario_id,
        "automatic_attempt_state": state.automatic_attempt_state,
        "active_attempt_id": state.active_attempt_id,
        "plan_fingerprint": state.plan_fingerprint,
        "candidate_projection_fingerprint": candidate_fingerprint,
        "failure_code": failure_code,
        "failure_category": failure_category,
        "retryability": retryability,
        "allowed_action_codes": allowed_actions,
    }
    return {
        "runtime_status_version": RUNTIME_STATUS_VERSION,
        "runtime_scope": scope.to_dict(),
        "runtime_scope_revision_id": scope.runtime_scope_revision_id,
        "runtime_status_revision": state.runtime_status_revision,
        "phase": state.phase,
        "prior_snapshot_state": "available",
        "refresh_state": state.refresh_state,
        "source_mode": "synthetic_mock" if configuration.mock_enabled else "none",
        "source_label": (
            "确定性模拟数据"
            if configuration.mock_enabled
            else "未启用模拟更新"
        ),
        "is_synthetic": bool(state.candidate_projection),
        "mock_enabled": configuration.mock_enabled,
        "mock_scenario_id": configuration.mock_scenario_id,
        "automatic_attempt_state": state.automatic_attempt_state,
        "active_attempt_id": state.active_attempt_id,
        "plan_fingerprint": state.plan_fingerprint,
        "candidate_projection": state.candidate_projection,
        "failure": state.failure,
        "state_explanation": explanation,
        "allowed_actions": allowed_actions,
        "technical_details": {
            "collapsed_by_default": True,
            "process_local": True,
            "persisted_write": False,
            "network_used": False,
            "live_ths_gate": "Issue #225",
        },
        "runtime_status_fingerprint": canonical_sha256(fingerprint_payload),
    }


def _state_explanation(phase: str) -> dict[str, str]:
    copy = {
        "prior_snapshot_ready": (
            "本地市场快照已读取，模拟更新条件已准备。",
            "模拟结果只用于验证更新流程，不代表真实市场最新状态。",
            "系统将自动执行一次有界模拟更新。",
        ),
        "mock_not_enabled": (
            "当前应用未启用模拟更新。",
            "默认应用不会自动读取模拟数据，也不会访问真实数据源。",
            "继续阅读已选择的本地市场快照。",
        ),
        "refresh_in_progress": (
            "正在执行一次同步、有限的模拟更新。",
            "先前本地快照仍是当前权威内容。",
            "等待当前请求返回，不会启动后台轮询。",
        ),
        "demo_published": (
            "完整模拟候选已单独展示。",
            "它通过完整性校验，但不写入本地历史，也不代表真实市场数据。",
            "比较模拟候选与先前快照，或继续阅读本地快照。",
        ),
        "no_refresh_needed": (
            "当前范围不需要模拟补齐。",
            "服务端计划判断没有缺失的已完成交易日。",
            "继续阅读先前本地快照。",
        ),
        "not_initialized": (
            "当前范围没有可用的先前本地快照。",
            "模拟更新不能初始化真实市场历史。",
            "先完成明确的本地数据初始化流程。",
        ),
        "manual_catchup_required": (
            "缺失交易日超过自动模拟更新上限。",
            "系统不会把大范围补齐隐藏在一次自动请求中。",
            "使用后续明确授权的手动补齐流程。",
        ),
        "failed_retained_prior": (
            "模拟候选未通过完整性或运行校验。",
            "先前本地快照保持可见且未被修改。",
            "可以明确选择重新运行模拟演示。",
        ),
        "cancelled_retained_prior": (
            "模拟更新在发布前取消。",
            "没有部分结果替换先前本地快照。",
            "可以明确选择重新运行模拟演示。",
        ),
        "scope_stale": (
            "运行范围或先前快照已经变化。",
            "旧状态指纹不能用于新范围。",
            "重新读取本地快照和运行状态。",
        ),
    }.get(
        phase,
        (
            "当前运行状态无法解释。",
            "系统不会对未知状态作推断。",
            "重新读取本地快照和运行状态。",
        ),
    )
    return {
        "what_happened": copy[0],
        "why_it_matters": copy[1],
        "available_action": copy[2],
    }


def _phase_from_outcome(state: OrchestrationState) -> tuple[str, str]:
    return {
        OrchestrationState.NO_REFRESH_NEEDED: (
            "no_refresh_needed",
            "current",
        ),
        OrchestrationState.MANUAL_CATCHUP_REQUIRED: (
            "manual_catchup_required",
            "manual_required",
        ),
        OrchestrationState.NOT_INITIALIZED: (
            "not_initialized",
            "not_initialized",
        ),
        OrchestrationState.PUBLISHED_DEMO: (
            "demo_published",
            "succeeded",
        ),
        OrchestrationState.FAILED_RETAINED_PRIOR: (
            "failed_retained_prior",
            "failed",
        ),
        OrchestrationState.CANCELLED_RETAINED_PRIOR: (
            "cancelled_retained_prior",
            "cancelled",
        ),
    }[state]


def _serialize_projection(value: Any) -> dict[str, Any] | None:
    if value is None:
        return None
    return {
        "projection_version": value.projection_version,
        "is_synthetic": value.is_synthetic,
        "source_label": value.source_label,
        "production_live_source_ready": value.production_live_source_ready,
        "overall_live_gate": value.overall_live_gate,
        "message_zh": value.message_zh,
        "data_through_session": value.data_through_session.isoformat(),
        "family_item_counts": [list(item) for item in value.family_item_counts],
        "projection_fingerprint": value.projection_fingerprint,
    }


def _serialize_failure(value: Any) -> dict[str, Any] | None:
    if value is None:
        return None
    return {
        "failure_code": value.failure_code,
        "category": value.category.value,
        "refresh_attempt_id": value.refresh_attempt_id,
        "source_key": value.source_key,
        "redacted_details": list(value.redacted_details),
        "retryability": value.retryability.value,
    }


def _expected_completed_sessions(
    prior_session: date,
    cutoff: date,
) -> tuple[date, ...]:
    sessions = [prior_session]
    cursor = prior_session + timedelta(days=1)
    while cursor <= cutoff:
        if cursor.weekday() < 5:
            sessions.append(cursor)
        cursor += timedelta(days=1)
    return tuple(sessions)


def _parse_utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("timestamp must be timezone-aware")
    return parsed.astimezone(timezone.utc)
