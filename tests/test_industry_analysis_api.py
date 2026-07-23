from __future__ import annotations

from datetime import date, datetime, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

import backend.api.industry_analysis as industry_api
from backend.database.engine import build_session_factory
from backend.database.models import Base
from backend.main import app
import industry_alpha.stage1_models  # noqa: F401 - register output-link FK targets
from industry_alpha.industry_thesis_commands import IndustryThesisCommandService
from scripts.demo_industry_analysis_workbench import run_demo

UTC = timezone.utc
NOW = datetime(2026, 7, 23, 3, 0, tzinfo=UTC)
CUTOFF = date(2026, 7, 23)


@pytest.fixture()
def database():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = build_session_factory(engine)
    try:
        yield factory
    finally:
        engine.dispose()


def _session_input() -> dict:
    return {
        "thesis_text_original": "高纯电子气体需求扩张与客户认证",
        "thesis_title_reviewed": "高纯电子气体",
        "driver_type": "demand_expansion",
        "analysis_horizon_kind": "medium_term",
        "market_scope": [
            {
                "market_namespace": "CN_A",
                "exchange_namespace": None,
                "security_type": "common_equity",
                "include_status": "active",
                "listed_instrument_ids": [],
            }
        ],
        "chain_boundary": {"included": ["purification", "certification"]},
        "exclusions": [],
        "seed_companies": [],
        "seed_products": [],
        "seed_technologies": [],
        "seed_bottlenecks": [],
        "draft_graph": {"nodes": [], "relationships": []},
        "coverage_state": "partial_local_coverage",
        "workflow_state": "draft",
        "information_cutoff_date": CUTOFF.isoformat(),
        "revision_note": "API fixture",
    }


def _clear_overrides() -> None:
    app.dependency_overrides.clear()


def test_workbench_redirect_and_canonical_pages_are_served() -> None:
    client = TestClient(app)

    redirect = client.get("/workbench", follow_redirects=False)
    assert redirect.status_code == 307
    assert redirect.headers["location"] == "/industry-analysis"

    for route in (
        "/industry-analysis",
        "/industry-analysis/new",
        "/workbench/settings",
    ):
        response = client.get(route)
        assert response.status_code == 200
        assert "个人研究工作台" in response.text
        assert "产业研究" in response.text
        assert "研究用途" in response.text


def test_future_modules_are_disabled_without_mock_market_values() -> None:
    response = TestClient(app).get("/industry-analysis")

    assert response.text.count("后续阶段") >= 3
    assert 'aria-disabled="true"' in response.text
    assert "上证指数" not in response.text
    assert "模拟收益" not in response.text


def test_bootstrap_is_deterministic_and_non_writing(monkeypatch) -> None:
    monkeypatch.setattr(industry_api, "_database_available", lambda: True)
    payload = TestClient(app).get("/industry-analysis/api/bootstrap").json()

    assert payload["phase"] == "ui_phase_1a"
    assert payload["database_available"] is True
    assert [item["label"] for item in payload["modules"]] == [
        "今日市场",
        "产业研究",
        "关注与跟踪",
        "研究组合",
        "系统设置",
    ]
    assert payload["capabilities"]["thesis_history"] is True
    assert payload["capabilities"]["session_write"] is False
    assert payload["capabilities"]["network_acquisition"] is False
    assert payload["capabilities"]["trading"] is False


def test_sessions_api_returns_exact_visible_history(database) -> None:
    created = IndustryThesisCommandService(
        database,
        clock=lambda: NOW,
    ).create_session(_session_input())

    def override_factory():
        yield database

    _clear_overrides()
    app.dependency_overrides[
        industry_api.get_industry_analysis_session_factory
    ] = override_factory
    try:
        response = TestClient(app).get(
            "/industry-analysis/api/sessions",
            params={
                "as_of_cutoff": CUTOFF.isoformat(),
                "as_of_recorded_at_utc": NOW.isoformat(),
                "limit": 20,
            },
        )
    finally:
        _clear_overrides()

    assert response.status_code == 200
    payload = response.json()
    assert payload["session_count"] == 1
    assert payload["sessions"][0]["session_id"] == created["session_id"]
    assert payload["sessions"][0]["visible_latest_revision_id"] == created[
        "session_revision_id"
    ]
    assert payload["sessions"][0]["thesis_title"] == "高纯电子气体"
    assert payload["notices"]["accepted_outputs_not_inferred"] is True


def test_invalid_boundary_fails_before_database_construction(monkeypatch) -> None:
    called = False

    def fail_if_called():
        nonlocal called
        called = True
        raise AssertionError("database must not be constructed")

    monkeypatch.setattr(industry_api, "build_engine", fail_if_called)
    response = TestClient(app).get(
        "/industry-analysis/api/sessions",
        params={
            "as_of_cutoff": "2026-07-23",
            "as_of_recorded_at_utc": "2026-07-23T03:00:00",
        },
    )

    assert response.status_code == 422
    assert called is False
    assert "explicit UTC" in response.json()["detail"]


def test_cutoff_after_recorded_date_fails_before_database_construction(monkeypatch) -> None:
    called = False

    def fail_if_called():
        nonlocal called
        called = True
        raise AssertionError("database must not be constructed")

    monkeypatch.setattr(industry_api, "build_engine", fail_if_called)
    response = TestClient(app).get(
        "/industry-analysis/api/sessions",
        params={
            "as_of_cutoff": "2026-07-24",
            "as_of_recorded_at_utc": "2026-07-23T03:00:00Z",
        },
    )

    assert response.status_code == 422
    assert called is False
    assert "cannot be later" in response.json()["detail"]


def test_missing_database_configuration_returns_stable_503(monkeypatch) -> None:
    monkeypatch.setattr(
        industry_api,
        "build_engine",
        lambda: (_ for _ in ()).throw(RuntimeError("missing database")),
    )
    response = TestClient(app).get(
        "/industry-analysis/api/sessions",
        params={
            "as_of_cutoff": CUTOFF.isoformat(),
            "as_of_recorded_at_utc": NOW.isoformat(),
        },
    )

    assert response.status_code == 503
    assert response.json()["detail"]["code"] == (
        "industry_analysis_database_unavailable"
    )


def test_static_assets_are_local_only_and_hide_technical_inputs() -> None:
    root = Path(__file__).resolve().parents[1] / "industry_analysis" / "static"
    html = (root / "workbench.html").read_text(encoding="utf-8")
    script = (root / "workbench.js").read_text(encoding="utf-8")

    assert "http://" not in script
    assert "https://" not in script
    assert "localStorage" in script
    assert "fetch(\"/industry-analysis/api/" in script
    assert "UUID" not in html
    assert "fingerprint" not in html
    assert "保存并构建候选（后续切片）" in html
    assert "disabled" in html


def test_offline_workbench_demo_runs_through_production_service() -> None:
    payload = run_demo()

    assert payload["session_count"] == 2
    assert payload["sessions"][0]["thesis_title"] == "高纯电子气体"
    assert payload["notices"]["not_investment_advice"] is True
