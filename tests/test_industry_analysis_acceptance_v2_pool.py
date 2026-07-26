from __future__ import annotations

from datetime import timedelta
from urllib.parse import urlencode
from uuid import UUID

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
from industry_alpha.stage1_models import (
    Stage1CandidatePoolMembership,
    Stage1CandidatePoolRevision,
)
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
    recorded_value = boundary if isinstance(boundary, str) else boundary.isoformat()
    return urlencode(
        {
            "session_id": session_id,
            "as_of_cutoff": owner_fixture.CUTOFF.isoformat(),
            "as_of_recorded_at_utc": recorded_value,
        }
    )


def _view(client: TestClient, review: dict) -> tuple[str, dict]:
    session_id = review["acceptance_plan"]["session_id"]
    reviewed_id = review["reviewed_session_revision_id"]
    query = _query(session_id)
    response = client.get(
        f"/industry-analysis/api/session-revisions/{reviewed_id}/"
        f"owner-acceptance-view?{query}"
    )
    assert response.status_code == 200, response.text
    return query, response.json()


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


def _pool_target(database, candidate_pool_id: UUID) -> tuple[dict, set[str]]:
    with database() as session:
        revision = session.scalar(
            select(Stage1CandidatePoolRevision)
            .where(Stage1CandidatePoolRevision.candidate_pool_id == candidate_pool_id)
            .order_by(Stage1CandidatePoolRevision.revision_no.desc())
        )
        assert revision is not None
        membership_ids = {
            str(value)
            for value in session.scalars(
                select(Stage1CandidatePoolMembership.beneficiary_revision_id).where(
                    Stage1CandidatePoolMembership.candidate_pool_revision_id
                    == revision.id
                )
            )
        }
        return (
            {
                "mode": "reuse_exact_supported_handoff",
                "candidate_pool_id": str(candidate_pool_id),
                "candidate_pool_revision_id": str(revision.id),
            },
            membership_ids,
        )


def _payload(
    view: dict,
    *,
    selected_revision_ids: set[str] | None,
    pool_operation: dict,
) -> dict:
    bindings = []
    for member in view["members"]:
        options = member["stage1_reuse_options"]
        assert options
        if selected_revision_ids is None:
            option = max(options, key=lambda item: item["revision_number"])
        else:
            matches = [
                item
                for item in options
                if item["beneficiary_revision_id"] in selected_revision_ids
            ]
            assert len(matches) == 1
            option = matches[0]
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
                "readiness_note": "普通用户明确复用精确 Stage 1 版本和候选池。",
            }
        )
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
        "candidate_pool_operation": pool_operation,
        "output_title": defaults["output_title"],
        "output_scope": defaults["output_scope"],
        "information_cutoff_date": view["information_cutoff_date"],
        "revision_note": "普通用户确认精确候选池冻结成员并接受成果。",
        "owner_acceptance_plan_version": view[
            "owner_acceptance_plan_version"
        ],
    }


def _review(database, fixture):
    return owner_fixture._build_reviewed(
        database,
        beneficiary_ids=(
            fixture.direct_beneficiary_id,
            fixture.secondary_beneficiary_id,
        ),
    )[0]


def test_view_projects_exact_sorted_candidate_pool_memberships(database, client) -> None:
    fixture = build_stage1_beneficiary_fixture(database)
    review = _review(database, fixture)
    _query_value, view = _view(client, review)
    pool_operation, membership_ids = _pool_target(
        database,
        fixture.candidate_pool_id,
    )
    matches = [
        item
        for item in view["candidate_pool_operation_contract"]["reuse_options"]
        if item["candidate_pool_id"] == pool_operation["candidate_pool_id"]
        and item["candidate_pool_revision_id"]
        == pool_operation["candidate_pool_revision_id"]
    ]
    assert len(matches) == 1
    assert matches[0]["beneficiary_revision_ids"] == sorted(membership_ids)


def test_exact_pool_reuse_preview_is_zero_write_and_commit_reuses_revision(
    database,
    client,
) -> None:
    fixture = build_stage1_beneficiary_fixture(database)
    review = _review(database, fixture)
    query, view = _view(client, review)
    pool_operation, membership_ids = _pool_target(
        database,
        fixture.candidate_pool_id,
    )
    payload = _payload(
        view,
        selected_revision_ids=membership_ids,
        pool_operation=pool_operation,
    )
    before = _counts(database)
    reviewed_id = review["reviewed_session_revision_id"]

    preview = client.post(
        f"/industry-analysis/api/session-revisions/{reviewed_id}/"
        f"owner-acceptance/preview?{query}",
        json=payload,
    )
    assert preview.status_code == 200, preview.text
    preview_body = preview.json()
    assert preview_body["commit_ready"] is True
    assert preview_body["candidate_pool_mode"] == (
        "reuse_exact_supported_handoff"
    )
    assert _counts(database) == before

    committed = client.post(
        f"/industry-analysis/api/session-revisions/{reviewed_id}/"
        f"owner-acceptance/commit?{query}",
        json={
            **payload,
            "preview_fingerprint_sha256": preview_body[
                "preview_fingerprint_sha256"
            ],
        },
    )
    assert committed.status_code == 200, committed.text
    body = committed.json()
    assert body["candidate_pool_mode"] == "reuse_exact_supported_handoff"
    assert body["accepted_candidate_pool_revision_id"] == pool_operation[
        "candidate_pool_revision_id"
    ]
    after = _counts(database)
    assert after[0] == before[0] + 1
    assert after[1] == before[1] + 1
    assert after[2] == before[2]


def test_pool_reuse_with_latest_but_different_revision_set_is_zero_write_blocked(
    database,
    client,
) -> None:
    fixture = build_stage1_beneficiary_fixture(database)
    review = _review(database, fixture)
    query, view = _view(client, review)
    pool_operation, membership_ids = _pool_target(
        database,
        fixture.candidate_pool_id,
    )
    payload = _payload(
        view,
        selected_revision_ids=None,
        pool_operation=pool_operation,
    )
    submitted_ids = {
        item["stage1"]["beneficiary_revision_id"]
        for item in payload["candidate_owner_bindings"]
    }
    assert submitted_ids != membership_ids
    before = _counts(database)
    reviewed_id = review["reviewed_session_revision_id"]

    preview = client.post(
        f"/industry-analysis/api/session-revisions/{reviewed_id}/"
        f"owner-acceptance/preview?{query}",
        json=payload,
    )
    assert preview.status_code == 200, preview.text
    body = preview.json()
    assert body["commit_ready"] is False
    assert body["preview_fingerprint_sha256"] is None
    assert body["blocked_reasons"][0]["code"] == (
        "INDUSTRY_THESIS_ACCEPTANCE_SUPPORTED_HANDOFF_MISMATCH"
    )
    assert _counts(database) == before
