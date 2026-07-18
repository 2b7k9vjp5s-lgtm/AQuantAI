from __future__ import annotations

import re
from collections.abc import Iterator
from pathlib import Path

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
from backend.database.models import Base
from backend.main import app
from datasource.akshare.provider import SubprocessAkshareRunner
from market_cockpit.fixtures import (
    COCKPIT_FIXTURE_ADJUST_TYPE,
    COCKPIT_FIXTURE_CURRENT_CUTOFF,
    COCKPIT_FIXTURE_END_DATE,
    COCKPIT_FIXTURE_HISTORICAL_CUTOFF,
    COCKPIT_FIXTURE_PROVIDER,
    COCKPIT_FIXTURE_SCOPE,
    COCKPIT_FIXTURE_START_DATE,
    build_market_cockpit_fixture,
)
from scripts.demo_market_cockpit import build_persisted_market_cockpit_demo


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
        provider_request_metadata={"fixture_revision": revision},
        adapter_version="market-cockpit-fixture-v1",
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

    assert invalid_key.status_code == 422
    assert "64-character" in invalid_key.json()["detail"]
    assert invalid_cutoff.status_code == 422
    assert "YYYYMMDD" in invalid_cutoff.json()["detail"]


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
    assert current_payload["stock_codes"] == ["000001", "000002", "000003"]
    assert current_payload["universe_stock_count"] == 3
    assert current_payload["available_stock_count"] == 3
    assert current_payload["completeness_status"] == "ready"
    assert current_payload["read_only"] is True
    assert current_payload["allowed_actions"] == ["view", "inspect"]
    assert current_payload["unsupported_sections"]
    serialized = str(current_payload)
    assert "全市场" not in serialized
    assert "A 股市场宽度" not in serialized
    assert "官方指数宽度" not in serialized


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
    assert "Not supported in v0.4A" in page.text
    assert "Read-only" in page.text
    assert "<form" not in page.text.lower()
    assert "<button" not in page.text.lower()
    assert "innerHTML" not in script.text
    assert "eval(" not in script.text
    assert "new Function" not in script.text
    assert "`" not in script.text
    assert "textContent" in script.text
    assert "/market-cockpit/snapshot?" in script.text
    for forbidden_claim in ("全市场", "A 股市场宽度", "官方指数宽度"):
        assert forbidden_claim not in page.text


def test_market_cockpit_page_does_not_create_database_or_access_network(monkeypatch) -> None:
    def reject_side_effect(*_args, **_kwargs):
        raise AssertionError("page rendering attempted a database or network side effect")

    monkeypatch.setattr(market_cockpit_api, "build_engine", reject_side_effect)
    monkeypatch.setattr(SubprocessAkshareRunner, "call", reject_side_effect)

    response = TestClient(app).get("/market-cockpit")

    assert response.status_code == 200


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
    assert payload["current"]["completeness_status"] == "ready"
    assert payload["historical"]["completeness_status"] == "ready"
    assert payload["read_only"] is True
    assert payload["network_access"] is False
