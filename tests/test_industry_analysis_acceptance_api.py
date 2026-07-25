from __future__ import annotations

from datetime import date, datetime, timezone
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

import backend.api.industry_analysis as industry_api
import backend.api.industry_analysis_acceptance as acceptance_api
from backend.database.engine import build_session_factory
from backend.database.models import Base
from backend.main import app
import industry_alpha.stage1_models  # noqa: F401 - register exact FK targets


UTC = timezone.utc
CUTOFF = date(2026, 7, 25)
BOUNDARY = datetime(2026, 7, 25, 12, 0, tzinfo=UTC)
SESSION_ID = uuid4()
REVIEWED_REVISION_ID = uuid4()
ACCEPTED_REVISION_ID = uuid4()
OUTPUT_REVISION_ID = uuid4()
CANDIDATE_ID = uuid4()
CASE_ID = uuid4()
MAP_ID = uuid4()
MAP_REVISION_ID = uuid4()


@pytest.fixture()
def client():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = build_session_factory(engine)
    app.dependency_overrides[
        acceptance_api.get_industry_analysis_session_factory
    ] = lambda: factory
    app.dependency_overrides[
        acceptance_api.get_industry_analysis_write_factory
    ] = lambda: factory
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


def _query() -> dict[str, str]:
    return {
        "session_id": str(SESSION_ID),
        "as_of_cutoff": CUTOFF.isoformat(),
        "as_of_recorded_at_utc": BOUNDARY.isoformat(),
    }


def _plan() -> dict:
    return {
        "reviewed_session_revision_id": str(REVIEWED_REVISION_ID),
        "expected_session_latest_revision_number": 4,
        "reviewed_plan_fingerprint_sha256": "a" * 64,
        "research_case_id": str(CASE_ID),
        "map_mode": "reuse_exact_existing_map_revision",
        "industry_map_id": str(MAP_ID),
        "industry_map_revision_id": str(MAP_REVISION_ID),
        "candidate_owner_bindings": [
            {
                "reviewed_candidate_revision_id": str(CANDIDATE_ID),
                "sequence": 0,
                "stage1_operation": "reuse_exact_beneficiary_revision",
                "stage1": {
                    "beneficiary_id": str(uuid4()),
                    "beneficiary_revision_id": str(uuid4()),
                    "stock_basic_record_id": 7,
                },
                "semantic_operation": "none",
                "semantic": None,
                "readiness_note": "仍需后续公司研究。",
            }
        ],
        "candidate_pool_operation": {"mode": "none_no_supported_members"},
        "output_title": "电子特气研究成果",
        "output_scope": "精确本地研究范围",
        "information_cutoff_date": CUTOFF.isoformat(),
        "revision_note": "明确接受本次研究成果",
        "owner_acceptance_plan_version": (
            "aquantai.industry-thesis-owner-acceptance-plan.v1"
        ),
    }


def _acceptance_view() -> dict:
    return {
        "session_id": str(SESSION_ID),
        "reviewed_session_revision_id": str(REVIEWED_REVISION_ID),
        "reviewed_session_revision_number": 4,
        "reviewed_plan_fingerprint_sha256": "a" * 64,
        "expected_session_latest_revision_number": 4,
        "thesis_title": "电子特气研究",
        "thesis_text_original": "电子特气供需与认证",
        "coverage_state": "reviewed_local_scope",
        "research_case": {"id": str(CASE_ID), "case_key": "case-electronic-gas"},
        "industry_map": {
            "id": str(MAP_ID),
            "map_key": "map-electronic-gas",
            "revision_id": str(MAP_REVISION_ID),
            "revision_number": 2,
            "title": "电子特气产业地图",
            "scope": "纯化、供应和客户认证",
        },
        "information_cutoff_date": CUTOFF.isoformat(),
        "recorded_at_utc": BOUNDARY.isoformat(),
        "as_of_cutoff": CUTOFF.isoformat(),
        "as_of_recorded_at_utc": BOUNDARY.isoformat(),
        "map_mode": "reuse_exact_existing_map_revision",
        "owner_acceptance_plan_version": (
            "aquantai.industry-thesis-owner-acceptance-plan.v1"
        ),
        "output_metadata_defaults": {
            "output_title": "电子特气研究",
            "output_scope": "纯化、供应和客户认证",
        },
        "members": [],
        "candidate_pool_operation_contract": {
            "create_contract": {
                "mode": "create_supported_handoff",
                "pool_key": f"industry-thesis-acceptance-v1:{REVIEWED_REVISION_ID}",
                "title_default": "电子特气研究 · supported 后续研究",
                "scope_default": "仅包含 supported 成员。",
            },
            "append_options": [],
            "reuse_options": [],
            "zero_supported_contract": {
                "mode": "none_no_supported_members",
                "notice": "仅当没有 supported 成员时可用。",
            },
        },
        "revision_note_constraints": {"required": True, "max_length": 1000},
        "blocking_reasons": [],
        "commit_possible": True,
        "primary_action": {"kind": "preview", "label": "生成变更预览"},
        "technical_details": {},
    }


def test_acceptance_and_accepted_result_pages_are_local_and_accessible(client) -> None:
    acceptance = client.get(
        f"/industry-analysis/sessions/{SESSION_ID}/revisions/"
        f"{REVIEWED_REVISION_ID}/acceptance",
        params={
            "as_of_cutoff": CUTOFF.isoformat(),
            "as_of_recorded_at_utc": BOUNDARY.isoformat(),
        },
    )
    accepted = client.get(
        f"/industry-analysis/sessions/{SESSION_ID}/revisions/"
        f"{ACCEPTED_REVISION_ID}/accepted-result",
        params={
            "as_of_cutoff": CUTOFF.isoformat(),
            "as_of_recorded_at_utc": BOUNDARY.isoformat(),
        },
    )
    assert acceptance.status_code == 200
    assert "检查并接受研究成果" in acceptance.text
    assert "生成变更预览" in acceptance.text
    assert "owner_acceptance.js" in acceptance.text
    assert 'aria-current="page"' in acceptance.text
    assert accepted.status_code == 200
    assert "完整接受成员" in accepted.text
    assert "supported 后续研究池" in accepted.text
    assert "accepted_result.js" in accepted.text

    root = Path(__file__).resolve().parents[1] / "industry_analysis" / "static"
    scripts = [
        (root / "owner_acceptance.js").read_text(encoding="utf-8"),
        (root / "accepted_result.js").read_text(encoding="utf-8"),
        (root / "review_result.js").read_text(encoding="utf-8"),
    ]
    forbidden = [
        'fetch("http',
        "fetch('http",
        "WebSocket",
        "EventSource",
        "innerHTML",
        "localStorage",
        "target price",
        "position sizing",
        "broker",
    ]
    assert all(token not in script for script in scripts for token in forbidden)
    assert "页面不会自动重试" in scripts[0]
    assert "preview_fingerprint_sha256" in scripts[0]
    assert "accepted-result-view" in scripts[1]
    assert "acceptance?" in scripts[2]


def test_acceptance_view_adapter_preserves_exact_route_and_boundaries(
    client, monkeypatch
) -> None:
    calls = []

    class FakeWorkbench:
        def __init__(self, _session):
            pass

        def get_acceptance_view(self, **kwargs):
            calls.append(kwargs)
            return _acceptance_view()

    monkeypatch.setattr(
        acceptance_api,
        "IndustryThesisOwnerAcceptanceWorkbenchQueryService",
        FakeWorkbench,
    )
    response = client.get(
        f"/industry-analysis/api/session-revisions/{REVIEWED_REVISION_ID}/"
        "owner-acceptance-view",
        params=_query(),
    )
    assert response.status_code == 200
    assert response.json()["reviewed_session_revision_id"] == str(
        REVIEWED_REVISION_ID
    )
    assert calls == [
        {
            "session_id": SESSION_ID,
            "reviewed_session_revision_id": REVIEWED_REVISION_ID,
            "as_of_cutoff": CUTOFF,
            "as_of_recorded_at_utc": BOUNDARY,
        }
    ]


def test_preview_and_commit_use_exact_flat_dto_and_matching_fingerprint(
    client, monkeypatch
) -> None:
    captured = []

    class FakeWorkbench:
        def __init__(self, _session):
            pass

        def get_acceptance_view(self, **_kwargs):
            return _acceptance_view()

    class FakeService:
        def __init__(self, _factory):
            pass

        def preview(self, raw):
            captured.append(("preview", raw))
            return {
                "commit_ready": True,
                "complete_universe_count": 1,
                "supported_handoff_count": 0,
                "candidate_pool_mode": "none_no_supported_members",
                "preview_fingerprint_sha256": "b" * 64,
                "owner_acceptance_plan_fingerprint_sha256": "b" * 64,
                "owner_transaction_id": str(uuid4()),
                "operation_summaries": [],
                "blocked_reasons": [],
                "reviewed_session_revision_id": str(REVIEWED_REVISION_ID),
                "recorded_at_utc": BOUNDARY.isoformat(),
            }

        def commit(self, raw):
            captured.append(("commit", raw))
            return {
                "idempotent_replay": False,
                "accepted_session_revision_id": str(ACCEPTED_REVISION_ID),
                "output_link_revision_id": str(OUTPUT_REVISION_ID),
                "recorded_at_utc": BOUNDARY.isoformat(),
            }

    monkeypatch.setattr(
        acceptance_api,
        "IndustryThesisOwnerAcceptanceWorkbenchQueryService",
        FakeWorkbench,
    )
    monkeypatch.setattr(
        acceptance_api,
        "IndustryThesisOwnerAcceptanceService",
        FakeService,
    )
    plan = _plan()
    preview = client.post(
        f"/industry-analysis/api/session-revisions/{REVIEWED_REVISION_ID}/"
        "owner-acceptance/preview",
        params=_query(),
        json=plan,
    )
    assert preview.status_code == 200
    assert preview.json()["primary_action"] == {
        "kind": "commit",
        "label": "确认接受研究成果",
    }
    assert captured[0] == ("preview", plan)

    commit_payload = {**plan, "preview_fingerprint_sha256": "b" * 64}
    committed = client.post(
        f"/industry-analysis/api/session-revisions/{REVIEWED_REVISION_ID}/"
        "owner-acceptance/commit",
        params=_query(),
        json=commit_payload,
    )
    assert committed.status_code == 200
    result = committed.json()
    assert captured[1] == ("commit", commit_payload)
    parsed = urlparse(result["accepted_result_path"])
    assert parsed.path.endswith(
        f"/{ACCEPTED_REVISION_ID}/accepted-result"
    )
    parsed_query = parse_qs(parsed.query)
    assert parsed_query["as_of_cutoff"] == [CUTOFF.isoformat()]
    assert parsed_query["as_of_recorded_at_utc"] == [BOUNDARY.isoformat()]

    mismatch = client.post(
        f"/industry-analysis/api/session-revisions/{uuid4()}/"
        "owner-acceptance/preview",
        params=_query(),
        json=plan,
    )
    assert mismatch.status_code == 409
    assert mismatch.json()["detail"]["preserve_form"] is True

    unknown = client.post(
        f"/industry-analysis/api/session-revisions/{REVIEWED_REVISION_ID}/"
        "owner-acceptance/preview",
        params=_query(),
        json={**plan, "automatic_acceptance": True},
    )
    assert unknown.status_code == 422
    assert unknown.json()["detail"]["code"] == "industry_analysis_request_invalid"


def test_accepted_result_adapter_and_history_continuation_are_exact(
    client, monkeypatch
) -> None:
    expected = {
        "session_id": str(SESSION_ID),
        "accepted_session_revision_id": str(ACCEPTED_REVISION_ID),
        "output_link_revision_id": str(OUTPUT_REVISION_ID),
        "members": [],
        "supported_handoff_members": [],
        "facts": [],
    }
    calls = []

    class FakeWorkbench:
        def __init__(self, _session):
            pass

        def get_accepted_result_view(self, **kwargs):
            calls.append(kwargs)
            return expected

    monkeypatch.setattr(
        acceptance_api,
        "IndustryThesisOwnerAcceptanceWorkbenchQueryService",
        FakeWorkbench,
    )
    response = client.get(
        f"/industry-analysis/api/session-revisions/{ACCEPTED_REVISION_ID}/"
        "accepted-result-view",
        params=_query(),
    )
    assert response.status_code == 200
    assert response.json() == expected
    assert calls == [
        {
            "session_id": SESSION_ID,
            "accepted_session_revision_id": ACCEPTED_REVISION_ID,
            "as_of_cutoff": CUTOFF,
            "as_of_recorded_at_utc": BOUNDARY,
        }
    ]

    continuation = industry_api._exact_continuation(
        {
            "session_id": str(SESSION_ID),
            "visible_latest_revision_id": str(ACCEPTED_REVISION_ID),
            "visible_latest_revision_number": 5,
            "information_cutoff_date": CUTOFF.isoformat(),
            "recorded_at_utc": BOUNDARY.isoformat(),
            "workflow_state": "accepted_outputs_linked",
        }
    )
    assert continuation["kind"] == "accepted_result"
    assert continuation["label"] == "查看已接受成果"
    parsed = urlparse(continuation["path"])
    assert parsed.path.endswith(
        f"/{ACCEPTED_REVISION_ID}/accepted-result"
    )
    assert parse_qs(parsed.query) == {
        "as_of_cutoff": [CUTOFF.isoformat()],
        "as_of_recorded_at_utc": [BOUNDARY.isoformat()],
    }
