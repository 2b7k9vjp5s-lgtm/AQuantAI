from __future__ import annotations

import inspect
from datetime import timedelta
from uuid import UUID, uuid4

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.pool import StaticPool

from backend.database.engine import build_session_factory
from backend.database.models import Base
from industry_alpha.chain_map_models import IndustryMap, IndustryMapRevision
from industry_alpha.industry_thesis_models import IndustryThesisSessionRevision
from industry_alpha.industry_thesis_owner_acceptance_contracts import (
    IndustryThesisOwnerAcceptanceError,
)
from industry_alpha.industry_thesis_owner_acceptance_workbench import (
    IndustryThesisOwnerAcceptanceWorkbenchQueryService,
)
from industry_alpha.industry_thesis_review import (
    HISTORICAL_ACCEPTANCE_PLAN_VERSION,
)
from industry_alpha.models import ResearchCase
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


def _reviewed_three_company_fixture(database):
    fixture = build_stage1_beneficiary_fixture(database)
    review, industry_map, map_revision, owner_rows = owner_fixture._build_reviewed(
        database,
        beneficiary_ids=(
            fixture.direct_beneficiary_id,
            fixture.secondary_beneficiary_id,
            fixture.draft_beneficiary_id,
        ),
    )
    return review, industry_map, map_revision, owner_rows


def _read_counts(database) -> tuple[int, int, int]:
    with database() as session:
        return (
            session.scalar(
                select(func.count()).select_from(IndustryThesisSessionRevision)
            ),
            session.scalar(select(func.count()).select_from(Stage1BeneficiaryRevision)),
            session.scalar(
                select(func.count()).select_from(Stage1CandidatePoolRevision)
            ),
        )


def _insert_other_context_for_same_stock(database, stock_id: int) -> tuple:
    recorded = owner_fixture.BASE_TIME + timedelta(microseconds=1)
    with database.begin() as session:
        research_case = ResearchCase(
            case_key=f"other-context-{uuid4()}",
            created_at_utc=owner_fixture.BASE_TIME - timedelta(days=1),
            origin="fixture",
        )
        session.add(research_case)
        session.flush()
        industry_map = IndustryMap(
            case_id=research_case.id,
            map_key=f"other-map-{uuid4()}",
            created_at_utc=owner_fixture.BASE_TIME - timedelta(hours=1),
        )
        session.add(industry_map)
        session.flush()
        map_revision = IndustryMapRevision(
            map_id=industry_map.id,
            revision_no=1,
            title="Other same-stock context",
            scope="Must never be inferred by the Owner Context v2 workbench.",
            information_cutoff_date=owner_fixture.CUTOFF,
            recorded_at_utc=recorded,
            supersedes_revision_id=None,
        )
        session.add(map_revision)
        session.flush()
        beneficiary = Stage1Beneficiary(
            case_id=research_case.id,
            map_id=industry_map.id,
            source="other-context",
            stock_code="000001",
            created_at_utc=recorded,
        )
        session.add(beneficiary)
        session.flush()
        revision = Stage1BeneficiaryRevision(
            beneficiary_id=beneficiary.id,
            revision_no=1,
            selected_map_revision_id=map_revision.id,
            stock_basic_record_id=stock_id,
            beneficiary_kind="direct",
            assessment_status="supported",
            rationale_summary="Same stock, deliberately different Owner Context.",
            information_cutoff_date=owner_fixture.CUTOFF,
            recorded_at_utc=recorded,
            supersedes_revision_id=None,
        )
        session.add(revision)
        session.flush()
        return research_case.id, industry_map.id, map_revision.id, beneficiary.id, revision.id


def test_workbench_uses_reviewed_context_and_excludes_same_stock_elsewhere(database) -> None:
    review, industry_map, map_revision, owner_rows = _reviewed_three_company_fixture(
        database
    )
    direct_stock_id = owner_rows[0][1].stock_basic_record_id
    other = _insert_other_context_for_same_stock(database, direct_stock_id)
    counts_before = _read_counts(database)

    with database() as session:
        view = IndustryThesisOwnerAcceptanceWorkbenchQueryService(
            session
        ).get_acceptance_view(
            session_id=UUID(review["acceptance_plan"]["session_id"]),
            reviewed_session_revision_id=UUID(review["reviewed_session_revision_id"]),
            as_of_cutoff=owner_fixture.CUTOFF,
            as_of_recorded_at_utc=owner_fixture.BASE_TIME + timedelta(seconds=3),
        )

    assert len(view["members"]) == 3
    assert view["owner_context"] == {
        "owner_context_contract_version": "aquantai.industry-thesis-owner-context.v1",
        "map_mode": "reuse_exact_existing_map_revision",
        "research_case_id": str(industry_map.case_id),
        "industry_map_id": str(industry_map.id),
        "industry_map_revision_id": str(map_revision.id),
    }
    assert view["technical_details"]["selected_context"] == {
        "research_case_id": str(industry_map.case_id),
        "industry_map_id": str(industry_map.id),
        "industry_map_revision_id": str(map_revision.id),
    }
    assert view["candidate_pool_operation_contract"]["zero_supported_contract"] == {
        "mode": "none_no_supported_members"
    }

    option_beneficiary_ids = {
        option["beneficiary_id"]
        for member in view["members"]
        for option in member["stage1_reuse_options"]
    }
    option_revision_ids = {
        option["beneficiary_revision_id"]
        for member in view["members"]
        for option in member["stage1_reuse_options"]
    }
    assert str(other[3]) not in option_beneficiary_ids
    assert str(other[4]) not in option_revision_ids
    assert {str(row[0].id) for row in owner_rows}.issubset(option_beneficiary_ids)

    material_counts = view["technical_details"]["authoring_material_counts"]
    assert material_counts["map_assertions"] >= 3
    assert material_counts["claim_revisions"] >= 3
    for member in view["members"]:
        contract = member["stage1_authoring_contract"]
        assert contract["map_assertion_options"]
        assert contract["claim_revision_options"]
        assert {item["value"] for item in contract["legacy_beneficiary_kind_options"]} == {
            "direct",
            "secondary",
            "potential",
        }
        assert {item["value"] for item in contract["assessment_status_options"]} == {
            "draft",
            "supported",
            "disputed",
        }
        assert all(
            option["assertion_kind"] in {"node", "relationship", "observation"}
            for option in contract["map_assertion_options"]
        )
        assert all(
            option["claim_status"] != "rejected"
            for option in contract["claim_revision_options"]
        )
    assert _read_counts(database) == counts_before


def test_workbench_has_no_context_substitution_parameters() -> None:
    signature = inspect.signature(
        IndustryThesisOwnerAcceptanceWorkbenchQueryService.get_acceptance_view
    )
    assert "research_case_id" not in signature.parameters
    assert "industry_map_id" not in signature.parameters
    assert "industry_map_revision_id" not in signature.parameters
    assert "map_mode" not in signature.parameters


def test_unaccepted_v1_fails_closed_even_when_one_stock_context_is_reachable(
    database,
    monkeypatch,
) -> None:
    review, _industry_map, _map_revision, _owner_rows = _reviewed_three_company_fixture(
        database
    )
    counts_before = _read_counts(database)

    class FakeLegacyReviewedPlanQueryService:
        def __init__(self, _session):
            pass

        def get_reviewed_plan(self, *_args, **_kwargs):
            return {
                "session_id": review["acceptance_plan"]["session_id"],
                "acceptance_plan_version": HISTORICAL_ACCEPTANCE_PLAN_VERSION,
                "owner_context": None,
                "acceptance_capability": {
                    "state": "legacy_owner_context_missing",
                    "reason_code": "industry_thesis_owner_context_required",
                },
                "acceptance_plan": review["acceptance_plan"],
                "acceptance_plan_fingerprint_sha256": review[
                    "acceptance_plan_fingerprint_sha256"
                ],
            }

    monkeypatch.setattr(
        "industry_alpha.industry_thesis_owner_acceptance_workbench."
        "IndustryThesisReviewedPlanQueryService",
        FakeLegacyReviewedPlanQueryService,
    )
    with database() as session:
        with pytest.raises(IndustryThesisOwnerAcceptanceError) as exc:
            IndustryThesisOwnerAcceptanceWorkbenchQueryService(
                session
            ).get_acceptance_view(
                session_id=UUID(review["acceptance_plan"]["session_id"]),
                reviewed_session_revision_id=UUID(
                    review["reviewed_session_revision_id"]
                ),
                as_of_cutoff=owner_fixture.CUTOFF,
                as_of_recorded_at_utc=owner_fixture.BASE_TIME
                + timedelta(seconds=3),
            )
    assert exc.value.code == "INDUSTRY_THESIS_ACCEPTANCE_REVIEWED_PLAN_NOT_READY"
    assert _read_counts(database) == counts_before
