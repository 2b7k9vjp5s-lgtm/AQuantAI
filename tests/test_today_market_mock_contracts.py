from __future__ import annotations

import ast
from dataclasses import FrozenInstanceError
from datetime import date, datetime, timedelta, timezone
import importlib
from pathlib import Path

import pytest

from backend.today_market_refresh import (
    DEFAULT_MOCK_ASSUMPTION,
    MOCK_ASSUMPTION_PROFILE_ID,
    REQUIRED_CAPABILITY_FAMILIES,
    SYNTHETIC_SOURCE_KEY,
    DeterministicTodayMarketMock,
    MockPlanningAssumption,
    MockScenario,
    MockUsageState,
    OrchestrationState,
    PlanningState,
    RefreshTrigger,
    SnapshotReference,
    TodayMarketAcquisitionError,
    TodayMarketRefreshIntent,
    build_refresh_plan,
    canonical_json_bytes,
    canonical_sha256,
    run_mock_refresh,
)

ROOT = Path(__file__).parents[1]
PACKAGE_ROOT = ROOT / "backend" / "today_market_refresh"
FIXTURES = Path(__file__).parent / "fixtures" / "today_market_mock"
FORBIDDEN_MODULE_PREFIXES = (
    "requests",
    "httpx",
    "urllib.request",
    "socket",
    "subprocess",
    "sqlalchemy",
    "psycopg",
    "sqlite3",
)


def _intent(
    *, prior_id: str | None = "snapshot-prior", second: int = 0
) -> TodayMarketRefreshIntent:
    return TodayMarketRefreshIntent(
        scope_revision_id="scope-synthetic-v1",
        trigger=RefreshTrigger.APPLICATION_START,
        prior_snapshot_id=prior_id,
        local_clock_utc=datetime(2026, 7, 27, 1, 0, second, tzinfo=timezone.utc),
    )


def _prior(day: date = date(2026, 7, 24)) -> SnapshotReference:
    return SnapshotReference(
        snapshot_id="snapshot-prior",
        data_through_session=day,
        content_fingerprint="a" * 64,
    )


def _sessions(
    count: int, *, start: date = date(2026, 7, 24)
) -> tuple[date, ...]:
    return tuple(start + timedelta(days=index) for index in range(count))


def _build_current_ths_plan():  # type: ignore[no-untyped-def]
    """Resolve Stage C0 modules at call time so existing reload tests remain valid."""

    planner = importlib.import_module("datasource.ths_structured_provider.planner")
    readiness = importlib.import_module("datasource.ths_structured_provider.readiness")
    selectors = importlib.import_module("datasource.ths_structured_provider.selectors")
    return planner.build_index_history_plan(
        selectors.IndexHistorySelector("SYNTH.IDX.C0", 1000, 2000),
        readiness.CapabilityReadiness(),
    )


def test_mock_assumption_is_frozen_synthetic_and_non_production() -> None:
    assert DEFAULT_MOCK_ASSUMPTION.profile_id == MOCK_ASSUMPTION_PROFILE_ID
    assert DEFAULT_MOCK_ASSUMPTION.mock_qps == 5
    assert DEFAULT_MOCK_ASSUMPTION.mock_concurrency == 2
    assert DEFAULT_MOCK_ASSUMPTION.mock_daily_request_budget == 50_000
    assert DEFAULT_MOCK_ASSUMPTION.provider_confirmed is False
    assert DEFAULT_MOCK_ASSUMPTION.production_eligible is False
    with pytest.raises(FrozenInstanceError):
        DEFAULT_MOCK_ASSUMPTION.mock_qps = 99  # type: ignore[misc]
    with pytest.raises(ValueError, match="exact reviewed"):
        MockPlanningAssumption(mock_qps=6)
    with pytest.raises(ValueError, match="exact reviewed"):
        MockPlanningAssumption(mock_concurrency=3)
    with pytest.raises(ValueError, match="exact reviewed"):
        MockPlanningAssumption(mock_daily_request_budget=50_001)
    with pytest.raises(ValueError, match="exact reviewed"):
        MockPlanningAssumption(provider_confirmed=True)
    with pytest.raises(ValueError, match="exact reviewed"):
        MockPlanningAssumption(production_eligible=True)


def test_canonical_fingerprint_is_stable_and_requires_aware_datetime() -> None:
    left = {
        "b": 2,
        "a": {
            "time": datetime(2026, 7, 27, tzinfo=timezone.utc),
            "x": 1,
        },
    }
    right = {
        "a": {
            "x": 1,
            "time": datetime(2026, 7, 27, tzinfo=timezone.utc),
        },
        "b": 2,
    }
    assert canonical_json_bytes(left) == canonical_json_bytes(right)
    assert canonical_sha256(left) == canonical_sha256(right)
    with pytest.raises(ValueError, match="timezone-aware"):
        canonical_json_bytes({"time": datetime(2026, 7, 27)})


def test_planner_supports_one_and_ten_sessions_and_blocks_larger_gap() -> None:
    one = build_refresh_plan(
        _intent(),
        expected_completed_sessions=_sessions(2),
        prior_snapshot=_prior(),
        capability_set=REQUIRED_CAPABILITY_FAMILIES,
    )
    assert one.state is PlanningState.ACQUISITION_REQUIRED
    assert one.plan is not None
    assert one.plan.requested_completed_sessions == (date(2026, 7, 25),)
    assert one.plan.verify_fingerprint()

    ten = build_refresh_plan(
        _intent(),
        expected_completed_sessions=_sessions(11),
        prior_snapshot=_prior(),
        capability_set=REQUIRED_CAPABILITY_FAMILIES,
    )
    assert ten.state is PlanningState.ACQUISITION_REQUIRED
    assert ten.plan is not None
    assert len(ten.plan.requested_completed_sessions) == 10

    too_many = build_refresh_plan(
        _intent(),
        expected_completed_sessions=_sessions(12),
        prior_snapshot=_prior(),
        capability_set=REQUIRED_CAPABILITY_FAMILIES,
    )
    assert too_many.state is PlanningState.MANUAL_CATCHUP_REQUIRED
    assert too_many.plan is None


def test_planner_has_explicit_current_and_not_initialized_states() -> None:
    current = build_refresh_plan(
        _intent(),
        expected_completed_sessions=(date(2026, 7, 24),),
        prior_snapshot=_prior(),
        capability_set=REQUIRED_CAPABILITY_FAMILIES,
    )
    assert current.state is PlanningState.CURRENT
    assert current.plan is None

    not_initialized = build_refresh_plan(
        _intent(prior_id=None),
        expected_completed_sessions=(date(2026, 7, 24),),
        prior_snapshot=None,
        capability_set=REQUIRED_CAPABILITY_FAMILIES,
    )
    assert not_initialized.state is PlanningState.NOT_INITIALIZED
    assert not_initialized.plan is None


def test_success_is_deterministic_synthetic_and_does_not_change_ths_readiness() -> None:
    prior = _prior()
    first_adapter = DeterministicTodayMarketMock(
        fixture_root=FIXTURES,
        scenario=MockScenario.STALE_SUCCESS,
    )
    second_adapter = DeterministicTodayMarketMock(
        fixture_root=FIXTURES,
        scenario=MockScenario.STALE_SUCCESS,
    )
    kwargs = dict(
        intent=_intent(),
        expected_completed_sessions=_sessions(2),
        prior_snapshot=prior,
        capability_set=REQUIRED_CAPABILITY_FAMILIES,
    )
    before = _build_current_ths_plan()
    first = run_mock_refresh(port=first_adapter, **kwargs)
    second = run_mock_refresh(port=second_adapter, **kwargs)
    after = _build_current_ths_plan()

    assert first.state is OrchestrationState.PUBLISHED_DEMO
    assert first.candidate_projection is not None
    assert first.candidate_projection.is_synthetic is True
    assert first.candidate_projection.source_label == "模拟数据"
    assert first.candidate_projection.production_live_source_ready is False
    assert second.candidate_projection is not None
    assert (
        first.candidate_projection.projection_fingerprint
        == second.candidate_projection.projection_fingerprint
    )
    assert first.plan is not None and second.plan is not None
    assert first.plan.plan_fingerprint == second.plan.plan_fingerprint

    decision = build_refresh_plan(
        _intent(),
        expected_completed_sessions=_sessions(2),
        prior_snapshot=prior,
        capability_set=REQUIRED_CAPABILITY_FAMILIES,
    )
    assert decision.plan is not None
    batch = DeterministicTodayMarketMock(fixture_root=FIXTURES).acquire(
        decision.plan
    )
    with pytest.raises(TypeError):
        batch.family_results[0].payload["mutate"] = True  # type: ignore[index]

    assert before.remote_executable is False and after.remote_executable is False
    assert before.live_readiness_candidate == after.live_readiness_candidate == "blocked"


def test_qps_concurrency_and_daily_budget_use_injected_state_without_sleep() -> None:
    decision = build_refresh_plan(
        _intent(),
        expected_completed_sessions=_sessions(2),
        prior_snapshot=_prior(),
        capability_set=REQUIRED_CAPABILITY_FAMILIES,
    )
    assert decision.plan is not None
    plan = decision.plan

    concurrency = DeterministicTodayMarketMock(
        fixture_root=FIXTURES,
        usage_state=MockUsageState(active_requests=2),
    )
    with pytest.raises(TodayMarketAcquisitionError) as concurrency_error:
        concurrency.acquire(plan)
    assert concurrency_error.value.failure.failure_code == "mock_concurrency_exceeded"

    qps_state = MockUsageState()
    qps_adapter = DeterministicTodayMarketMock(
        fixture_root=FIXTURES,
        usage_state=qps_state,
    )
    for _ in range(5):
        qps_adapter.acquire(plan)
    with pytest.raises(TodayMarketAcquisitionError) as qps_error:
        qps_adapter.acquire(plan)
    assert qps_error.value.failure.failure_code == "mock_qps_exceeded"

    daily_state = MockUsageState(
        daily_requests={plan.recorded_at_utc.date().isoformat(): 50_000}
    )
    daily_adapter = DeterministicTodayMarketMock(
        fixture_root=FIXTURES,
        usage_state=daily_state,
    )
    with pytest.raises(TodayMarketAcquisitionError) as daily_error:
        daily_adapter.acquire(plan)
    assert daily_error.value.failure.failure_code == "mock_daily_budget_exhausted"


def test_contracts_have_no_credential_fields_and_package_has_no_forbidden_imports() -> None:
    sentinel = "SENTINEL_API_KEY_DO_NOT_LEAK"
    with pytest.raises(TypeError) as exc:
        TodayMarketRefreshIntent(  # type: ignore[call-arg]
            scope_revision_id="scope",
            trigger=RefreshTrigger.APPLICATION_START,
            prior_snapshot_id=None,
            local_clock_utc=datetime(2026, 7, 27, tzinfo=timezone.utc),
            api_key=sentinel,
        )
    assert sentinel not in str(exc.value)

    for path in PACKAGE_ROOT.glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                modules = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                modules = [node.module or ""]
            else:
                continue
            for module in modules:
                assert not module.startswith(FORBIDDEN_MODULE_PREFIXES), (
                    f"{path} imports forbidden module {module}"
                )


def test_import_and_demo_are_network_environment_and_subprocess_free(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import os
    import socket
    import subprocess
    import urllib.request

    import httpx

    def denied(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise AssertionError("Today Market Mock attempted a prohibited side effect")

    monkeypatch.setattr(socket, "socket", denied)
    monkeypatch.setattr(socket, "create_connection", denied)
    monkeypatch.setattr(socket, "getaddrinfo", denied)
    monkeypatch.setattr(httpx.Client, "request", denied)
    monkeypatch.setattr(httpx.AsyncClient, "request", denied)
    monkeypatch.setattr(urllib.request, "urlopen", denied)
    monkeypatch.setattr(subprocess, "run", denied)
    monkeypatch.setattr(subprocess, "Popen", denied)
    monkeypatch.setattr(os, "getenv", denied)

    modules = (
        "backend.today_market_refresh.fingerprint",
        "backend.today_market_refresh.contracts",
        "backend.today_market_refresh.planner",
        "backend.today_market_refresh.port",
        "backend.today_market_refresh.mock",
        "backend.today_market_refresh.projection",
        "backend.today_market_refresh.orchestrator",
        "backend.today_market_refresh",
    )
    for module_name in modules:
        importlib.import_module(module_name)
    demo = importlib.import_module("scripts.demo_today_market_mock_refresh")
    summary = demo.build_demo_summary()
    assert summary["state"] == "published_demo"
    assert summary["is_synthetic"] is True
    assert summary["source_key"] == SYNTHETIC_SOURCE_KEY
