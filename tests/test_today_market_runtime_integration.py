from __future__ import annotations

import copy
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from threading import Event, Lock

import pytest
from fastapi import FastAPI, HTTPException
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

import backend.today_market_refresh.runtime as runtime_module
from backend.api.today_market import TodayMarketBoundaries, TodayMarketSnapshotRequest
from backend.database.engine import build_session_factory
from backend.database.models import Base, IngestionRun
from backend.main import app as default_app
from backend.today_market_refresh import (
    MockScenario,
    RefreshTrigger,
    SnapshotReference,
    TodayMarketMockRuntimeConfigurationV1,
    TodayMarketPriorSnapshotContext,
    TodayMarketRuntimeCoordinator,
    build_prior_snapshot_context,
    build_runtime_scope,
    install_today_market_runtime,
)
from backend.today_market_refresh.mock import DeterministicTodayMarketMock
from backend.today_market_refresh.runtime import (
    RUNTIME_SCOPE_VERSION,
    RuntimeScopeConflict,
    RuntimeStatusConflict,
    _compare_command_scope,
    _validate_command,
)
from scripts.demo_today_market import (
    VISIBLE_AT,
    _boundaries,
    _fix_recorded_times,
    _ingest_benchmark,
    _ingest_equity,
    _ingest_sector,
)

ROOT = Path(__file__).parents[1]
FIXTURES = ROOT / "tests" / "fixtures" / "today_market_mock"


def _request(*, cutoff: date = date(2026, 7, 27)) -> TodayMarketSnapshotRequest:
    recorded = datetime(2026, 7, 27, 3, 0, tzinfo=timezone.utc)
    return TodayMarketSnapshotRequest(
        equity_series_key="equity-series-v1",
        benchmark_series_key=None,
        sector_series_key=None,
        boundaries=TodayMarketBoundaries(
            cutoff=cutoff,
            cutoff_compact=cutoff.strftime("%Y%m%d"),
            recorded_at=recorded,
            recorded_at_iso=recorded.isoformat().replace("+00:00", "Z"),
        ),
    )


def _prior(*, fingerprint: str = "a" * 64) -> TodayMarketPriorSnapshotContext:
    reference = SnapshotReference(
        snapshot_id="today-market-local-v1:test",
        data_through_session=date(2026, 7, 24),
        content_fingerprint=fingerprint,
    )
    return TodayMarketPriorSnapshotContext(
        snapshot_reference=reference,
        identity_payload={"id": reference.snapshot_id},
        content_payload={"fingerprint": fingerprint},
        projected_snapshot={"status": "complete_selected_scope"},
    )


def _enabled_config(
    scenario: MockScenario = MockScenario.STALE_SUCCESS,
) -> TodayMarketMockRuntimeConfigurationV1:
    return TodayMarketMockRuntimeConfigurationV1(
        mock_enabled=True,
        mock_scenario_id=scenario.value,
    )


class _BlockingCountingPort:
    def __init__(self) -> None:
        self.started = Event()
        self.release = Event()
        self._lock = Lock()
        self.call_count = 0
        self._inner = DeterministicTodayMarketMock(
            fixture_root=FIXTURES,
            scenario=MockScenario.STALE_SUCCESS,
        )

    def acquire(self, plan):
        with self._lock:
            self.call_count += 1
        self.started.set()
        assert self.release.wait(timeout=5)
        return self._inner.acquire(plan)


def test_default_application_is_mock_disabled_and_routes_are_installed() -> None:
    configuration = default_app.state.today_market_runtime_configuration
    assert configuration.mock_enabled is False
    assert configuration.mock_scenario_id is None
    paths = {
        route.path
        for route in default_app.routes
        if hasattr(route, "path")
    }
    assert "/today-market/api/runtime-status" in paths
    assert "/today-market/api/runtime-refresh" in paths


def test_mock_configuration_is_closed_and_application_owned() -> None:
    with pytest.raises(ValueError):
        TodayMarketMockRuntimeConfigurationV1(
            mock_enabled=True,
            mock_scenario_id=None,
        )
    with pytest.raises(ValueError):
        TodayMarketMockRuntimeConfigurationV1(
            mock_enabled=False,
            mock_scenario_id=MockScenario.STALE_SUCCESS.value,
        )
    demo_app = FastAPI()
    configuration = _enabled_config()
    install_today_market_runtime(
        demo_app,
        configuration=configuration,
        fixture_root=FIXTURES,
    )
    assert demo_app.state.today_market_runtime_configuration is configuration
    assert demo_app.state.today_market_runtime_fixture_root == FIXTURES


def test_scope_revision_is_single_authoritative_identity() -> None:
    base = build_runtime_scope(
        request=_request(),
        prior=_prior(),
        configuration=_enabled_config(),
    )
    changed_boundary = build_runtime_scope(
        request=_request(cutoff=date(2026, 7, 28)),
        prior=_prior(),
        configuration=_enabled_config(),
    )
    changed_prior = build_runtime_scope(
        request=_request(),
        prior=_prior(fingerprint="b" * 64),
        configuration=_enabled_config(),
    )
    changed_scenario = build_runtime_scope(
        request=_request(),
        prior=_prior(),
        configuration=_enabled_config(
            MockScenario.SYNTHETIC_CORRECTION_REVISION
        ),
    )
    assert base.runtime_scope_revision_id != changed_boundary.runtime_scope_revision_id
    assert base.runtime_scope_revision_id != changed_prior.runtime_scope_revision_id
    assert base.runtime_scope_revision_id != changed_scenario.runtime_scope_revision_id
    assert base.to_dict()["runtime_scope_revision_id"] == base.runtime_scope_revision_id


def test_disabled_status_has_zero_acquisition_path() -> None:
    scope = build_runtime_scope(
        request=_request(),
        prior=_prior(),
        configuration=TodayMarketMockRuntimeConfigurationV1(),
    )
    coordinator = TodayMarketRuntimeCoordinator()
    status = coordinator.get_status(scope, TodayMarketMockRuntimeConfigurationV1())
    assert status["phase"] == "mock_not_enabled"
    assert status["allowed_actions"] == []
    with pytest.raises(RuntimeScopeConflict):
        coordinator.execute(
            scope=scope,
            configuration=TodayMarketMockRuntimeConfigurationV1(),
            expected_runtime_status_fingerprint=status[
                "runtime_status_fingerprint"
            ],
            trigger=RefreshTrigger.FIRST_TODAY_MARKET_ENTRY,
            fixture_root=None,
        )


def test_same_scope_single_flight_and_completed_replay() -> None:
    configuration = _enabled_config()
    scope = build_runtime_scope(
        request=_request(),
        prior=_prior(),
        configuration=configuration,
    )
    port = _BlockingCountingPort()
    coordinator = TodayMarketRuntimeCoordinator(port_factory=lambda _: port)
    initial = coordinator.get_status(scope, configuration)
    expected = initial["runtime_status_fingerprint"]

    with ThreadPoolExecutor(max_workers=2) as executor:
        first = executor.submit(
            coordinator.execute,
            scope=scope,
            configuration=configuration,
            expected_runtime_status_fingerprint=expected,
            trigger=RefreshTrigger.FIRST_TODAY_MARKET_ENTRY,
            fixture_root=FIXTURES,
        )
        assert port.started.wait(timeout=5)
        with pytest.raises(RuntimeStatusConflict):
            coordinator.execute(
                scope=scope,
                configuration=configuration,
                expected_runtime_status_fingerprint=expected,
                trigger=RefreshTrigger.FIRST_TODAY_MARKET_ENTRY,
                fixture_root=FIXTURES,
            )
        port.release.set()
        completed = first.result(timeout=5)

    assert port.call_count == 1
    assert completed["phase"] == "demo_published"
    assert completed["candidate_projection"]["is_synthetic"] is True
    assert completed["runtime_status_fingerprint"] != expected

    replay = coordinator.execute(
        scope=scope,
        configuration=configuration,
        expected_runtime_status_fingerprint=expected,
        trigger=RefreshTrigger.FIRST_TODAY_MARKET_ENTRY,
        fixture_root=FIXTURES,
    )
    assert replay["runtime_status_fingerprint"] == completed[
        "runtime_status_fingerprint"
    ]
    assert port.call_count == 1


def test_stale_status_conflicts_before_new_acquisition() -> None:
    configuration = _enabled_config()
    scope = build_runtime_scope(
        request=_request(),
        prior=_prior(),
        configuration=configuration,
    )
    coordinator = TodayMarketRuntimeCoordinator()
    initial = coordinator.get_status(scope, configuration)
    with pytest.raises(RuntimeStatusConflict):
        coordinator.execute(
            scope=scope,
            configuration=configuration,
            expected_runtime_status_fingerprint="0" * 64,
            trigger=RefreshTrigger.FIRST_TODAY_MARKET_ENTRY,
            fixture_root=FIXTURES,
        )
    unchanged = coordinator.get_status(scope, configuration)
    assert unchanged["runtime_status_revision"] == initial["runtime_status_revision"]
    assert unchanged["candidate_projection"] is None


def test_closed_command_rejects_client_scenario_and_moved_prior() -> None:
    configuration = _enabled_config()
    prior = _prior()
    scope = build_runtime_scope(
        request=_request(),
        prior=prior,
        configuration=configuration,
    )
    status = TodayMarketRuntimeCoordinator().get_status(scope, configuration)
    command = {
        "runtime_scope_version": RUNTIME_SCOPE_VERSION,
        "runtime_scope_revision_id": scope.runtime_scope_revision_id,
        "prior_snapshot_id": prior.snapshot_reference.snapshot_id,
        "prior_snapshot_content_fingerprint": (
            prior.snapshot_reference.content_fingerprint
        ),
        "as_of_cutoff": scope.payload["as_of_cutoff"],
        "as_of_recorded_at_utc": scope.payload["as_of_recorded_at_utc"],
        "equity_series_key": scope.payload["equity_series_key"],
        "benchmark_series_key": None,
        "sector_series_key": None,
        "trigger": RefreshTrigger.FIRST_TODAY_MARKET_ENTRY.value,
        "expected_runtime_status_fingerprint": status[
            "runtime_status_fingerprint"
        ],
    }
    with pytest.raises(HTTPException) as unknown:
        _validate_command({**command, "mock_scenario_id": "stale_success"})
    assert unknown.value.detail["code"] == "runtime_request_unknown_field"

    moved = _prior(fingerprint="c" * 64)
    with pytest.raises(HTTPException) as conflict:
        _compare_command_scope(command, scope, moved)
    assert conflict.value.status_code == 409
    assert conflict.value.detail["code"] == "runtime_prior_snapshot_moved"


def test_authoritative_snapshot_context_is_repeatable_and_fails_when_moved(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = build_session_factory(engine)
    try:
        equity = _ingest_equity(session_factory)
        benchmark = _ingest_benchmark(session_factory)
        sector = _ingest_sector(session_factory)
        _fix_recorded_times(
            session_factory,
            equity.ingestion_run_id,
            benchmark.ingestion_run_id,
            sector.ingestion_run_id,
        )
        request = TodayMarketSnapshotRequest(
            equity_series_key=equity.series_key,
            benchmark_series_key=benchmark.series_key,
            sector_series_key=sector.series_key,
            boundaries=_boundaries(VISIBLE_AT),
        )
        first = build_prior_snapshot_context(request, session_factory)
        second = build_prior_snapshot_context(request, session_factory)
        assert first.snapshot_reference == second.snapshot_reference
        assert first.identity_payload == second.identity_payload
        assert first.content_payload == second.content_payload

        projected_domain = first.projected_snapshot["technical_details"][
            "raw_market_cockpit_snapshot"
        ]
        canonical_domain = first.content_payload[
            "market_cockpit_domain_snapshot"
        ]
        assert "generated_at_utc" in projected_domain["provenance"]
        assert "generated_at_utc" not in canonical_domain["provenance"]
        for context_key in ("benchmark_context", "sector_context"):
            assert (
                "generated_at_utc"
                in projected_domain[context_key]["provenance"]
            )
            assert (
                "generated_at_utc"
                not in canonical_domain[context_key]["provenance"]
            )

        original_snapshot_read = runtime_module.today_market_snapshot

        def changed_domain_snapshot(*args, **kwargs):
            changed = copy.deepcopy(original_snapshot_read(*args, **kwargs))
            raw = changed["technical_details"]["raw_market_cockpit_snapshot"]
            raw["available_stock_count"] += 1
            return changed

        monkeypatch.setattr(
            runtime_module,
            "today_market_snapshot",
            changed_domain_snapshot,
        )
        changed = build_prior_snapshot_context(request, session_factory)
        assert changed.snapshot_reference.snapshot_id == first.snapshot_reference.snapshot_id
        assert (
            changed.snapshot_reference.content_fingerprint
            != first.snapshot_reference.content_fingerprint
        )

        with session_factory.begin() as session:
            run = session.get(IngestionRun, equity.ingestion_run_id)
            assert run is not None
            run.completed_at = VISIBLE_AT + timedelta(seconds=1)
        with pytest.raises(HTTPException):
            build_prior_snapshot_context(request, session_factory)
    finally:
        engine.dispose()


def test_page_contract_has_one_automatic_attempt_and_no_polling() -> None:
    html = (ROOT / "today_market" / "static" / "today_market.html").read_text(
        encoding="utf-8"
    )
    assert "/today-market/api/runtime-status" in html
    assert "/today-market/api/runtime-refresh" in html
    assert 'id="runtime-retry"' in html
    assert "first_today_market_entry" in html
    assert "explicit_user_retry" in html
    assert "MutationObserver" in html
    assert "setInterval" not in html
    assert "模拟结果与本地市场快照分开展示" in html
    assert 'id="mock-scenario' not in html
    assert "localStorage.setItem" not in html.split(
        '<section id="runtime-panel"', 1
    )[1]
