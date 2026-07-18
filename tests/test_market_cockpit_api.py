from __future__ import annotations

import importlib
import json
import re
from collections.abc import Iterator
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import backend.api.market_cockpit as market_cockpit_api
from backend.api.market_cockpit import get_market_cockpit_session_factory
from backend.database.engine import build_session_factory
from backend.database.market_data import MarketDataPersistenceService
from backend.database.sector_data import SectorPersistenceService
from backend.database.models import Base
from backend.main import app
from datasource.akshare.provider import SubprocessAkshareRunner
from market_cockpit.fixtures import (
    COCKPIT_FIXTURE_ADJUST_TYPE,
    COCKPIT_FIXTURE_CURRENT_CUTOFF,
    COCKPIT_FIXTURE_DATES,
    COCKPIT_FIXTURE_END_DATE,
    COCKPIT_FIXTURE_HISTORICAL_CUTOFF,
    COCKPIT_FIXTURE_PROVIDER,
    COCKPIT_FIXTURE_SCOPE,
    COCKPIT_FIXTURE_START_DATE,
    build_market_cockpit_fixture,
)
from market_cockpit.repository import MarketCockpitRepository
from market_cockpit.service import MarketCockpitService as RealMarketCockpitService
from market_cockpit.sector_fixtures import (
    SECTOR_FIXTURE_CODES,
    SECTOR_FIXTURE_CURRENT_CUTOFF,
    SECTOR_FIXTURE_END_DATE,
    SECTOR_FIXTURE_PROVIDER,
    SECTOR_FIXTURE_SCOPE,
    SECTOR_FIXTURE_START_DATE,
    build_sector_fixture,
)
from scripts.demo_market_cockpit import build_persisted_market_cockpit_demo
from tests.test_liquidity_context import _snapshot as build_liquidity_test_snapshot


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
    app.dependency_overrides[get_market_cockpit_session_factory] = lambda: session_factory
    try:
        yield TestClient(app), session_factory
    finally:
        app.dependency_overrides.clear()


def _ingest(session_factory: sessionmaker[Session], *, revision: str, cutoff: str):
    return MarketDataPersistenceService(session_factory).ingest_bundle(
        build_market_cockpit_fixture(revision=revision),
        provider=COCKPIT_FIXTURE_PROVIDER,
        requested_start_date=COCKPIT_FIXTURE_START_DATE,
        requested_end_date=COCKPIT_FIXTURE_END_DATE,
        information_cutoff_date=cutoff,
        requested_scope=COCKPIT_FIXTURE_SCOPE,
        adjust_type=COCKPIT_FIXTURE_ADJUST_TYPE,
        compatibility_parameters={
            "stock_basic_endpoint": "fixture_stock_basic",
            "daily_price_endpoint": "fixture_daily_price",
            "trade_calendar_endpoint": "fixture_trade_calendar",
            "frequency": "daily",
            "adapter_compatibility_version": "market-cockpit-fixture-v1",
        },
        provider_request_metadata={
            "fixture_revision": revision,
            "collection_timestamp_utc": f"2026-04-{cutoff[-2:]}T12:00:00Z",
            "effective_information_cutoff_date": cutoff,
            "unknown_metadata": "must-not-be-public",
        },
        adapter_version="market-cockpit-fixture-v1",
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
        adapter_compatibility_version="sector-fixture-v1",
        adapter_version="sector-fixture-v1",
        provider_request_metadata={
            "taxonomy_endpoint": "fixture_sector_taxonomy",
            "history_endpoint": "fixture_sector_history",
            "classification_system": "eastmoney_industry_board",
            "classification_level": None,
            "frequency": "daily",
            "adjust_type": "",
            "sector_codes": list(SECTOR_FIXTURE_CODES),
            "start_date": SECTOR_FIXTURE_START_DATE,
            "end_date": SECTOR_FIXTURE_END_DATE,
            "network_mode": "offline-fixture",
            "timeout_seconds": 1.0,
            "max_retries": 0,
            "akshare_package_version": "1.18.64",
            "definition_contract_version": "1.0",
            "daily_contract_version": "1.0",
            "adapter_version": "sector-fixture-v1",
            "adapter_compatibility_version": "sector-fixture-v1",
            "collection_timestamp_utc": "2026-04-05T12:00:00Z",
            "effective_information_cutoff_date": SECTOR_FIXTURE_CURRENT_CUTOFF,
        },
    )


def test_missing_selector_fails_before_database_engine_creation(monkeypatch) -> None:
    def reject_engine(*_args, **_kwargs):
        raise AssertionError("database engine must not be created without a selector")

    monkeypatch.setattr(market_cockpit_api, "build_engine", reject_engine)
    response = TestClient(app).get("/market-cockpit/snapshot")

    assert response.status_code == 422
    assert "series_key is required" in response.json()["detail"]


def test_invalid_selector_and_cutoff_have_clear_client_errors() -> None:
    client = TestClient(app)

    invalid_key = client.get("/market-cockpit/snapshot?series_key=fixture")
    invalid_cutoff = client.get(
        "/market-cockpit/snapshot?series_key=" + "a" * 64 + "&as_of_cutoff=bad-date"
    )
    invalid_sector = client.get(
        "/market-cockpit/snapshot?series_key=" + "a" * 64 + "&sector_series_key=name-only"
    )

    assert invalid_key.status_code == 422
    assert "64-character" in invalid_key.json()["detail"]
    assert invalid_cutoff.status_code == 422
    assert "YYYYMMDD" in invalid_cutoff.json()["detail"]
    assert invalid_sector.status_code == 422
    assert "64-character" in invalid_sector.json()["detail"]


def test_api_adds_sector_context_only_for_an_explicit_valid_sector_series(client) -> None:
    test_client, session_factory = client
    equity = _ingest(
        session_factory, revision="current", cutoff=COCKPIT_FIXTURE_CURRENT_CUTOFF
    )
    sector = _ingest_sector(session_factory)

    equity_only = test_client.get(
        "/market-cockpit/snapshot?series_key=" + equity.series_key
    )
    with_sector = test_client.get(
        "/market-cockpit/snapshot?series_key="
        + equity.series_key
        + "&sector_series_key="
        + sector.series_key
    )
    missing_sector = test_client.get(
        "/market-cockpit/snapshot?series_key="
        + equity.series_key
        + "&sector_series_key="
        + "f" * 64
    )

    assert equity_only.status_code == 200
    assert equity_only.json()["sector_context"] is None
    assert equity_only.json()["liquidity_context"]["effective_session"] == (
        COCKPIT_FIXTURE_END_DATE
    )
    assert with_sector.status_code == 200
    context = with_sector.json()["sector_context"]
    assert context["provenance"]["series_key"] == sector.series_key
    assert context["provenance"]["effective_sector_session"] == SECTOR_FIXTURE_END_DATE
    assert context["requested_sector_count"] == 2
    assert context["coverage_status"] == "complete"
    assert context["read_only"] is True
    assert "recommendation" not in str(context).lower()
    assert missing_sector.status_code == 404
    assert "No successful complete sector snapshot" in missing_sector.json()["detail"]


def test_missing_database_configuration_returns_503(monkeypatch) -> None:
    def reject_engine(*_args, **_kwargs):
        raise RuntimeError("DATABASE_URL is required for database operations.")

    monkeypatch.setattr(market_cockpit_api, "build_engine", reject_engine)
    response = TestClient(app).get("/market-cockpit/snapshot?series_key=" + "a" * 64)

    assert response.status_code == 503
    assert "database configuration is unavailable" in response.json()["detail"]


def test_missing_snapshot_returns_actionable_404(client) -> None:
    test_client, _ = client

    response = test_client.get("/market-cockpit/snapshot?series_key=" + "a" * 64)

    assert response.status_code == 404
    assert "No successful complete snapshot" in response.json()["detail"]


def test_api_returns_current_and_historical_persisted_snapshots(client) -> None:
    test_client, session_factory = client
    historical = _ingest(
        session_factory,
        revision="historical",
        cutoff=COCKPIT_FIXTURE_HISTORICAL_CUTOFF,
    )
    current = _ingest(
        session_factory,
        revision="current",
        cutoff=COCKPIT_FIXTURE_CURRENT_CUTOFF,
    )
    assert historical.series_key == current.series_key

    current_response = test_client.get(
        "/market-cockpit/snapshot?series_key=" + current.series_key
    )
    historical_response = test_client.get(
        "/market-cockpit/snapshot?series_key="
        + current.series_key
        + "&as_of_cutoff="
        + COCKPIT_FIXTURE_HISTORICAL_CUTOFF
    )

    assert current_response.status_code == 200
    assert historical_response.status_code == 200
    current_payload = current_response.json()
    historical_payload = historical_response.json()
    assert current_payload["provenance"]["ingestion_run_id"] == current.ingestion_run_id
    assert historical_payload["provenance"]["ingestion_run_id"] == historical.ingestion_run_id
    assert current_payload["provenance"]["series_key"] == current.series_key
    assert current_payload["provenance"]["adjust_type"] == "qfq"
    assert current_payload["provenance"]["effective_as_of_session"] == COCKPIT_FIXTURE_END_DATE
    assert current_payload["provenance"]["requested_as_of_cutoff"] is None
    assert historical_payload["provenance"]["requested_as_of_cutoff"] == (
        COCKPIT_FIXTURE_HISTORICAL_CUTOFF
    )
    assert current_payload["provenance"]["collection_timestamp_utc"] == (
        "2026-04-05T12:00:00Z"
    )
    assert current_payload["provenance"]["effective_information_cutoff_date"] == (
        COCKPIT_FIXTURE_CURRENT_CUTOFF
    )
    assert current_payload["provenance"]["stock_basic_endpoint"] == "fixture_stock_basic"
    assert current_payload["provenance"]["adapter_compatibility_version"] == (
        "market-cockpit-fixture-v1"
    )
    assert current_payload["provenance"]["ingestion_imported_at_utc"].endswith("Z")
    assert current_payload["provenance"]["ingestion_completed_at_utc"].endswith("Z")
    assert current_payload["provenance"]["generated_at_utc"].endswith("Z")
    assert current_payload["stock_codes"] == ["000001", "000002", "000003"]
    assert current_payload["universe_stock_count"] == 3
    assert current_payload["available_stock_count"] == 3
    assert current_payload["calculation_status"] == "ready"
    assert current_payload["scope_coverage_status"] == "unverified_selected_scope"
    assert current_payload["completeness_status"] == "partial"
    assert current_payload["latest_data_diagnostics"] == {
        "stale_or_missing_latest_count": 0,
        "no_trade_latest_count": 0,
        "latest_return_unavailable_count": 0,
        "latest_return_issues": [],
    }
    liquidity = current_payload["liquidity_context"]
    assert liquidity["effective_session"] == COCKPIT_FIXTURE_END_DATE
    assert liquidity["requested_stock_count"] == 3
    assert liquidity["latest_eligible_count"] == 3
    assert liquidity["activity_5"]["matched_cohort_count"] == 3
    assert liquidity["activity_20"]["matched_cohort_count"] == 3
    assert liquidity["read_only"] is True
    assert liquidity["scope_label"] == "selected universe"
    assert current_payload["read_only"] is True
    assert current_payload["allowed_actions"] == ["view", "inspect"]
    assert current_payload["unsupported_sections"]
    serialized = str(current_payload)
    assert "unknown_metadata" not in serialized
    assert "must-not-be-public" not in serialized
    assert "全市场" not in serialized
    assert "A 股市场宽度" not in serialized
    assert "官方指数宽度" not in serialized


def test_api_strictly_serializes_nulls_for_liquidity_aggregate_overflow(
    client,
    monkeypatch,
) -> None:
    test_client, _ = client
    snapshot = build_liquidity_test_snapshot(stock_count=20)
    prices = snapshot.daily_price.copy()
    prices.loc[
        prices["trade_date"].eq(snapshot.requested_end_date), "amount"
    ] = float(np.finfo(float).max * 0.75)
    overflow_snapshot = replace(snapshot, daily_price=prices)

    class StaticRepository:
        def load_snapshot(self, **_kwargs):
            return overflow_snapshot

    expected = RealMarketCockpitService(
        StaticRepository(),
        clock=lambda: datetime(2026, 7, 18, 12, 0, tzinfo=timezone.utc),
    ).build_snapshot(series_key="a" * 64)

    class StaticService:
        def __init__(self, *_args, **_kwargs) -> None:
            pass

        def build_snapshot(self, **_kwargs):
            return expected

    monkeypatch.setattr(market_cockpit_api, "MarketCockpitService", StaticService)
    response = test_client.get("/market-cockpit/snapshot?series_key=" + "a" * 64)

    assert response.status_code == 200
    payload = response.json()
    liquidity = payload["liquidity_context"]
    assert liquidity["latest_total_amount"] is None
    assert liquidity["top5_concentration_share"] is None
    assert liquidity["top_decile_concentration_share"] is None
    assert liquidity["latest_aggregate_reason"] == "non_finite_aggregate"
    assert liquidity["activity_5"]["reason"] == "non_finite_aggregate"
    assert liquidity["activity_20"]["activity_ratio"] is None
    serialized = json.dumps(payload, allow_nan=False)
    assert "NaN" not in serialized
    assert "Infinity" not in serialized


def test_page_and_assets_are_read_only_and_show_scope_provenance_and_limitations() -> None:
    client = TestClient(app)

    page = client.get("/market-cockpit")
    stylesheet = client.get("/market-cockpit/static/market_cockpit.css")
    script = client.get("/market-cockpit/static/market_cockpit.js")

    assert page.status_code == 200
    assert stylesheet.status_code == 200
    assert script.status_code == 200
    assert "selected-universe monitoring" in page.text
    assert "Selected universe / 选定股票范围" in page.text
    assert "One ingestion run, no cross-series stitching" in page.text
    assert "Coverage confidence is unverified" in page.text
    assert "Current-session health and latest-return eligibility" in page.text
    assert "Selected-sector market context" in page.text
    assert "exact stable codes" in page.text
    assert "does not provide sector constituents" in page.text
    assert "Liquidity distribution and trading concentration" in page.text
    assert "descriptive distribution statistic" in page.text
    assert "not a crowding conclusion" in page.text
    assert "Still unsupported after the bounded v0.4D slice" in page.text
    assert "Read-only" in page.text
    assert "<form" not in page.text.lower()
    assert "<button" not in page.text.lower()
    assert "innerHTML" not in script.text
    assert "eval(" not in script.text
    assert "new Function" not in script.text
    assert "`" not in script.text
    assert "textContent" in script.text
    assert "/market-cockpit/snapshot?" in script.text
    assert "Calculation status" in script.text
    assert "Scope coverage" in script.text
    assert "Collected UTC" in script.text
    assert "Imported UTC" in script.text
    assert "Requested historical cutoff" in script.text
    assert "Calculated trading session" in script.text
    assert "View generated UTC" in script.text
    assert "Current-session stale, invalid, or missing" in script.text
    assert "Current-session no-trade" in script.text
    assert "Latest-return unavailable" in script.text
    assert "sector_series_key" in script.text
    assert "Exact stable sector codes" in script.text
    assert "No sector series was requested" in script.text
    assert "renderLiquidityContext" in script.text
    assert "Top-decile concentration" in script.text
    assert "No liquidity source-exclusion diagnostics" in script.text
    assert "Number.isFinite" in script.text
    assert "Latest aggregate reason" in script.text
    assert "formatIdentifierSample" in script.text
    assert "unavailable count=" in script.text
    assert "sample truncated=" in script.text
    assert '"; omitted="' in script.text
    assert 'return "Unavailable"' in script.text
    for forbidden_claim in ("全市场", "A 股市场宽度", "官方指数宽度"):
        assert forbidden_claim not in page.text


def test_market_cockpit_page_does_not_create_database_or_access_network(monkeypatch) -> None:
    def reject_side_effect(*_args, **_kwargs):
        raise AssertionError("page rendering attempted a database or network side effect")

    monkeypatch.setattr(market_cockpit_api, "build_engine", reject_side_effect)
    monkeypatch.setattr(SubprocessAkshareRunner, "call", reject_side_effect)

    response = TestClient(app).get("/market-cockpit")

    assert response.status_code == 200


def test_import_and_fastapi_startup_do_not_create_database_or_access_network(monkeypatch) -> None:
    def reject_side_effect(*_args, **_kwargs):
        raise AssertionError("import or startup attempted a database or network side effect")

    monkeypatch.setattr(market_cockpit_api, "build_engine", reject_side_effect)
    monkeypatch.setattr(SubprocessAkshareRunner, "call", reject_side_effect)
    import backend.main as main_module

    reloaded = importlib.reload(main_module)
    with TestClient(reloaded.app) as startup_client:
        assert startup_client.get("/health").json() == {"status": "ok"}
        assert startup_client.get("/market-cockpit").status_code == 200


def test_existing_dashboard_and_api_contracts_are_unchanged() -> None:
    client = TestClient(app)

    assert client.get("/").json()["status"] == "v0.2 research-only local Dashboard baseline"
    assert client.get("/health").json() == {"status": "ok"}
    assert client.get("/dashboard").status_code == 200
    assert client.get("/dashboard/overview").json()["page_id"] == "dashboard_overview"
    assert client.get("/dashboard/report").json()["page_id"] == "dashboard_report"


def test_page_script_fetches_only_the_explicit_market_cockpit_endpoint() -> None:
    script = (
        Path(__file__).resolve().parents[1]
        / "market_cockpit"
        / "static"
        / "market_cockpit.js"
    ).read_text(encoding="utf-8")

    endpoints = set(re.findall(r'fetch\("([^\"]+)', script))
    assert endpoints == {"/market-cockpit/snapshot?"}


def test_persisted_demo_reports_current_and_historical_cutoffs(tmp_path) -> None:
    database_path = tmp_path / "market-cockpit.sqlite3"
    database_url = f"sqlite+pysqlite:///{database_path.as_posix()}"
    engine = create_engine(database_url)
    Base.metadata.create_all(engine)
    engine.dispose()

    payload = build_persisted_market_cockpit_demo(database_url)

    assert payload["current"]["information_cutoff_date"] == COCKPIT_FIXTURE_CURRENT_CUTOFF
    assert payload["historical"]["information_cutoff_date"] == (
        COCKPIT_FIXTURE_HISTORICAL_CUTOFF
    )
    assert payload["current"]["ingestion_run_id"] != payload["historical"]["ingestion_run_id"]
    assert payload["current"]["calculation_status"] == "ready"
    assert payload["historical"]["calculation_status"] == "ready"
    assert payload["current"]["scope_coverage_status"] == "unverified_selected_scope"
    assert payload["current"]["completeness_status"] == "partial"
    assert payload["historical"]["completeness_status"] == "partial"
    assert payload["current"]["collection_timestamp_utc"] == "2026-04-05T12:00:00Z"
    assert payload["historical"]["requested_as_of_cutoff"] == (
        COCKPIT_FIXTURE_HISTORICAL_CUTOFF
    )
    assert payload["current"]["stale_or_missing_latest_count"] == 0
    assert payload["current"]["no_trade_latest_count"] == 0
    assert payload["current"]["latest_return_unavailable_count"] == 0
    assert payload["current"]["latest_return_issues"] == []
    assert payload["read_only"] is True
    assert payload["network_access"] is False


@pytest.mark.parametrize(
    (
        "session_role",
        "mutation",
        "expected_reason",
        "expected_stale_current",
        "expected_no_trade_current",
    ),
    [
        ("effective", "missing", "missing_effective_session_row", 1, 0),
        ("effective", "invalid", "invalid_effective_session_row", 1, 0),
        ("effective", "no_trade", "no_trade_effective_session_row", 0, 1),
        ("previous", "missing", "missing_previous_session_row", 0, 0),
        ("previous", "invalid", "invalid_previous_session_row", 0, 0),
        ("previous", "no_trade", "no_trade_previous_session_row", 0, 0),
    ],
)
def test_api_serializes_every_latest_return_issue_reason(
    client,
    monkeypatch,
    session_role: str,
    mutation: str,
    expected_reason: str,
    expected_stale_current: int,
    expected_no_trade_current: int,
) -> None:
    test_client, session_factory = client
    result = _ingest(
        session_factory,
        revision="current",
        cutoff=COCKPIT_FIXTURE_CURRENT_CUTOFF,
    )
    blocking_date = (
        COCKPIT_FIXTURE_DATES[-1]
        if session_role == "effective"
        else COCKPIT_FIXTURE_DATES[-2]
    )
    with session_factory() as session:
        persisted = MarketCockpitRepository(session).load_snapshot(
            series_key=result.series_key
        )
    prices = persisted.daily_price.copy()
    mask = prices["trade_date"].eq(blocking_date) & prices["stock_code"].eq("000003")
    assert int(mask.sum()) == 1
    if mutation == "missing":
        prices = prices.loc[~mask].copy()
    elif mutation == "invalid":
        prices.loc[mask, "volume"] = np.nan
    else:
        prices.loc[mask, ["volume", "amount"]] = 0.0
    malformed = replace(persisted, daily_price=prices)
    monkeypatch.setattr(
        MarketCockpitRepository,
        "load_snapshot",
        lambda _self, **_kwargs: malformed,
    )

    response = test_client.get(
        "/market-cockpit/snapshot?series_key=" + result.series_key
    )

    assert response.status_code == 200
    payload = response.json()
    diagnostics = payload["latest_data_diagnostics"]
    assert payload["metrics"]["latest_session"]["unavailable_count"] == 1
    assert diagnostics["latest_return_unavailable_count"] == 1
    assert len(diagnostics["latest_return_issues"]) == 1
    assert diagnostics["stale_or_missing_latest_count"] == expected_stale_current
    assert diagnostics["no_trade_latest_count"] == expected_no_trade_current
    issue = diagnostics["latest_return_issues"][0]
    assert issue == {
        "stock_code": "000003",
        "reason": expected_reason,
        "blocking_session": blocking_date,
        "last_valid_traded_session": (
            COCKPIT_FIXTURE_DATES[-2]
            if session_role == "effective"
            else COCKPIT_FIXTURE_DATES[-3]
        ),
        "open_session_gap": 1,
    }


def test_page_script_renders_previous_session_issue_without_contradictory_empty_message() -> None:
    script = (
        Path(__file__).resolve().parents[1]
        / "market_cockpit"
        / "static"
        / "market_cockpit.js"
    ).read_text(encoding="utf-8")

    assert "Missing previous-session row" in script
    assert "Invalid previous-session row" in script
    assert "No-trade previous-session row" in script
    assert "blocking session=" in script
    assert "last valid traded session=" in script
    assert "No latest-return eligibility issues." in script
    assert "No stale, missing, or no-trade latest observations." not in script
