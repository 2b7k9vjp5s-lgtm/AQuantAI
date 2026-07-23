from __future__ import annotations

from collections.abc import Iterator
from datetime import datetime, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import backend.api.today_market as today_market_api
from backend.api.today_market import get_today_market_session_factory
from backend.database.benchmark_data import BenchmarkPersistenceService
from backend.database.engine import build_session_factory
from backend.database.market_data import MarketDataPersistenceService
from backend.database.models import Base, IngestionRun
from backend.database.sector_data import SectorPersistenceService
from backend.main import app
from market_cockpit.benchmark_fixtures import (
    BENCHMARK_FIXTURE_CODES,
    BENCHMARK_FIXTURE_CURRENT_CUTOFF,
    BENCHMARK_FIXTURE_END_DATE,
    BENCHMARK_FIXTURE_PROVIDER,
    BENCHMARK_FIXTURE_SCOPE,
    BENCHMARK_FIXTURE_START_DATE,
    build_benchmark_fixture,
)
from market_cockpit.fixtures import (
    COCKPIT_FIXTURE_ADJUST_TYPE,
    COCKPIT_FIXTURE_CURRENT_CUTOFF,
    COCKPIT_FIXTURE_END_DATE,
    COCKPIT_FIXTURE_PROVIDER,
    COCKPIT_FIXTURE_SCOPE,
    COCKPIT_FIXTURE_START_DATE,
    build_market_cockpit_fixture,
)
from market_cockpit.repository import MarketCockpitRepository
from market_cockpit.sector_fixtures import (
    SECTOR_FIXTURE_CODES,
    SECTOR_FIXTURE_CURRENT_CUTOFF,
    SECTOR_FIXTURE_END_DATE,
    SECTOR_FIXTURE_PROVIDER,
    SECTOR_FIXTURE_SCOPE,
    SECTOR_FIXTURE_START_DATE,
    build_sector_fixture,
)


VISIBLE_AT = datetime(2026, 4, 6, 12, 0, tzinfo=timezone.utc)
EARLY_AT = datetime(2026, 4, 5, 8, 0, tzinfo=timezone.utc)


@pytest.fixture
def database() -> Iterator[tuple[Engine, sessionmaker[Session]]]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    yield engine, build_session_factory(engine)
    engine.dispose()


@pytest.fixture
def client(database) -> Iterator[tuple[TestClient, sessionmaker[Session]]]:
    _, session_factory = database
    app.dependency_overrides[get_today_market_session_factory] = lambda: session_factory
    try:
        yield TestClient(app), session_factory
    finally:
        app.dependency_overrides.clear()


def _ingest_equity(session_factory: sessionmaker[Session], *, revision: str = "current"):
    return MarketDataPersistenceService(session_factory).ingest_bundle(
        build_market_cockpit_fixture(revision=revision),
        provider=COCKPIT_FIXTURE_PROVIDER,
        requested_start_date=COCKPIT_FIXTURE_START_DATE,
        requested_end_date=COCKPIT_FIXTURE_END_DATE,
        information_cutoff_date=COCKPIT_FIXTURE_CURRENT_CUTOFF,
        requested_scope=COCKPIT_FIXTURE_SCOPE,
        adjust_type=COCKPIT_FIXTURE_ADJUST_TYPE,
        compatibility_parameters={
            "stock_basic_endpoint": "fixture_stock_basic",
            "daily_price_endpoint": "fixture_daily_price",
            "trade_calendar_endpoint": "fixture_trade_calendar",
            "frequency": "daily",
            "adapter_compatibility_version": "today-market-fixture-v1",
        },
        provider_request_metadata={
            "collection_timestamp_utc": "2026-04-05T12:00:00Z",
            "effective_information_cutoff_date": COCKPIT_FIXTURE_CURRENT_CUTOFF,
        },
        adapter_version="today-market-fixture-v1",
    )


def _ingest_benchmark(session_factory: sessionmaker[Session]):
    return BenchmarkPersistenceService(session_factory).ingest_bundle(
        build_benchmark_fixture(),
        provider=BENCHMARK_FIXTURE_PROVIDER,
        requested_start_date=BENCHMARK_FIXTURE_START_DATE,
        requested_end_date=BENCHMARK_FIXTURE_END_DATE,
        information_cutoff_date=BENCHMARK_FIXTURE_CURRENT_CUTOFF,
        requested_scope=BENCHMARK_FIXTURE_SCOPE,
        endpoint="fixture_benchmark_history",
        adapter_compatibility_version="today-market-benchmark-v1",
        provider_request_metadata={
            "collection_timestamp_utc": "2026-04-05T12:00:00Z",
            "effective_information_cutoff_date": BENCHMARK_FIXTURE_CURRENT_CUTOFF,
            "network_mode": "offline-fixture",
            "timeout_seconds": 1.0,
            "max_retries": 0,
        },
        adapter_version="today-market-benchmark-v1",
    )


def _ingest_sector(session_factory: sessionmaker[Session]):
    return SectorPersistenceService(session_factory).ingest_bundle(
        build_sector_fixture(),
        provider=SECTOR_FIXTURE_PROVIDER,
        requested_start_date=SECTOR_FIXTURE_START_DATE,
        requested_end_date=SECTOR_FIXTURE_END_DATE,
        information_cutoff_date=SECTOR_FIXTURE_CURRENT_CUTOFF,
        requested_scope=SECTOR_FIXTURE_SCOPE,
        taxonomy_endpoint="fixture_sector_taxonomy",
        history_endpoint="fixture_sector_history",
        adapter_compatibility_version="today-market-sector-v1",
        adapter_version="today-market-sector-v1",
        provider_request_metadata={
            "collection_timestamp_utc": "2026-04-05T12:00:00Z",
            "effective_information_cutoff_date": SECTOR_FIXTURE_CURRENT_CUTOFF,
            "network_mode": "offline-fixture",
            "timeout_seconds": 1.0,
            "max_retries": 0,
        },
    )


def _set_visible_times(
    session_factory: sessionmaker[Session],
    *run_ids: int,
    imported_at: datetime = EARLY_AT,
    completed_at: datetime = VISIBLE_AT,
) -> None:
    with session_factory.begin() as session:
        for run_id in run_ids:
            run = session.get(IngestionRun, run_id)
            assert run is not None
            run.imported_at = imported_at
            run.completed_at = completed_at


def _boundaries(recorded_at: str = "2026-04-06T12:00:00Z") -> str:
    return (
        "as_of_cutoff=2026-04-05"
        f"&as_of_recorded_at_utc={recorded_at}"
    )


def test_boundaries_fail_before_database_construction(monkeypatch) -> None:
    def reject_engine(*_args, **_kwargs):
        raise AssertionError("database engine must not be created")

    monkeypatch.setattr(today_market_api, "build_engine", reject_engine)
    test_client = TestClient(app)

    missing = test_client.get("/today-market/api/local-series")
    naive = test_client.get(
        "/today-market/api/local-series"
        "?as_of_cutoff=2026-04-05"
        "&as_of_recorded_at_utc=2026-04-06T12:00:00"
    )

    assert missing.status_code == 422
    assert missing.json()["detail"]["code"] == "today_market_cutoff_required"
    assert naive.status_code == 422
    assert (
        naive.json()["detail"]["code"]
        == "today_market_recorded_at_timezone_required"
    )


def test_database_configuration_failure_is_stable_503(monkeypatch) -> None:
    def reject_engine(*_args, **_kwargs):
        raise RuntimeError("DATABASE_URL is unavailable")

    monkeypatch.setattr(today_market_api, "build_engine", reject_engine)
    response = TestClient(app).get(
        "/today-market/api/local-series?" + _boundaries()
    )

    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "today_market_database_unavailable"
    assert "DATABASE_URL" not in response.json()["detail"]["message"]


def test_empty_catalog_is_honest_and_uses_one_query(database) -> None:
    engine, session_factory = database
    app.dependency_overrides[get_today_market_session_factory] = lambda: session_factory
    statements = 0

    def count_statement(*_args, **_kwargs):
        nonlocal statements
        statements += 1

    event.listen(engine, "before_cursor_execute", count_statement)
    try:
        response = TestClient(app).get(
            "/today-market/api/local-series?" + _boundaries()
        )
    finally:
        event.remove(engine, "before_cursor_execute", count_statement)
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "no_eligible_local_data"
    assert payload["families"] == {"equity": [], "benchmark": [], "sector": []}
    assert payload["selected"] == {
        "equity_series_key": None,
        "benchmark_series_key": None,
        "sector_series_key": None,
    }
    assert payload["auto_selected"] is False
    assert statements == 1


def test_catalog_lists_exact_families_without_selection_and_within_query_limit(
    database,
) -> None:
    engine, session_factory = database
    equity = _ingest_equity(session_factory)
    benchmark = _ingest_benchmark(session_factory)
    sector = _ingest_sector(session_factory)
    _set_visible_times(
        session_factory,
        equity.ingestion_run_id,
        benchmark.ingestion_run_id,
        sector.ingestion_run_id,
    )
    app.dependency_overrides[get_today_market_session_factory] = lambda: session_factory
    statements = 0

    def count_statement(*_args, **_kwargs):
        nonlocal statements
        statements += 1

    event.listen(engine, "before_cursor_execute", count_statement)
    try:
        response = TestClient(app).get(
            "/today-market/api/local-series?" + _boundaries()
        )
    finally:
        event.remove(engine, "before_cursor_execute", count_statement)
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ready"
    assert [item["series_key"] for item in payload["families"]["equity"]] == [
        equity.series_key
    ]
    assert [item["series_key"] for item in payload["families"]["benchmark"]] == [
        benchmark.series_key
    ]
    assert [item["series_key"] for item in payload["families"]["sector"]] == [
        sector.series_key
    ]
    assert "公司" in payload["families"]["equity"][0]["label"]
    assert ", ".join(BENCHMARK_FIXTURE_CODES) in payload["families"]["benchmark"][0]["label"]
    assert str(len(SECTOR_FIXTURE_CODES)) in payload["families"]["sector"][0]["label"]
    assert payload["auto_selected"] is False
    assert statements <= 4


def test_recorded_boundary_prevents_equity_benchmark_and_sector_leakage(client) -> None:
    test_client, session_factory = client
    equity = _ingest_equity(session_factory)
    benchmark = _ingest_benchmark(session_factory)
    sector = _ingest_sector(session_factory)
    _set_visible_times(
        session_factory,
        equity.ingestion_run_id,
        benchmark.ingestion_run_id,
        sector.ingestion_run_id,
    )

    catalog = test_client.get(
        "/today-market/api/local-series?"
        + _boundaries("2026-04-06T11:59:59Z")
    )
    snapshot = test_client.get(
        "/today-market/api/snapshot?"
        + _boundaries("2026-04-06T11:59:59Z")
        + f"&equity_series_key={equity.series_key}"
        + f"&benchmark_series_key={benchmark.series_key}"
        + f"&sector_series_key={sector.series_key}"
    )

    assert catalog.status_code == 200
    assert catalog.json()["status"] == "no_eligible_local_data"
    assert snapshot.status_code == 404
    assert snapshot.json()["detail"]["code"] == "today_market_snapshot_not_visible"


def test_snapshot_golden_path_delegates_to_market_cockpit_and_stays_read_only(
    database,
) -> None:
    engine, session_factory = database
    equity = _ingest_equity(session_factory)
    benchmark = _ingest_benchmark(session_factory)
    sector = _ingest_sector(session_factory)
    _set_visible_times(
        session_factory,
        equity.ingestion_run_id,
        benchmark.ingestion_run_id,
        sector.ingestion_run_id,
    )
    app.dependency_overrides[get_today_market_session_factory] = lambda: session_factory
    statements = 0

    def count_statement(*_args, **_kwargs):
        nonlocal statements
        statements += 1

    event.listen(engine, "before_cursor_execute", count_statement)
    try:
        response = TestClient(app).get(
            "/today-market/api/snapshot?"
            + _boundaries()
            + f"&equity_series_key={equity.series_key}"
            + f"&benchmark_series_key={benchmark.series_key}"
            + f"&sector_series_key={sector.series_key}"
        )
    finally:
        event.remove(engine, "before_cursor_execute", count_statement)
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["read_only"] is True
    assert payload["scope_and_freshness"]["coverage_notice"] == "不是全市场覆盖"
    assert payload["scope_and_freshness"]["effective_equity_session"] == (
        datetime.strptime(COCKPIT_FIXTURE_END_DATE, "%Y%m%d").date().isoformat()
    )
    assert payload["supported_analysis"]["price_behavior"]["read_only"] is True
    assert payload["supported_analysis"]["liquidity"]["read_only"] is True
    assert payload["supported_analysis"]["benchmark"]["read_only"] is True
    assert payload["supported_analysis"]["sector"]["read_only"] is True
    assert payload["technical_details"]["raw_market_cockpit_snapshot"][
        "provenance"
    ]["series_key"] == equity.series_key
    assert {item["key"] for item in payload["unavailable_sections"]} == {
        "full_market_breadth",
        "stock_anomalies",
        "events_and_causes",
        "attention_and_fund_flow",
        "live_intraday",
        "remote_refresh",
    }
    assert statements <= 14


def test_legacy_repository_selection_is_unchanged_when_recorded_boundary_is_omitted(
    database,
) -> None:
    _, session_factory = database
    older = _ingest_equity(session_factory, revision="historical")
    with session_factory.begin() as session:
        older_run = session.get(IngestionRun, older.ingestion_run_id)
        assert older_run is not None
        older_run.imported_at = datetime(2026, 4, 5, 8, tzinfo=timezone.utc)
        older_run.completed_at = datetime(2026, 4, 5, 9, tzinfo=timezone.utc)

    newer = _ingest_equity(session_factory, revision="current")
    assert newer.series_key == older.series_key
    with session_factory.begin() as session:
        newer_run = session.get(IngestionRun, newer.ingestion_run_id)
        assert newer_run is not None
        newer_run.imported_at = datetime(2026, 4, 6, 8, tzinfo=timezone.utc)
        newer_run.completed_at = datetime(2026, 4, 6, 9, tzinfo=timezone.utc)

    with session_factory() as session:
        repository = MarketCockpitRepository(session)
        legacy = repository.load_snapshot(series_key=newer.series_key)
        historical = repository.load_snapshot(
            series_key=newer.series_key,
            as_of_recorded_at_utc="2026-04-05T12:00:00Z",
        )

    assert legacy.ingestion_run_id == newer.ingestion_run_id
    assert historical.ingestion_run_id == older.ingestion_run_id


def test_today_market_page_is_selection_first_and_never_auto_loads_snapshot() -> None:
    test_client = TestClient(app)
    page = test_client.get("/today-market")
    script = test_client.get("/today-market/static/today_market.js")
    workbench = test_client.get("/workbench")

    assert page.status_code == 200
    assert 'id="snapshot-content" hidden' in page.text
    assert 'id="snapshot-button"' in page.text
    assert "查看本地市场快照" in page.text
    assert "series_key" not in page.text
    assert script.status_code == 200
    assert 'snapshotButton.addEventListener("click"' in script.text
    assert "activeBoundaries = null" in script.text
    assert workbench.status_code == 200
    assert workbench.history[0].status_code == 307
    assert workbench.url.path == "/industry-analysis"


def test_static_assets_contain_no_remote_or_investment_actions() -> None:
    root = Path(__file__).resolve().parents[1]
    html = (root / "today_market" / "static" / "today_market.html").read_text(
        encoding="utf-8"
    )
    script = (root / "today_market" / "static" / "today_market.js").read_text(
        encoding="utf-8"
    )
    serialized = (html + script).lower()

    assert "http://" not in serialized
    assert "https://" not in serialized
    for forbidden in ("买入", "卖出", "目标价", "仓位", "自动交易"):
        assert forbidden not in serialized
