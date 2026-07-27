"""Process-local Mock-only Today Market runtime integration."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from threading import RLock
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from backend.api.today_market import (
    TodayMarketBoundaries,
    TodayMarketSnapshotRequest,
    get_today_market_session_factory,
    require_today_market_snapshot_request,
    today_market_snapshot,
)
from backend.database import build_engine, build_session_factory
from backend.database.benchmark_data import BENCHMARK_DATASET
from backend.database.models import IngestionRun
from backend.database.sector_data import SECTOR_DATASET
from backend.database.series import (
    BenchmarkSeriesIdentity,
    SectorSeriesIdentity,
    SnapshotSeriesError,
    SnapshotSeriesIdentity,
    validate_benchmark_series_identity,
    validate_sector_series_identity,
    validate_series_key,
    validate_snapshot_series_identity,
)
from market_cockpit.repository import MARKET_DATASET

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
SNAPSHOT_IDENTITY_VERSION = "aquantai.today-market-local-snapshot-identity.v1"
SNAPSHOT_CONTENT_VERSION = "aquantai.today-market-local-snapshot-content.v1"

router = APIRouter(prefix="/today-market/api", tags=["today-market-runtime"])

_DATASET_BY_FAMILY = {
    "equity": MARKET_DATASET,
    "benchmark": BENCHMARK_DATASET,
    "sector": SECTOR_DATASET,
}
_ALLOWED_COMMAND_FIELDS = {
    "runtime_scope_version",
    "runtime_scope_revision_id",
    "prior_snapshot_id",
    "prior_snapshot_content_fingerprint",
    "as_of_cutoff",
    "as_of_recorded_at_utc",
    "equity_series_key",
    "benchmark_series_key",
    "sector_series_key",
    "trigger",
    "expected_runtime_status_fingerprint",
}
_ALLOWED_TRIGGERS = {
    RefreshTrigger.FIRST_TODAY_MARKET_ENTRY,
    RefreshTrigger.EXPLICIT_USER_RETRY,
}
_DOMAIN_SNAPSHOT_KEYS = (
    "provenance",
    "universe_stock_count",
    "available_stock_count",
    "scope_coverage_status",
    "calculation_status",
    "completeness_status",
    "warnings",
    "price_behavior_context",
    "liquidity_context",
    "benchmark_context",
    "sector_context",
    "latest_data_diagnostics",
)


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


def build_prior_snapshot_context(
    request: TodayMarketSnapshotRequest,
    session_factory: sessionmaker[Session],
) -> TodayMarketPriorSnapshotContext:
    projected = today_market_snapshot(
        request=request,
        session_factory=session_factory,
    )
    raw = projected["technical_details"]["raw_market_cockpit_snapshot"]
    components: list[dict[str, Any] | None] = []
    with session_factory() as session:
        for family, series_key in (
            ("equity", request.equity_series_key),
            ("benchmark", request.benchmark_series_key),
            ("sector", request.sector_series_key),
        ):
            components.append(
                None
                if series_key is None
                else _authoritative_component(
                    session,
                    family=family,
                    series_key=series_key,
                    boundaries=request.boundaries,
                )
            )
    equity_component = components[0]
    if equity_component is None:
        raise RuntimeError("equity component is required")
    components[0] = _bind_component_to_service(
        equity_component,
        raw.get("provenance"),
        effective_session_key="effective_as_of_session",
    )
    benchmark_component = components[1]
    benchmark_context = raw.get("benchmark_context")
    if benchmark_component is not None:
        components[1] = _bind_component_to_service(
            benchmark_component,
            (
                benchmark_context.get("provenance")
                if isinstance(benchmark_context, Mapping)
                else None
            ),
            effective_session_key="effective_benchmark_session",
        )
    sector_component = components[2]
    sector_context = raw.get("sector_context")
    if sector_component is not None:
        components[2] = _bind_component_to_service(
            sector_component,
            (
                sector_context.get("provenance")
                if isinstance(sector_context, Mapping)
                else None
            ),
            effective_session_key="effective_sector_session",
        )

    identity_payload = {
        "snapshot_identity_version": SNAPSHOT_IDENTITY_VERSION,
        "as_of_cutoff": request.boundaries.cutoff.isoformat(),
        "as_of_recorded_at_utc": request.boundaries.recorded_at_iso,
        "selected_components": components,
        "market_snapshot_contract_version": raw.get(
            "snapshot_contract_version",
            raw.get("contract_version", "market-cockpit-domain-snapshot"),
        ),
    }
    content_payload = {
        "snapshot_content_version": SNAPSHOT_CONTENT_VERSION,
        "identity_payload": identity_payload,
        "market_cockpit_domain_snapshot": (
            _canonical_market_cockpit_domain_snapshot(raw)
        ),
    }
    effective_session = date.fromisoformat(
        projected["scope_and_freshness"]["effective_equity_session"]
    )
    return TodayMarketPriorSnapshotContext(
        snapshot_reference=SnapshotReference(
            snapshot_id=(
                "today-market-local-v1:" + canonical_sha256(identity_payload)
            ),
            data_through_session=effective_session,
            content_fingerprint=canonical_sha256(content_payload),
        ),
        identity_payload=identity_payload,
        content_payload=content_payload,
        projected_snapshot=projected,
    )


@router.get("/runtime-status")
def today_market_runtime_status(
    http_request: Request,
    snapshot_request: TodayMarketSnapshotRequest = Depends(
        require_today_market_snapshot_request
    ),
    session_factory: sessionmaker[Session] = Depends(
        get_today_market_session_factory
    ),
) -> dict[str, Any]:
    try:
        prior = build_prior_snapshot_context(snapshot_request, session_factory)
        configuration, _, coordinator = _app_runtime_dependencies(http_request)
        scope = build_runtime_scope(
            request=snapshot_request,
            prior=prior,
            configuration=configuration,
        )
        return coordinator.get_status(scope, configuration)
    except RuntimeScopeConflict as exc:
        raise _error(
            409,
            "runtime_scope_identity_conflict",
            "本地快照身份与权威读取结果不一致，请重新读取。",
        ) from exc


@router.post("/runtime-refresh")
def today_market_runtime_refresh(
    http_request: Request,
    payload: dict[str, Any] = Body(...),
) -> dict[str, Any]:
    command = _validate_command(payload)
    snapshot_request = _snapshot_request_from_command(command)
    try:
        engine = build_engine()
    except RuntimeError as exc:
        raise _error(
            503,
            "runtime_database_unavailable",
            "本地数据库不可用，模拟更新未执行。",
        ) from exc
    try:
        session_factory = build_session_factory(engine)
        prior = build_prior_snapshot_context(snapshot_request, session_factory)
        configuration, fixture_root, coordinator = _app_runtime_dependencies(
            http_request
        )
        scope = build_runtime_scope(
            request=snapshot_request,
            prior=prior,
            configuration=configuration,
        )
        _compare_command_scope(command, scope, prior)
        try:
            trigger = RefreshTrigger(str(command["trigger"]))
        except ValueError as exc:
            raise _error(
                422,
                "runtime_trigger_not_allowed",
                "当前触发方式未获授权。",
            ) from exc
        try:
            return coordinator.execute(
                scope=scope,
                configuration=configuration,
                expected_runtime_status_fingerprint=str(
                    command["expected_runtime_status_fingerprint"]
                ),
                trigger=trigger,
                fixture_root=fixture_root,
            )
        except RuntimeStatusConflict as exc:
            current = coordinator.get_status(scope, configuration)
            raise HTTPException(
                status_code=409,
                detail={
                    "code": "runtime_status_conflict",
                    "message": "运行状态已变化，请使用最新状态重试。",
                    "current_status": current,
                },
            ) from exc
        except RuntimeScopeConflict as exc:
            raise _error(
                409,
                "runtime_mock_not_enabled",
                "当前应用未启用模拟更新。",
            ) from exc
        except ValueError as exc:
            raise _error(
                422,
                "runtime_trigger_not_allowed",
                "当前状态不允许此操作。",
            ) from exc
    except RuntimeScopeConflict as exc:
        raise _error(
            409,
            "runtime_scope_identity_conflict",
            "本地快照身份与权威读取结果不一致，请重新读取。",
        ) from exc
    except SQLAlchemyError as exc:
        raise _error(
            503,
            "runtime_database_unavailable",
            "本地数据库读取失败，模拟更新未执行。",
        ) from exc
    except RuntimeError as exc:
        raise _error(
            500,
            "runtime_internal_validation_failed",
            "模拟更新内部校验失败，先前本地快照保持不变。",
        ) from exc
    finally:
        engine.dispose()


def _canonical_market_cockpit_domain_snapshot(
    raw: Mapping[str, Any],
) -> dict[str, Any]:
    """Exclude request-time clocks without mutating the projected snapshot."""

    domain = {key: raw.get(key) for key in _DOMAIN_SNAPSHOT_KEYS}
    domain["provenance"] = _canonical_domain_provenance(
        domain.get("provenance")
    )
    domain["benchmark_context"] = _canonical_domain_context(
        domain.get("benchmark_context")
    )
    domain["sector_context"] = _canonical_domain_context(
        domain.get("sector_context")
    )
    return domain


def _canonical_domain_context(value: Any) -> Any:
    if not isinstance(value, Mapping):
        return value
    context = dict(value)
    context["provenance"] = _canonical_domain_provenance(
        context.get("provenance")
    )
    return context


def _canonical_domain_provenance(value: Any) -> Any:
    if not isinstance(value, Mapping):
        return value
    return {
        key: item
        for key, item in value.items()
        if key != "generated_at_utc"
    }


def _authoritative_component(
    session: Session,
    *,
    family: str,
    series_key: str,
    boundaries: TodayMarketBoundaries,
) -> dict[str, Any]:
    dataset = _DATASET_BY_FAMILY[family]
    run = session.scalar(
        select(IngestionRun)
        .where(
            IngestionRun.dataset == dataset,
            IngestionRun.series_key == series_key,
            IngestionRun.status == "succeeded",
            IngestionRun.snapshot_mode == "complete",
            IngestionRun.information_cutoff_date <= boundaries.cutoff,
            IngestionRun.imported_at <= boundaries.recorded_at,
            IngestionRun.completed_at.is_not(None),
            IngestionRun.completed_at <= boundaries.recorded_at,
        )
        .order_by(
            IngestionRun.information_cutoff_date.desc(),
            IngestionRun.completed_at.desc(),
            IngestionRun.id.desc(),
        )
        .limit(1)
    )
    if run is None or run.completed_at is None:
        raise RuntimeScopeConflict("authoritative ingestion run is unavailable")
    raw_identity = dict(run.series_identity)
    if family == "equity":
        canonical_identity = dict(
            validate_snapshot_series_identity(
                SnapshotSeriesIdentity(run.series_key, raw_identity)
            ).canonical
        )
    elif family == "benchmark":
        canonical_identity = dict(
            validate_benchmark_series_identity(
                BenchmarkSeriesIdentity(run.series_key, raw_identity)
            ).canonical
        )
    elif family == "sector":
        canonical_identity = dict(
            validate_sector_series_identity(
                SectorSeriesIdentity(run.series_key, raw_identity)
            ).canonical
        )
    else:
        raise RuntimeScopeConflict("unsupported authoritative snapshot family")
    return {
        "family_key": family,
        "ingestion_run_id": run.id,
        "dataset": run.dataset,
        "provider": run.provider,
        "series_key": run.series_key,
        "information_cutoff_date": run.information_cutoff_date.isoformat(),
        "imported_at_utc": _utc_iso(run.imported_at),
        "completed_at_utc": _utc_iso(run.completed_at),
        "snapshot_mode": run.snapshot_mode,
        "effective_session": None,
        "canonical_series_identity": canonical_identity,
    }


def _bind_component_to_service(
    component: dict[str, Any],
    provenance: Mapping[str, Any] | None,
    *,
    effective_session_key: str,
) -> dict[str, Any]:
    if not isinstance(provenance, Mapping):
        raise RuntimeScopeConflict("service provenance is unavailable")
    expected = {
        "ingestion_run_id": component["ingestion_run_id"],
        "provider": component["provider"],
        "series_key": component["series_key"],
    }
    for field, value in expected.items():
        if provenance.get(field) != value:
            raise RuntimeScopeConflict(
                f"service/repository {field} disagreement"
            )
    effective_session = provenance.get(effective_session_key)
    if effective_session is None:
        raise RuntimeScopeConflict("service effective session is unavailable")
    return {**component, "effective_session": str(effective_session)}


def _validate_command(payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise _error(
            422,
            "runtime_request_unknown_field",
            "运行请求必须是封闭的 JSON 对象。",
        )
    unknown = sorted(set(payload) - _ALLOWED_COMMAND_FIELDS)
    missing = sorted(_ALLOWED_COMMAND_FIELDS - set(payload))
    if unknown:
        raise _error(
            422,
            "runtime_request_unknown_field",
            f"运行请求包含未授权字段：{', '.join(unknown)}。",
        )
    if missing:
        raise _error(
            422,
            "runtime_request_missing_field",
            f"运行请求缺少字段：{', '.join(missing)}。",
        )
    return payload


def _snapshot_request_from_command(
    command: Mapping[str, Any],
) -> TodayMarketSnapshotRequest:
    try:
        cutoff = date.fromisoformat(str(command["as_of_cutoff"]))
        recorded = _parse_utc(str(command["as_of_recorded_at_utc"]))
        equity = validate_series_key(str(command["equity_series_key"]))
        benchmark_raw = command["benchmark_series_key"]
        sector_raw = command["sector_series_key"]
        benchmark = (
            None
            if benchmark_raw is None
            else validate_series_key(str(benchmark_raw))
        )
        sector = (
            None if sector_raw is None else validate_series_key(str(sector_raw))
        )
    except (ValueError, TypeError, SnapshotSeriesError) as exc:
        raise _error(
            422,
            "runtime_scope_stale",
            "运行请求中的边界或数据选择无效。",
        ) from exc
    return TodayMarketSnapshotRequest(
        equity_series_key=equity,
        benchmark_series_key=benchmark,
        sector_series_key=sector,
        boundaries=TodayMarketBoundaries(
            cutoff=cutoff,
            cutoff_compact=cutoff.strftime("%Y%m%d"),
            recorded_at=recorded,
            recorded_at_iso=_utc_iso(recorded),
        ),
    )


def _compare_command_scope(
    command: Mapping[str, Any],
    scope: TodayMarketRuntimeScopeV1,
    prior: TodayMarketPriorSnapshotContext,
) -> None:
    if str(command["runtime_scope_version"]) != RUNTIME_SCOPE_VERSION:
        raise _error(
            409,
            "runtime_scope_stale",
            "运行范围版本已变化，请重新读取状态。",
        )
    if str(command["prior_snapshot_id"]) != prior.snapshot_reference.snapshot_id:
        raise _error(
            409,
            "runtime_prior_snapshot_moved",
            "先前本地快照已变化，请重新读取。",
        )
    if (
        str(command["prior_snapshot_content_fingerprint"])
        != prior.snapshot_reference.content_fingerprint
    ):
        raise _error(
            409,
            "runtime_prior_snapshot_moved",
            "先前本地快照内容已变化，请重新读取。",
        )
    if (
        str(command["runtime_scope_revision_id"])
        != scope.runtime_scope_revision_id
    ):
        raise _error(
            409,
            "runtime_scope_stale",
            "运行范围已变化，请重新读取状态。",
        )


def _app_runtime_dependencies(
    request: Request,
) -> tuple[
    TodayMarketMockRuntimeConfigurationV1,
    Path | None,
    TodayMarketRuntimeCoordinator,
]:
    configuration = getattr(
        request.app.state,
        "today_market_runtime_configuration",
        TodayMarketMockRuntimeConfigurationV1(),
    )
    fixture_root = getattr(
        request.app.state,
        "today_market_runtime_fixture_root",
        None,
    )
    coordinator = getattr(
        request.app.state,
        "today_market_runtime_coordinator",
        None,
    )
    if coordinator is None:
        coordinator = TodayMarketRuntimeCoordinator()
        request.app.state.today_market_runtime_coordinator = coordinator
    return configuration, fixture_root, coordinator


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


def _utc_iso(value: datetime) -> str:
    parsed = value
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _error(status: int, code: str, message: str) -> HTTPException:
    return HTTPException(status_code=status, detail={"code": code, "message": message})
