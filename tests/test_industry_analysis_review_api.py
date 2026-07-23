from __future__ import annotations

from datetime import date, datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

import backend.api.industry_analysis_review as review_api
from backend.database.engine import build_session_factory
from backend.database.models import Base
from backend.main import app
import industry_alpha.stage1_models  # noqa: F401 - register exact FK targets

UTC = timezone.utc
CUTOFF = date(2026, 7, 23)
BOUNDARY = datetime(2026, 7, 23, 8, 0, tzinfo=UTC)
SESSION_ID = uuid4()
SOURCE_REVISION_ID = uuid4()
REVIEWED_REVISION_ID = uuid4()
CANDIDATE_A = uuid4()
CANDIDATE_B = uuid4()


@pytest.fixture()
def client(monkeypatch):
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = build_session_factory(engine)
    app.dependency_overrides[
        review_api.get_industry_analysis_session_factory
    ] = lambda: factory
    app.dependency_overrides[
        review_api.get_industry_analysis_write_factory
    ] = lambda: factory
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
    return urlencode(values)


def _view() -> dict:
    return {
        "session_id": str(SESSION_ID),
        "session_revision_id": str(SOURCE_REVISION_ID),
        "session_revision_number": 2,
        "thesis_title": "电子特气需求",
        "thesis_text_original": "AI 数据中心扩张带动电子特气需求",
        "workflow_state": "candidate_build_ready",
        "coverage_state": "partial_local_coverage",
        "information_cutoff_date": CUTOFF.isoformat(),
        "recorded_at_utc": BOUNDARY.isoformat(),
        "candidate_count": 2,
        "candidates": [
            {
                "candidate_revision_id": str(CANDIDATE_A),
                "revision_number": 1,
            },
            {
                "candidate_revision_id": str(CANDIDATE_B),
                "revision_number": 1,
            },
        ],
    }


def _review_payload() -> dict:
    return {
        "expected_session_latest_revision_number": 2,
        "acceptance_plan_version": review_api.ACCEPTANCE_PLAN_VERSION,
        "decisions": [
            {
                "candidate_revision_id": str(CANDIDATE_A),
                "expected_latest_revision_number": 1,
                "decision": "selected_for_acceptance",
                "final_proposed_exposure_type": "direct",
                "rationale_text": "产品和认证路径直接对应需求扩张。",
                "uncertainty_state": "limited_evidence",
                "uncertainty_note": "仍需验证收入占比。",
            },
            {
                "candidate_revision_id": str(CANDIDATE_B),
                "expected_latest_revision_number": 1,
                "decision": "unresolved",
                "final_proposed_exposure_type": None,
                "rationale_text": "受益路径存在但尚不完整。",
                "uncertainty_state": "awaiting_verification",
                "uncertainty_note": "等待客户认证信息。",
            },
        ],
        "revision_note": "完整审阅两条精确候选路径",
    }


def test_review_and_result_pages_are_active_and_static_boundaries_are_safe(client) -> None:
    http, _ = client
    review = http.get(
        f"/industry-analysis/sessions/{SESSION_ID}/revisions/{SOURCE_REVISION_ID}/review?{_query()}"
    )
    assert review.status_code == 200
    assert "逐条完成三态审阅" in review.text
    assert "检查审阅结果" in review.text
    assert "保存审阅计划" in review.text

    result = http.get(
        f"/industry-analysis/sessions/{SESSION_ID}/revisions/{REVIEWED_REVISION_ID}/result?{_query()}"
    )
    assert result.status_code == 200
    assert "审阅计划已生成，但尚未写入正式产业地图" in result.text
    assert "review_result.js" in result.text

    root = Path(__file__).resolve().parents[1]
    scripts = [
        (root / "industry_analysis" / "static" / "candidate_review.js").read_text(
            encoding="utf-8"
        ),
        (root / "industry_analysis" / "static" / "review_result.js").read_text(
            encoding="utf-8"
        ),
    ]
    forbidden = [
        'fetch("http',
        "fetch('http",
        "WebSocket",
        "EventSource",
        "broker",
        "position sizing",
        "target price",
    ]
    assert all(token not in script for script in scripts for token in forbidden)
    assert "页面不会自动重试" in scripts[0]
    assert "dry_run" in scripts[0]
    assert "acceptance_plan_fingerprint_sha256" in scripts[1]


def test_review_view_adapter_preserves_exact_route_arguments(client) -> None:
    http, monkeypatch = client
    calls = []

    class FakeViewService:
        def __init__(self, _session):
            pass

        def get_review_view(self, **kwargs):
            calls.append(kwargs)
            return _view()

    monkeypatch.setattr(
        review_api,
        "IndustryThesisReviewWorkbenchQueryService",
        FakeViewService,
    )
    response = http.get(
        f"/industry-analysis/api/session-revisions/{SOURCE_REVISION_ID}/review-view?{_query()}"
    )
    assert response.status_code == 200
    assert response.json()["candidate_count"] == 2
    assert calls == [
        {
            "session_id": SESSION_ID,
            "session_revision_id": SOURCE_REVISION_ID,
            "as_of_cutoff": CUTOFF,
            "as_of_recorded_at_utc": BOUNDARY,
        }
    ]


def test_review_write_requires_strict_complete_json_and_maps_user_text_exactly(client) -> None:
    http, monkeypatch = client
    url = (
        f"/industry-analysis/api/session-revisions/{SOURCE_REVISION_ID}/reviews?"
        f"{_query(dry_run='false')}"
    )
    wrong_type = http.post(
        url,
        content="{}",
        headers={"Content-Type": "text/plain"},
    )
    assert wrong_type.status_code == 400
    assert wrong_type.json()["detail"]["code"] == "industry_analysis_json_required"

    malformed = http.post(
        url,
        content=b'{"expected_session_latest_revision_number":',
        headers={"Content-Type": "application/json"},
    )
    assert malformed.status_code == 400

    oversized = http.post(
        url,
        content=b"{" + b" " * 1_048_576 + b"}",
        headers={"Content-Type": "application/json"},
    )
    assert oversized.status_code == 413
    assert oversized.json()["detail"]["code"] == "industry_analysis_body_too_large"

    unknown = http.post(
        url,
        json={
            "expected_session_latest_revision_number": 2,
            "acceptance_plan_version": review_api.ACCEPTANCE_PLAN_VERSION,
            "decisions": [],
            "revision_note": "完整审阅",
            "automatic_acceptance": True,
        },
    )
    assert unknown.status_code == 422

    class FakeViewService:
        def __init__(self, _session):
            pass

        def get_review_view(self, **_kwargs):
            return _view()

    captured = []

    class FakeReviewService:
        def __init__(self, _factory):
            pass

        def review_candidates(self, command, *, dry_run):
            captured.append((command, dry_run))
            return {
                "dry_run": dry_run,
                "session_id": str(SESSION_ID),
                "source_session_revision_id": str(SOURCE_REVISION_ID),
                "reviewed_session_revision_id": str(REVIEWED_REVISION_ID),
                "reviewed_session_revision_number": 3,
                "workflow_state": "reviewed_plan_ready",
                "information_cutoff_date": CUTOFF.isoformat(),
                "session_recorded_at_utc": BOUNDARY.isoformat(),
                "candidate_recorded_at_utc": datetime(
                    2026, 7, 23, 8, 0, 0, 1, tzinfo=UTC
                ).isoformat(),
                "candidate_count": 2,
                "acceptance_plan": {
                    "selected_candidates": [
                        {"candidate_revision_id": str(uuid4())}
                    ],
                    "rejected_candidate_revision_ids": [],
                    "unresolved_candidate_revision_ids": [str(uuid4())],
                },
                "acceptance_plan_fingerprint_sha256": "f" * 64,
            }

    monkeypatch.setattr(
        review_api,
        "IndustryThesisReviewWorkbenchQueryService",
        FakeViewService,
    )
    monkeypatch.setattr(
        review_api,
        "IndustryThesisProposalReviewService",
        FakeReviewService,
    )
    payload = _review_payload()
    response = http.post(url, json=payload)
    assert response.status_code == 200
    result = response.json()
    assert result["selected_count"] == 1
    assert result["unresolved_count"] == 1
    assert result["rejected_count"] == 0
    assert f"/sessions/{SESSION_ID}/revisions/{REVIEWED_REVISION_ID}/result" in result[
        "result_path"
    ]
    assert captured[0][1] is False
    command = captured[0][0]
    assert command["session_revision_id"] == str(SOURCE_REVISION_ID)
    assert command["decisions"][0]["rationale"] == {
        "user_review_rationale": "产品和认证路径直接对应需求扩张。"
    }
    assert command["decisions"][1]["uncertainty"] == {
        "state": "awaiting_verification",
        "note": "等待客户认证信息。",
    }

    incomplete = dict(payload)
    incomplete["decisions"] = payload["decisions"][:1]
    response = http.post(url, json=incomplete)
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "industry_thesis_review_incomplete"

    duplicate = dict(payload)
    duplicate["decisions"] = [payload["decisions"][0], payload["decisions"][0]]
    response = http.post(url, json=duplicate)
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "industry_thesis_duplicate_review"

    invalid_exposure = _review_payload()
    invalid_exposure["decisions"][1]["decision"] = "rejected_by_user"
    invalid_exposure["decisions"][1]["final_proposed_exposure_type"] = "indirect"
    response = http.post(url, json=invalid_exposure)
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "industry_thesis_review_invalid"


def test_reviewed_plan_adapter_preserves_exact_result_route(client) -> None:
    http, monkeypatch = client
    expected = {
        "session_id": str(SESSION_ID),
        "reviewed_session_revision_id": str(REVIEWED_REVISION_ID),
        "candidate_count": 3,
        "selected_candidates": [{"candidate_revision_id": "a"}],
        "unresolved_candidates": [{"candidate_revision_id": "b"}],
        "rejected_candidates": [{"candidate_revision_id": "c"}],
    }
    calls = []

    class FakeViewService:
        def __init__(self, _session):
            pass

        def get_result_view(self, **kwargs):
            calls.append(kwargs)
            return expected

    monkeypatch.setattr(
        review_api,
        "IndustryThesisReviewWorkbenchQueryService",
        FakeViewService,
    )
    response = http.get(
        f"/industry-analysis/api/reviewed-plans/{REVIEWED_REVISION_ID}?{_query()}"
    )
    assert response.status_code == 200
    assert response.json() == expected
    assert calls == [
        {
            "session_id": SESSION_ID,
            "reviewed_session_revision_id": REVIEWED_REVISION_ID,
            "as_of_cutoff": CUTOFF,
            "as_of_recorded_at_utc": BOUNDARY,
        }
    ]
