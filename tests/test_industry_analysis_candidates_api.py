from __future__ import annotations

from datetime import date, datetime, timezone
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

import backend.api.industry_analysis_candidates as candidate_api
from backend.database.engine import build_session_factory
from backend.database.models import Base
from backend.main import app
import industry_alpha.stage1_models  # noqa: F401 - register exact FK targets

UTC = timezone.utc
CUTOFF = date(2026, 7, 23)
BOUNDARY = datetime(2026, 7, 23, 4, 0, tzinfo=UTC)
SESSION_ID = uuid4()
REVISION_ID = uuid4()
POOL_ID = uuid4()


@pytest.fixture()
def client(monkeypatch):
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = build_session_factory(engine)
    app.dependency_overrides[candidate_api.get_industry_analysis_session_factory] = lambda: factory
    app.dependency_overrides[candidate_api.get_industry_analysis_write_factory] = lambda: factory
    try:
        yield TestClient(app), monkeypatch
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


def _query(**extra) -> str:
    values = {
        "session_id": str(SESSION_ID),
        "as_of_cutoff": CUTOFF.isoformat(),
        "as_of_recorded_at_utc": BOUNDARY.isoformat(),
    }
    values.update(extra)
    from urllib.parse import urlencode

    return urlencode(values)


def test_exact_candidate_page_route_and_static_boundary(client) -> None:
    http, _ = client
    response = http.get(
        f"/industry-analysis/sessions/{SESSION_ID}/revisions/{REVISION_ID}/review"
        f"?as_of_cutoff={CUTOFF.isoformat()}&as_of_recorded_at_utc={BOUNDARY.isoformat()}"
    )
    assert response.status_code == 200
    assert "当前已构建本地范围全量候选" in response.text
    assert "逐条完成三态审阅" in response.text
    assert "检查审阅结果" in response.text
    assert "review-save-button" in response.text
    assert "candidate_review.js" in response.text

    root = Path(__file__).resolve().parents[1]
    script = (root / "industry_analysis" / "static" / "candidate_review.js").read_text(encoding="utf-8")
    enhancement = (root / "industry_analysis" / "static" / "workbench_phase1c.js").read_text(encoding="utf-8")
    forbidden = ["fetch(\"http", "fetch('http", "WebSocket", "EventSource", "buy", "sell", "target price"]
    assert all(value not in script for value in forbidden)
    assert "window.location.assign" in script
    assert "页面不会自动重试" in script
    assert "data-phase1d-link" in enhancement
    assert 'isResult ? "result" : "review"' in enhancement


def test_source_options_adapter_preserves_exact_route_arguments(client) -> None:
    http, monkeypatch = client
    calls = []

    class FakeService:
        def __init__(self, _session):
            pass

        def candidate_source_options(self, **kwargs):
            calls.append(kwargs)
            return {
                "session_id": str(kwargs["session_id"]),
                "session_revision_id": str(kwargs["session_revision_id"]),
                "session_revision_number": 1,
                "workflow_state": "candidate_build_ready",
                "coverage_state": "partial_local_coverage",
                "information_cutoff_date": CUTOFF.isoformat(),
                "as_of_cutoff": CUTOFF.isoformat(),
                "as_of_recorded_at_utc": BOUNDARY.isoformat(),
                "is_exact_latest_revision": True,
                "build_allowed": True,
                "company_seed_count": 1,
                "company_seeds": [{"selected": True}],
                "map_count": 1,
                "maps": [{"selected_candidate_pool_revision_id": None}],
                "notices": {"first_pool_not_selected": True},
            }

    monkeypatch.setattr(candidate_api, "IndustryThesisCandidateWorkbenchService", FakeService)
    response = http.get(
        f"/industry-analysis/api/session-revisions/{REVISION_ID}/candidate-source-options?{_query()}"
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["notices"]["first_pool_not_selected"] is True
    assert payload["maps"][0]["selected_candidate_pool_revision_id"] is None
    assert calls == [
        {
            "session_id": SESSION_ID,
            "session_revision_id": REVISION_ID,
            "as_of_cutoff": CUTOFF,
            "as_of_recorded_at_utc": BOUNDARY,
        }
    ]


def test_candidate_build_strict_json_and_exact_review_link(client) -> None:
    http, monkeypatch = client
    url = (
        f"/industry-analysis/api/session-revisions/{REVISION_ID}/candidate-builds?"
        f"{_query(dry_run='true')}"
    )
    malformed = http.post(
        url,
        content=b'{"expected_session_latest_revision_number":',
        headers={"Content-Type": "application/json"},
    )
    assert malformed.status_code == 400

    unknown = http.post(
        url,
        json={
            "expected_session_latest_revision_number": 1,
            "selected_candidate_pool_revision_ids": [],
            "automatic_first_pool": True,
        },
    )
    assert unknown.status_code == 422

    class FakeComposer:
        def __init__(self, _session):
            pass

        def compose_candidate_build(self, **kwargs):
            assert kwargs["session_id"] == SESSION_ID
            assert kwargs["session_revision_id"] == REVISION_ID
            assert kwargs["selected_candidate_pool_revision_ids"] == [POOL_ID]
            return (
                {
                    "session_revision_id": str(REVISION_ID),
                    "expected_session_latest_revision_number": 1,
                    "builder_version": "fixture",
                    "allowed_source_kinds": ["user_seed"],
                    "proposals": [{"source_kind": "user_seed"}],
                },
                {
                    "company_seed_proposal_count": 1,
                    "stage1_proposal_count": 0,
                    "proposal_count": 1,
                    "selected_candidate_pool_revision_ids": [str(POOL_ID)],
                },
            )

    class FakeCommand:
        def __init__(self, _factory):
            pass

        def build_candidates(self, _command, *, dry_run):
            assert dry_run is True
            return {
                "dry_run": True,
                "session_id": str(SESSION_ID),
                "session_revision_id": str(REVISION_ID),
                "session_revision_number": 1,
                "coverage_state": "partial_local_coverage",
                "information_cutoff_date": CUTOFF.isoformat(),
                "recorded_at_utc": BOUNDARY.isoformat(),
                "candidate_count": 1,
                "candidates": [{"review_state": "proposed"}],
            }

    monkeypatch.setattr(candidate_api, "IndustryThesisCandidateWorkbenchService", FakeComposer)
    monkeypatch.setattr(candidate_api, "IndustryThesisWorkbenchCandidateCommandService", FakeCommand)
    response = http.post(
        url,
        json={
            "expected_session_latest_revision_number": 1,
            "selected_candidate_pool_revision_ids": [str(POOL_ID)],
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["review_enabled"] is False
    assert payload["review_phase"] == "Phase 1D"
    assert payload["composition"]["proposal_count"] == 1
    assert f"/sessions/{SESSION_ID}/revisions/{REVISION_ID}/review" in payload["review_path"]
    assert "%2B00%3A00" in payload["review_path"]


def test_candidate_universe_adapter_preserves_every_row(client) -> None:
    http, monkeypatch = client

    class FakeQuery:
        def __init__(self, _session):
            pass

        def list_candidate_revisions(self, revision_id: UUID, **_kwargs):
            assert revision_id == REVISION_ID
            return {
                "session_id": str(SESSION_ID),
                "session_revision_id": str(REVISION_ID),
                "session_revision_number": 1,
                "coverage_state": "partial_local_coverage",
                "information_cutoff_date": CUTOFF.isoformat(),
                "candidate_count": 3,
                "candidates": [
                    {"candidate_key": "a", "source_kind": "existing_industry_map_revision"},
                    {"candidate_key": "b", "source_kind": "user_seed"},
                    {"candidate_key": "c", "source_kind": "user_seed"},
                ],
            }

    monkeypatch.setattr(candidate_api, "IndustryThesisQueryService", FakeQuery)
    response = http.get(
        f"/industry-analysis/api/session-revisions/{REVISION_ID}/candidates?{_query()}"
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["candidate_count"] == 3
    assert [item["candidate_key"] for item in payload["candidates"]] == ["a", "b", "c"]
    assert payload["universe_label"] == "当前已构建本地范围全量候选"
    assert payload["review_enabled"] is True
