from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.pool import StaticPool

import backend.api.industry_analysis as industry_api
from backend.database.engine import build_session_factory
from backend.database.models import Base
from backend.main import app
import industry_alpha.stage1_models  # noqa: F401 - register output-link FK targets
from industry_alpha.industry_thesis_commands import (
    IndustryThesisCommandService as DomainCommandService,
)
from industry_alpha.industry_thesis_models import (
    IndustryThesisSessionIdentity,
    IndustryThesisSessionRevision,
)
from scripts.demo_industry_analysis_workbench import run_demo

UTC = timezone.utc
NOW = datetime(2026, 7, 23, 3, 0, tzinfo=UTC)
CUTOFF = date(2026, 7, 23)
WORKBENCH_SCOPE_CONTRACT = "aquantai.personal-research-workbench.scope.v1"


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
        "analysis_start_date": None,
        "analysis_end_date": None,
        "market_scope": [
            {
                "market_namespace": "CN_A",
                "exchange_namespace": None,
                "security_type": "common_equity",
                "include_status": "active",
                "listed_instrument_ids": [],
            }
        ],
        "chain_boundary": {
            "kind": "user_confirmed_text",
            "text": "纯化与客户认证",
        },
        "exclusions": [],
        "seed_companies": [],
        "seed_products": ["高纯电子气体"],
        "seed_technologies": [],
        "seed_bottlenecks": ["客户认证"],
        "draft_graph": {
            "workbench_contract": WORKBENCH_SCOPE_CONTRACT,
            "exact_industry_map_references": [],
            "nodes": [],
            "relationships": [],
        },
        "coverage_state": "coverage_unknown",
        "workflow_state": "draft",
        "information_cutoff_date": CUTOFF.isoformat(),
        "revision_note": "API fixture",
    }


def _clear_overrides() -> None:
    app.dependency_overrides.clear()


def _override_read_write_factories(database) -> None:
    def override_factory():
        yield database

    app.dependency_overrides[
        industry_api.get_industry_analysis_session_factory
    ] = override_factory
    app.dependency_overrides[
        industry_api.get_industry_analysis_write_factory
    ] = override_factory


def _install_clock(monkeypatch, *times: datetime) -> None:
    iterator = iter(times)

    def service(factory):
        return DomainCommandService(factory, clock=lambda: next(iterator))

    monkeypatch.setattr(industry_api, "IndustryThesisCommandService", service)


def _counts(database) -> tuple[int, int]:
    with database() as session:
        identities = session.scalar(
            select(func.count(IndustryThesisSessionIdentity.id))
        )
        revisions = session.scalar(
            select(func.count(IndustryThesisSessionRevision.id))
        )
    return int(identities or 0), int(revisions or 0)


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


def test_bootstrap_enables_only_phase_1b_scope_writes(monkeypatch) -> None:
    monkeypatch.setattr(industry_api, "_database_available", lambda: True)
    payload = TestClient(app).get("/industry-analysis/api/bootstrap").json()
    assert payload["phase"] == "ui_phase_1b"
    assert payload["database_available"] is True
    assert [item["label"] for item in payload["modules"]] == [
        "今日市场",
        "产业研究",
        "关注与跟踪",
        "研究组合",
        "系统设置",
    ]
    assert payload["capabilities"]["thesis_history"] is True
    assert payload["capabilities"]["local_option_reads"] is True
    assert payload["capabilities"]["session_write"] is True
    assert payload["capabilities"]["session_revision_write"] is True
    assert payload["capabilities"]["candidate_build"] is False
    assert payload["capabilities"]["candidate_review"] is False
    assert payload["capabilities"]["accepted_output_write"] is False
    assert payload["capabilities"]["network_acquisition"] is False
    assert payload["capabilities"]["trading"] is False


def test_sessions_api_returns_exact_visible_history_with_default_limit(database) -> None:
    created = DomainCommandService(database, clock=lambda: NOW).create_session(
        _session_input()
    )
    _clear_overrides()
    _override_read_write_factories(database)
    try:
        response = TestClient(app).get(
            "/industry-analysis/api/sessions",
            params={
                "as_of_cutoff": CUTOFF.isoformat(),
                "as_of_recorded_at_utc": NOW.isoformat(),
            },
        )
    finally:
        _clear_overrides()

    assert response.status_code == 200
    payload = response.json()
    assert payload["limit"] == 20
    assert payload["session_count"] == 1
    assert payload["sessions"][0]["session_id"] == created["session_id"]
    assert payload["sessions"][0]["visible_latest_revision_id"] == created[
        "session_revision_id"
    ]
    assert payload["sessions"][0]["thesis_title"] == "高纯电子气体"
    assert payload["notices"]["accepted_outputs_not_inferred"] is True


def test_create_dry_run_is_non_persistent_and_commit_creates_revision_one(
    database,
    monkeypatch,
) -> None:
    _install_clock(monkeypatch, NOW, NOW + timedelta(seconds=1))
    _clear_overrides()
    _override_read_write_factories(database)
    client = TestClient(app)
    try:
        dry_run = client.post(
            "/industry-analysis/api/sessions",
            params={"dry_run": "true"},
            json=_session_input(),
        )
        assert dry_run.status_code == 200
        assert dry_run.json()["dry_run"] is True
        assert dry_run.json()["session_id"] is None
        assert _counts(database) == (0, 0)

        committed = client.post(
            "/industry-analysis/api/sessions",
            params={"dry_run": "false"},
            json=_session_input(),
        )
    finally:
        _clear_overrides()

    assert committed.status_code == 200
    result = committed.json()
    assert result["dry_run"] is False
    assert result["revision_number"] == 1
    assert result["session_id"]
    assert result["session_revision_id"]
    assert result["history_path"] == "/industry-analysis"
    assert "session_id=" in result["edit_scope_path"]
    assert "session_revision_id=" in result["edit_scope_path"]
    parsed = urlparse(result["edit_scope_path"])
    query = parse_qs(parsed.query)
    assert query["as_of_recorded_at_utc"] == [result["recorded_at_utc"]]
    assert "%2B00%3A00" in result["edit_scope_path"]
    assert _counts(database) == (1, 1)


def test_exact_revision_reopens_and_revise_dry_run_then_commit_is_append_only(
    database,
    monkeypatch,
) -> None:
    _install_clock(
        monkeypatch,
        NOW,
        NOW + timedelta(seconds=1),
        NOW + timedelta(seconds=2),
    )
    _clear_overrides()
    _override_read_write_factories(database)
    client = TestClient(app)
    try:
        created = client.post(
            "/industry-analysis/api/sessions",
            params={"dry_run": "false"},
            json=_session_input(),
        ).json()
        exact = client.get(
            f"/industry-analysis/api/session-revisions/{created['session_revision_id']}",
            params={
                "as_of_cutoff": CUTOFF.isoformat(),
                "as_of_recorded_at_utc": created["recorded_at_utc"],
            },
        )
        changes = _session_input()
        changes.pop("revision_note")
        changes["thesis_title_reviewed"] = "高纯电子气体范围修订"
        revise_body = {
            "expected_latest_revision_number": 1,
            "changes": changes,
            "revision_note": "确认范围修订",
        }
        dry_run = client.post(
            f"/industry-analysis/api/sessions/{created['session_id']}/revisions",
            params={"dry_run": "true"},
            json=revise_body,
        )
        assert _counts(database) == (1, 1)
        committed = client.post(
            f"/industry-analysis/api/sessions/{created['session_id']}/revisions",
            params={"dry_run": "false"},
            json=revise_body,
        )
    finally:
        _clear_overrides()

    assert exact.status_code == 200
    assert exact.json()["session_id"] == created["session_id"]
    assert exact.json()["session_revision_id"] == created["session_revision_id"]
    assert exact.json()["draft_graph"]["workbench_contract"] == WORKBENCH_SCOPE_CONTRACT
    assert dry_run.status_code == 200
    assert dry_run.json()["dry_run"] is True
    assert dry_run.json()["revision_number"] == 2
    assert dry_run.json()["session_revision_id"] is None
    assert committed.status_code == 200
    result = committed.json()
    assert result["revision_number"] == 2
    assert _counts(database) == (1, 2)

    with database() as session:
        revision_two = session.get(
            IndustryThesisSessionRevision,
            UUID(result["session_revision_id"]),
        )
        identity = session.get(
            IndustryThesisSessionIdentity,
            UUID(created["session_id"]),
        )
    assert revision_two is not None
    assert revision_two.supersedes_revision_id == UUID(created["session_revision_id"])
    assert identity is not None
    assert identity.latest_revision_number == 2


def test_conflicts_fail_closed_without_additional_write(
    database,
    monkeypatch,
) -> None:
    _install_clock(
        monkeypatch,
        NOW,
        NOW + timedelta(seconds=1),
        NOW + timedelta(seconds=2),
        NOW + timedelta(seconds=3),
    )
    _clear_overrides()
    _override_read_write_factories(database)
    client = TestClient(app)
    try:
        created = client.post(
            "/industry-analysis/api/sessions",
            params={"dry_run": "false"},
            json=_session_input(),
        ).json()
        changes = _session_input()
        changes.pop("revision_note")
        changes["thesis_title_reviewed"] = "第一次修订"
        first = client.post(
            f"/industry-analysis/api/sessions/{created['session_id']}/revisions",
            params={"dry_run": "false"},
            json={
                "expected_latest_revision_number": 1,
                "changes": changes,
                "revision_note": "第一次修订",
            },
        )
        stale = client.post(
            f"/industry-analysis/api/sessions/{created['session_id']}/revisions",
            params={"dry_run": "false"},
            json={
                "expected_latest_revision_number": 1,
                "changes": changes,
                "revision_note": "陈旧修订",
            },
        )
        no_change = client.post(
            f"/industry-analysis/api/sessions/{created['session_id']}/revisions",
            params={"dry_run": "false"},
            json={
                "expected_latest_revision_number": 2,
                "changes": changes,
                "revision_note": "没有变化",
            },
        )
        backward_changes = dict(changes)
        backward_changes["thesis_title_reviewed"] = "截止日向后移动"
        backward_changes["information_cutoff_date"] = "2026-07-22"
        chronology = client.post(
            f"/industry-analysis/api/sessions/{created['session_id']}/revisions",
            params={"dry_run": "false"},
            json={
                "expected_latest_revision_number": 2,
                "changes": backward_changes,
                "revision_note": "非法时间倒退",
            },
        )
    finally:
        _clear_overrides()

    assert first.status_code == 200
    assert stale.status_code == 409
    assert stale.json()["detail"]["code"] == "industry_thesis_revision_conflict"
    assert no_change.status_code == 409
    assert no_change.json()["detail"]["code"] == "industry_thesis_no_change"
    assert chronology.status_code == 409
    assert chronology.json()["detail"]["code"] == "industry_thesis_chronology_invalid"
    assert _counts(database) == (1, 2)


def test_request_validation_is_strict_and_occurs_before_command_execution(
    database,
    monkeypatch,
) -> None:
    called = False

    def forbidden_service(_factory):
        nonlocal called
        called = True
        raise AssertionError("command service must not run")

    monkeypatch.setattr(industry_api, "IndustryThesisCommandService", forbidden_service)
    _clear_overrides()
    _override_read_write_factories(database)
    client = TestClient(app)
    try:
        unknown = _session_input()
        unknown["unexpected"] = True
        response = client.post("/industry-analysis/api/sessions", json=unknown)
        nested_unknown = client.post(
            f"/industry-analysis/api/sessions/{UUID(int=999)}/revisions",
            json={
                "expected_latest_revision_number": 1,
                "changes": {
                    "thesis_text_original": "范围修订",
                    "revision_note": "不允许嵌套",
                },
                "revision_note": "顶层修订说明",
            },
        )
        wrong_type = client.post(
            "/industry-analysis/api/sessions",
            content="{}",
            headers={"Content-Type": "text/plain"},
        )
        malformed = client.post(
            "/industry-analysis/api/sessions",
            content=b'{"thesis_text_original":',
            headers={"Content-Type": "application/json"},
        )
        oversized = client.post(
            "/industry-analysis/api/sessions",
            content=b"{" + b" " * 1_048_576 + b"}",
            headers={"Content-Type": "application/json"},
        )
    finally:
        _clear_overrides()

    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "industry_analysis_request_invalid"
    assert nested_unknown.status_code == 422
    assert nested_unknown.json()["detail"]["code"] == "industry_analysis_request_invalid"
    assert wrong_type.status_code == 400
    assert wrong_type.json()["detail"]["code"] == "industry_analysis_json_required"
    assert malformed.status_code == 400
    assert malformed.json()["detail"]["code"] == "industry_analysis_json_invalid"
    assert oversized.status_code == 413
    assert oversized.json()["detail"]["code"] == "industry_analysis_body_too_large"
    assert called is False


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
    assert response.json()["detail"]["code"] == "industry_analysis_database_unavailable"


def test_static_assets_are_local_strict_and_preserve_ambiguous_inputs() -> None:
    root = Path(__file__).resolve().parents[1] / "industry_analysis" / "static"
    html = (root / "workbench.html").read_text(encoding="utf-8")
    script = (root / "workbench.js").read_text(encoding="utf-8")

    assert "http://" not in script
    assert "https://" not in script
    assert "localStorage" in script
    assert 'fetch("/industry-analysis/api/' in script
    assert 'document.querySelector("#history-limit").value = "20"' in script
    assert "const { revision_note: revisionNote, ...changes } = payload;" in script
    assert WORKBENCH_SCOPE_CONTRACT in script
    assert "assertEditableRevision(revision);" in script
    assert "当前页面不会覆盖其结构化数据" in script
    assert "页面已保留你的输入" in script
    assert "请先返回研究历史确认是否已写入，再重试" in script
    assert "UUID" not in html
    assert "fingerprint" not in html
    assert "检查研究范围" in html
    assert "保存研究主题" in html
    assert "构建候选公司池（Phase 1C）" in html
    assert "disabled" in html
    assert "/candidate-builds" not in script
    assert "/reviews" not in script
    assert "buy" not in script.lower()
    assert "broker" not in script.lower()


def test_offline_workbench_demo_runs_create_revise_history_flow() -> None:
    payload = run_demo()
    assert payload["created"]["revision_number"] == 1
    assert payload["revised"]["revision_number"] == 2
    assert payload["history"]["session_count"] == 1
    assert payload["history"]["sessions"][0]["visible_revision_count"] == 2
    assert payload["history"]["notices"]["not_investment_advice"] is True
