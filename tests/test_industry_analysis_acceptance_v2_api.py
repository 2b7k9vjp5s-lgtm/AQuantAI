from __future__ import annotations

from copy import deepcopy
from datetime import timedelta
from urllib.parse import urlencode
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.pool import StaticPool

import backend.api.industry_analysis_acceptance as acceptance_api
from backend.database.engine import build_session_factory
from backend.database.models import Base
from backend.main import app
from industry_alpha.industry_thesis_models import (
    IndustryThesisOutputLinkRevision,
    IndustryThesisSessionRevision,
)
from industry_alpha.stage1_fixtures import build_stage1_beneficiary_fixture
from industry_alpha.stage1_models import Stage1CandidatePoolRevision
from tests import test_industry_thesis_owner_acceptance as owner_fixture


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


@pytest.fixture()
def client(database):
    app.dependency_overrides[
        acceptance_api.get_industry_analysis_session_factory
    ] = lambda: database
    app.dependency_overrides[
        acceptance_api.get_industry_analysis_write_factory
    ] = lambda: database
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


def _query(session_id: str, *, recorded_at=None) -> str:
    boundary = recorded_at or owner_fixture.BASE_TIME + timedelta(seconds=3)
    return urlencode(
        {
            "session_id": session_id,
            "as_of_cutoff": owner_fixture.CUTOFF.isoformat(),
            "as_of_recorded_at_utc": boundary.isoformat(),
        }
    )


def _counts(database) -> tuple[int, int, int]:
    with database() as session:
        return (
            session.scalar(
                select(func.count()).select_from(IndustryThesisSessionRevision)
            ),
            session.scalar(
                select(func.count()).select_from(IndustryThesisOutputLinkRevision)
            ),
            session.scalar(
                select(func.count()).select_from(Stage1CandidatePoolRevision)
            ),
        )


def _reviewed(database, beneficiary_ids):
    return owner_fixture._build_reviewed(
        database,
        beneficiary_ids=tuple(beneficiary_ids),
    )


def _payload_from_view(view: dict) -> dict:
    bindings = []
    supported = False
    for member in view["members"]:
        options = member["stage1_reuse_options"]
        assert options
        option = max(options, key=lambda item: item["revision_number"])
        supported = supported or option["assessment_status"] == "supported"
        bindings.append(
            {
                "reviewed_candidate_revision_id": member[
                    "reviewed_candidate_revision_id"
                ],
                "sequence": member["sequence"],
                "stage1_operation": "reuse_exact_beneficiary_revision",
                "stage1": {
                    "beneficiary_id": option["beneficiary_id"],
                    "beneficiary_revision_id": option["beneficiary_revision_id"],
                    "stock_basic_record_id": option["stock_basic_record_id"],
                },
                "semantic_operation": "none",
                "semantic": None,
                "readiness_note": "普通用户明确复用精确 Stage 1 版本。",
            }
        )
    if supported:
        create = view["candidate_pool_operation_contract"]["create_contract"]
        pool = {
            "mode": "create_supported_handoff",
            "pool_key": create["pool_key"],
            "title": create["title_default"],
            "scope": create["scope_default"],
        }
    else:
        pool = {"mode": "none_no_supported_members"}
    defaults = view["output_metadata_defaults"]
    return {
        "reviewed_session_revision_id": view["reviewed_session_revision_id"],
        "expected_session_latest_revision_number": view[
            "expected_session_latest_revision_number"
        ],
        "reviewed_plan_fingerprint_sha256": view[
            "reviewed_plan_fingerprint_sha256"
        ],
        "research_case_id": view["owner_context"]["research_case_id"],
        "map_mode": view["owner_context"]["map_mode"],
        "industry_map_id": view["owner_context"]["industry_map_id"],
        "industry_map_revision_id": view["owner_context"][
            "industry_map_revision_id"
        ],
        "candidate_owner_bindings": bindings,
        "candidate_pool_operation": pool,
        "output_title": defaults["output_title"],
        "output_scope": defaults["output_scope"],
        "information_cutoff_date": view["information_cutoff_date"],
        "revision_note": "普通用户确认精确研究归属并接受完整成果。",
        "owner_acceptance_plan_version": view[
            "owner_acceptance_plan_version"
        ],
    }


def _view(client, review: dict) -> tuple[str, dict]:
    session_id = review["acceptance_plan"]["session_id"]
    reviewed_id = review["reviewed_session_revision_id"]
    query = _query(session_id)
    response = client.get(
        f"/industry-analysis/api/session-revisions/{reviewed_id}/"
        f"owner-acceptance-view?{query}"
    )
    assert response.status_code == 200, response.text
    return query, response.json()


def test_three_company_preview_commit_and_exact_result(database, client) -> None:
    fixture = build_stage1_beneficiary_fixture(database)
    review, _industry_map, _map_revision, _rows = _reviewed(
        database,
        (
            fixture.direct_beneficiary_id,
            fixture.secondary_beneficiary_id,
            fixture.draft_beneficiary_id,
        ),
    )
    query, view = _view(client, review)
    assert len(view["members"]) == 3
    assert view["owner_context"] == review["acceptance_plan"]["owner_context"]
    payload = _payload_from_view(view)
    counts_before = _counts(database)

    reviewed_id = review["reviewed_session_revision_id"]
    preview = client.post(
        f"/industry-analysis/api/session-revisions/{reviewed_id}/"
        f"owner-acceptance/preview?{query}",
        json=payload,
    )
    assert preview.status_code == 200, preview.text
    preview_body = preview.json()
    assert preview_body["commit_ready"] is True
    assert preview_body["complete_universe_count"] == 3
    assert preview_body["supported_handoff_count"] == 2
    assert _counts(database) == counts_before

    commit_payload = {
        **payload,
        "preview_fingerprint_sha256": preview_body[
            "preview_fingerprint_sha256"
        ],
    }
    commit = client.post(
        f"/industry-analysis/api/session-revisions/{reviewed_id}/"
        f"owner-acceptance/commit?{query}",
        json=commit_payload,
    )
    assert commit.status_code == 200, commit.text
    committed = commit.json()
    assert committed["complete_universe_count"] == 3
    assert committed["supported_handoff_count"] == 2
    assert committed["accepted_candidate_pool_revision_id"] is not None
    assert committed["accepted_result_path"].startswith("/industry-analysis/")

    result_query = _query(
        review["acceptance_plan"]["session_id"],
        recorded_at=committed["recorded_at_utc"],
    )
    result = client.get(
        f"/industry-analysis/api/session-revisions/"
        f"{committed['accepted_session_revision_id']}/accepted-result-view?"
        f"{result_query}"
    )
    assert result.status_code == 200, result.text
    body = result.json()
    assert body["complete_member_count"] == 3
    assert body["supported_handoff_count"] == 2
    assert len(body["supported_handoff_members"]) == 2
    assert body["ranking_applied"] is False
    assert body["research_case_id"] == view["owner_context"]["research_case_id"]
    assert body["industry_map_id"] == view["owner_context"]["industry_map_id"]
    assert body["industry_map_revision_id"] == view["owner_context"][
        "industry_map_revision_id"
    ]


def test_context_substitution_rejected_before_writes(database, client) -> None:
    fixture = build_stage1_beneficiary_fixture(database)
    review, _industry_map, _map_revision, _rows = _reviewed(
        database,
        (fixture.direct_beneficiary_id,),
    )
    query, view = _view(client, review)
    payload = _payload_from_view(view)
    counts_before = _counts(database)
    reviewed_id = review["reviewed_session_revision_id"]

    substituted = deepcopy(payload)
    substituted["industry_map_id"] = str(uuid4())
    response = client.post(
        f"/industry-analysis/api/session-revisions/{reviewed_id}/"
        f"owner-acceptance/preview?{query}",
        json=substituted,
    )
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == (
        "INDUSTRY_THESIS_ACCEPTANCE_EXACT_MAP_REQUIRED"
    )
    assert _counts(database) == counts_before

    revision_substitution = deepcopy(payload)
    revision_substitution["industry_map_revision_id"] = str(uuid4())
    response = client.post(
        f"/industry-analysis/api/session-revisions/{reviewed_id}/"
        f"owner-acceptance/preview?{query}",
        json=revision_substitution,
    )
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == (
        "INDUSTRY_THESIS_ACCEPTANCE_MAP_REVISION_MISMATCH"
    )
    assert _counts(database) == counts_before


def test_zero_supported_preserves_complete_result_without_pool(database, client) -> None:
    fixture = build_stage1_beneficiary_fixture(database)
    review, _industry_map, _map_revision, _rows = _reviewed(
        database,
        (
            fixture.draft_beneficiary_id,
            fixture.disputed_beneficiary_id,
        ),
    )
    query, view = _view(client, review)
    payload = _payload_from_view(view)
    assert payload["candidate_pool_operation"] == {
        "mode": "none_no_supported_members"
    }
    reviewed_id = review["reviewed_session_revision_id"]

    preview = client.post(
        f"/industry-analysis/api/session-revisions/{reviewed_id}/"
        f"owner-acceptance/preview?{query}",
        json=payload,
    )
    assert preview.status_code == 200, preview.text
    preview_body = preview.json()
    assert preview_body["complete_universe_count"] == 2
    assert preview_body["supported_handoff_count"] == 0
    assert preview_body["accepted_candidate_pool_revision_id"] is None

    commit = client.post(
        f"/industry-analysis/api/session-revisions/{reviewed_id}/"
        f"owner-acceptance/commit?{query}",
        json={
            **payload,
            "preview_fingerprint_sha256": preview_body[
                "preview_fingerprint_sha256"
            ],
        },
    )
    assert commit.status_code == 200, commit.text
    committed = commit.json()
    assert committed["supported_handoff_count"] == 0
    assert committed["accepted_candidate_pool_revision_id"] is None

    result_query = _query(
        review["acceptance_plan"]["session_id"],
        recorded_at=committed["recorded_at_utc"],
    )
    result = client.get(
        f"/industry-analysis/api/session-revisions/"
        f"{committed['accepted_session_revision_id']}/accepted-result-view?"
        f"{result_query}"
    )
    assert result.status_code == 200, result.text
    body = result.json()
    assert body["complete_member_count"] == 2
    assert body["supported_handoff_count"] == 0
    assert body["supported_handoff_members"] == []
    assert body["accepted_candidate_pool_revision_id"] is None
