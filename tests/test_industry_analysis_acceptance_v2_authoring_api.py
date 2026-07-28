from __future__ import annotations

from copy import deepcopy
from datetime import timedelta
from urllib.parse import urlencode
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.pool import StaticPool

import backend.api.industry_analysis_acceptance as acceptance_api
from backend.database.engine import build_session_factory
from backend.database.models import Base, StockBasicRecord
from backend.main import app
from industry_alpha.chain_map_models import IndustryMap, IndustryMapRevision
from industry_alpha.industry_thesis_commands import IndustryThesisCommandService
from industry_alpha.industry_thesis_models import (
    IndustryThesisOutputLinkRevision,
    IndustryThesisSessionRevision,
)
from industry_alpha.industry_thesis_review import (
    ACCEPTANCE_PLAN_VERSION,
    IndustryThesisProposalReviewService,
)
from industry_alpha.industry_thesis_rules import BUILDER_VERSION
from industry_alpha.stage1_fixtures import build_stage1_beneficiary_fixture
from industry_alpha.stage1_models import (
    Stage1Beneficiary,
    Stage1BeneficiaryRevision,
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


def _counts(database) -> tuple[int, int, int, int, int]:
    with database() as session:
        return (
            session.scalar(select(func.count()).select_from(Stage1Beneficiary)),
            session.scalar(select(func.count()).select_from(Stage1BeneficiaryRevision)),
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


def _authoring_fields(member: dict, *, status: str, rationale: str) -> dict:
    contract = member["stage1_authoring_contract"]
    assertion = contract["map_assertion_options"][0]
    claim = contract["claim_revision_options"][0]
    return {
        "legacy_beneficiary_kind": "direct",
        "assessment_status": status,
        "rationale_summary": rationale,
        "map_assertion_revisions": [
            {
                "assertion_kind": assertion["assertion_kind"],
                "assertion_revision_id": assertion["assertion_revision_id"],
            }
        ],
        "claim_revision_ids": [claim["claim_revision_id"]],
    }


def _payload(view: dict, binding: dict, *, supported: bool) -> dict:
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
        "acceptance_view_snapshot_contract_version": view[
            "acceptance_view_snapshot_contract_version"
        ],
        "acceptance_view_snapshot_content_sha256": view[
            "acceptance_view_snapshot_content_sha256"
        ],
        "research_case_id": view["owner_context"]["research_case_id"],
        "map_mode": view["owner_context"]["map_mode"],
        "industry_map_id": view["owner_context"]["industry_map_id"],
        "industry_map_revision_id": view["owner_context"][
            "industry_map_revision_id"
        ],
        "candidate_owner_bindings": [binding],
        "candidate_pool_operation": pool,
        "output_title": defaults["output_title"],
        "output_scope": defaults["output_scope"],
        "information_cutoff_date": view["information_cutoff_date"],
        "revision_note": "普通用户显式作者化 Stage 1 后接受研究成果。",
        "owner_acceptance_plan_version": view[
            "owner_acceptance_plan_version"
        ],
    }


def _accepted_result(client: TestClient, review: dict, committed: dict) -> dict:
    query = _query(
        review["acceptance_plan"]["session_id"],
        recorded_at=committed["recorded_at_utc"],
    )
    response = client.get(
        f"/industry-analysis/api/session-revisions/"
        f"{committed['accepted_session_revision_id']}/accepted-result-view?{query}"
    )
    assert response.status_code == 200, response.text
    return response.json()


def _commit(client: TestClient, review: dict, query: str, payload: dict) -> dict:
    reviewed_id = review["reviewed_session_revision_id"]
    preview = client.post(
        f"/industry-analysis/api/session-revisions/{reviewed_id}/"
        f"owner-acceptance/preview?{query}",
        json=payload,
    )
    assert preview.status_code == 200, preview.text
    preview_body = preview.json()
    assert preview_body["commit_ready"] is True
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
    return commit.json()


def _build_create_review(database) -> tuple[dict, int]:
    fixture = build_stage1_beneficiary_fixture(database)
    with database.begin() as session:
        reference_beneficiary = session.get(
            Stage1Beneficiary,
            fixture.direct_beneficiary_id,
        )
        reference_revision = session.scalar(
            select(Stage1BeneficiaryRevision)
            .where(
                Stage1BeneficiaryRevision.beneficiary_id
                == fixture.direct_beneficiary_id
            )
            .order_by(Stage1BeneficiaryRevision.revision_no.desc())
        )
        reference_stock = session.get(
            StockBasicRecord,
            reference_revision.stock_basic_record_id,
        )
        industry_map = session.get(IndustryMap, reference_beneficiary.map_id)
        map_revision = session.scalar(
            select(IndustryMapRevision)
            .where(IndustryMapRevision.map_id == industry_map.id)
            .order_by(IndustryMapRevision.revision_no.desc())
        )
        stock = StockBasicRecord(
            ingestion_run_id=reference_stock.ingestion_run_id,
            stock_code="909090",
            stock_name="Explicit Create Fixture Co",
            exchange="SZSE",
            industry="Fixture explicit authoring",
            listing_date=reference_stock.listing_date,
            status="listed",
            source=reference_stock.source,
        )
        session.add(stock)
        session.flush()
        stock_id = stock.id
        stock_name = stock.stock_name
        map_revision_id = map_revision.id

    created = IndustryThesisCommandService(
        database,
        clock=lambda: owner_fixture.BASE_TIME,
    ).create_session(owner_fixture._session_input())
    built = IndustryThesisCommandService(
        database,
        clock=lambda: owner_fixture.BASE_TIME + timedelta(seconds=1),
    ).build_candidates(
        {
            "session_revision_id": created["session_revision_id"],
            "expected_session_latest_revision_number": 1,
            "builder_version": BUILDER_VERSION,
            "allowed_source_kinds": ["accepted_local_mapping"],
            "proposals": [
                {
                    "source_kind": "accepted_local_mapping",
                    "source_reference": {"fixture_binding": "explicit-create"},
                    "proposed_stock_basic_record_id": stock_id,
                    "company_label_original": stock_name,
                    "product_or_service_fit": "Explicit create fixture fit.",
                    "industry_position": "Explicit create fixture position.",
                    "benefit_path_text": "Explicit create fixture benefit path.",
                    "proposed_exposure_type": "direct",
                    "proposal_confidence": "medium",
                    "identity_state": "exact_accepted_identity",
                    "review_state": "proposed",
                    "rationale": {"reason": "new exact stock identity"},
                    "uncertainty": {"state": "review_required"},
                }
            ],
        }
    )
    reviewed = IndustryThesisProposalReviewService(
        database,
        clock=lambda: owner_fixture.BASE_TIME + timedelta(seconds=2),
    ).review_candidates(
        {
            "session_revision_id": created["session_revision_id"],
            "expected_session_latest_revision_number": 1,
            "acceptance_plan_version": ACCEPTANCE_PLAN_VERSION,
            "owner_context": {
                "industry_map_revision_id": str(map_revision_id),
            },
            "decisions": [
                {
                    "candidate_revision_id": built["candidates"][0][
                        "candidate_revision_id"
                    ],
                    "expected_latest_revision_number": 1,
                    "decision": "selected_for_acceptance",
                    "final_proposed_exposure_type": "direct",
                    "rationale": {"reason": "explicitly reviewed create fixture"},
                    "uncertainty": {"state": "reviewed_local_scope"},
                }
            ],
            "revision_note": "selected explicit create fixture",
        }
    )
    return reviewed, stock_id


def test_explicit_append_preview_is_zero_write_and_commit_appends_revision(
    database,
    client,
) -> None:
    fixture = build_stage1_beneficiary_fixture(database)
    review, _industry_map, _map_revision, _rows = owner_fixture._build_reviewed(
        database,
        beneficiary_ids=(fixture.direct_beneficiary_id,),
    )
    query, view = _view(client, review)
    member = view["members"][0]
    target = max(
        member["stage1_append_options"],
        key=lambda item: item["revision_number"],
    )
    binding = {
        "reviewed_candidate_revision_id": member[
            "reviewed_candidate_revision_id"
        ],
        "sequence": member["sequence"],
        "stage1_operation": "append_beneficiary_revision",
        "stage1": {
            "beneficiary_id": target["beneficiary_id"],
            "expected_latest_revision_id": target[
                "expected_latest_revision_id"
            ],
            "stock_basic_record_id": target["stock_basic_record_id"],
            "source": target["source"],
            "stock_code": target["stock_code"],
            **_authoring_fields(
                member,
                status="supported",
                rationale="普通用户显式追加新的 supported Stage 1 修订。",
            ),
        },
        "semantic_operation": "none",
        "semantic": None,
        "readiness_note": "显式追加；类型化语义待后续处理。",
    }
    payload = _payload(view, binding, supported=True)
    before = _counts(database)

    reviewed_id = review["reviewed_session_revision_id"]
    preview = client.post(
        f"/industry-analysis/api/session-revisions/{reviewed_id}/"
        f"owner-acceptance/preview?{query}",
        json=payload,
    )
    assert preview.status_code == 200, preview.text
    assert preview.json()["commit_ready"] is True
    assert _counts(database) == before

    committed = _commit(client, review, query, payload)
    after = _counts(database)
    assert after[0] == before[0]
    assert after[1] == before[1] + 1
    body = _accepted_result(client, review, committed)
    assert body["complete_member_count"] == 1
    assert body["supported_handoff_count"] == 1
    assert body["members"][0]["beneficiary_id"] == target["beneficiary_id"]
    assert body["members"][0]["beneficiary_revision_id"] != target[
        "expected_latest_revision_id"
    ]
    assert body["members"][0]["assessment_status"] == "supported"


def test_explicit_create_preview_is_zero_write_and_commit_creates_identity(
    database,
    client,
) -> None:
    review, stock_id = _build_create_review(database)
    query, view = _view(client, review)
    member = view["members"][0]
    contract = member["stage1_create_contract"]
    assert member["stage1_reuse_options"] == []
    assert member["stage1_append_options"] == []
    assert contract["available"] is True
    assert contract["stock_basic_record_id"] == stock_id

    binding = {
        "reviewed_candidate_revision_id": member[
            "reviewed_candidate_revision_id"
        ],
        "sequence": member["sequence"],
        "stage1_operation": "create_beneficiary_identity_and_revision",
        "stage1": {
            "stock_basic_record_id": contract["stock_basic_record_id"],
            "source": contract["source"],
            "stock_code": contract["stock_code"],
            **_authoring_fields(
                member,
                status="supported",
                rationale="普通用户显式创建新的 supported Stage 1 身份。",
            ),
        },
        "semantic_operation": "none",
        "semantic": None,
        "readiness_note": "显式创建；类型化语义待后续处理。",
    }
    payload = _payload(view, binding, supported=True)
    before = _counts(database)

    reviewed_id = review["reviewed_session_revision_id"]
    preview = client.post(
        f"/industry-analysis/api/session-revisions/{reviewed_id}/"
        f"owner-acceptance/preview?{query}",
        json=payload,
    )
    assert preview.status_code == 200, preview.text
    assert preview.json()["commit_ready"] is True
    assert _counts(database) == before

    committed = _commit(client, review, query, payload)
    after = _counts(database)
    assert after[0] == before[0] + 1
    assert after[1] == before[1] + 1
    body = _accepted_result(client, review, committed)
    assert body["complete_member_count"] == 1
    assert body["supported_handoff_count"] == 1
    assert body["members"][0]["stock_basic_record_id"] == stock_id
    assert body["members"][0]["assessment_status"] == "supported"


def test_forged_create_authoring_material_is_blocked_without_writes(
    database,
    client,
) -> None:
    review, _stock_id = _build_create_review(database)
    query, view = _view(client, review)
    member = view["members"][0]
    contract = member["stage1_create_contract"]
    binding = {
        "reviewed_candidate_revision_id": member[
            "reviewed_candidate_revision_id"
        ],
        "sequence": member["sequence"],
        "stage1_operation": "create_beneficiary_identity_and_revision",
        "stage1": {
            "stock_basic_record_id": contract["stock_basic_record_id"],
            "source": contract["source"],
            "stock_code": contract["stock_code"],
            **_authoring_fields(
                member,
                status="draft",
                rationale="伪造材料必须失败。",
            ),
        },
        "semantic_operation": "none",
        "semantic": None,
        "readiness_note": "必须失败。",
    }
    binding["stage1"]["map_assertion_revisions"][0][
        "assertion_revision_id"
    ] = str(uuid4())
    payload = _payload(view, binding, supported=False)
    before = _counts(database)
    reviewed_id = review["reviewed_session_revision_id"]

    response = client.post(
        f"/industry-analysis/api/session-revisions/{reviewed_id}/"
        f"owner-acceptance/preview?{query}",
        json=deepcopy(payload),
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["commit_ready"] is False
    assert body["blocked_reasons"]
    assert _counts(database) == before
