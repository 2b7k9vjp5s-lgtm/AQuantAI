from __future__ import annotations

from datetime import timedelta
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.pool import StaticPool

import backend.api.industry_research_result as result_api
from backend.database.engine import build_session_factory
from backend.database.models import Base
from backend.main import app
from industry_alpha.chain_map_models import IndustryMapRevision
from industry_alpha.industry_research_result_query import (
    IndustryResearchResultQueryService,
)
from industry_alpha.investment_candidate_commands import (
    InvestmentCandidateCommandService,
)
from industry_alpha.investment_candidate_models import (
    InvestmentCandidateSnapshotRevision,
)
from industry_alpha.investment_candidate_rules import PURPOSE_CODE, RULE_VERSION
from industry_alpha.stage1_models import (
    Stage1CandidatePool,
    Stage1CandidatePoolMembership,
    Stage1CandidatePoolRevision,
)
from scripts.demo_industry_research_result_assembly import (
    BASE_TIME,
    CUTOFF,
    seed_industry_research_result_demo,
)


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
        result_api.get_industry_analysis_session_factory
    ] = lambda: database
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


def _row_counts(database) -> tuple[int, int, int]:
    from industry_alpha.industry_thesis_models import IndustryThesisOutputLinkRevision

    with database() as session:
        return (
            session.scalar(
                select(func.count()).select_from(IndustryThesisOutputLinkRevision)
            ),
            session.scalar(
                select(func.count()).select_from(InvestmentCandidateSnapshotRevision)
            ),
            session.scalar(select(func.count()).select_from(IndustryMapRevision)),
        )


def _add_newer_map_revision(database, exact_revision_id: UUID) -> UUID:
    with database.begin() as session:
        exact = session.get(IndustryMapRevision, exact_revision_id)
        newer = IndustryMapRevision(
            map_id=exact.map_id,
            revision_no=exact.revision_no + 1,
            title="不应被 accepted 结果自动选择的新版本",
            scope="Later visible revision that proves exact-ID selection.",
            information_cutoff_date=CUTOFF,
            recorded_at_utc=BASE_TIME + timedelta(seconds=7),
            supersedes_revision_id=exact.id,
        )
        session.add(newer)
        session.flush()
        return newer.id


def _other_pool_snapshot(database, seeded: dict) -> str:
    with database.begin() as session:
        accepted_revision = session.get(
            Stage1CandidatePoolRevision,
            UUID(seeded["candidate_pool_revision_id"]),
        )
        accepted_pool = session.get(
            Stage1CandidatePool,
            accepted_revision.candidate_pool_id,
        )
        accepted_members = list(
            session.scalars(
                select(Stage1CandidatePoolMembership)
                .where(
                    Stage1CandidatePoolMembership.candidate_pool_revision_id
                    == accepted_revision.id
                )
                .order_by(Stage1CandidatePoolMembership.id)
            )
        )
        other_pool = Stage1CandidatePool(
            case_id=accepted_pool.case_id,
            map_id=accepted_pool.map_id,
            pool_key="result-assembly-mismatch-pool",
            created_at_utc=BASE_TIME + timedelta(seconds=7),
        )
        session.add(other_pool)
        session.flush()
        other_revision = Stage1CandidatePoolRevision(
            candidate_pool_id=other_pool.id,
            revision_no=1,
            selected_map_revision_id=accepted_revision.selected_map_revision_id,
            title="Different exact pool",
            scope="Used only for exact-pool mismatch validation.",
            information_cutoff_date=CUTOFF,
            recorded_at_utc=BASE_TIME + timedelta(seconds=7),
            supersedes_revision_id=None,
        )
        session.add(other_revision)
        session.flush()
        manifest = []
        for source in accepted_members:
            membership = Stage1CandidatePoolMembership(
                candidate_pool_revision_id=other_revision.id,
                beneficiary_id=source.beneficiary_id,
                beneficiary_revision_id=source.beneficiary_revision_id,
                recorded_at_utc=BASE_TIME + timedelta(seconds=7),
            )
            session.add(membership)
            session.flush()
            manifest.append(
                {
                    "candidate_pool_membership_id": str(membership.id),
                    "beneficiary_id": str(membership.beneficiary_id),
                    "beneficiary_revision_id": str(
                        membership.beneficiary_revision_id
                    ),
                    "company_research_revision_id": None,
                    "typed_beneficiary_revision_id": None,
                    "canonical_price_revision_id": None,
                    "comparison_eligibility_revision_id": None,
                    "component_revision_ids": {},
                }
            )
        other_pool_id = other_pool.id
        other_revision_id = other_revision.id
    result = InvestmentCandidateCommandService(database).record_snapshot(
        {
            "candidate_pool_id": str(other_pool_id),
            "candidate_pool_revision_id": str(other_revision_id),
            "purpose_code": PURPOSE_CODE,
            "rule_version": RULE_VERSION,
            "snapshot_key": "result-assembly-mismatch-snapshot",
            "expected_latest_revision_id": None,
            "information_cutoff_date": CUTOFF.isoformat(),
            "recorded_at_utc": (BASE_TIME + timedelta(seconds=8)).isoformat(),
            "recorded_by": "test",
            "members": manifest,
        }
    )
    return result["snapshot_revision_id"]


def test_exact_map_and_candidate_options_require_explicit_selection(database) -> None:
    seeded = seed_industry_research_result_demo(database)
    exact_map_id = UUID(seeded["industry_map_revision_id"])
    newer_id = _add_newer_map_revision(database, exact_map_id)
    counts_before = _row_counts(database)
    with database() as session:
        result = IndustryResearchResultQueryService(session).get_assembled_result(
            UUID(seeded["output_link_revision_id"]),
            as_of_cutoff=CUTOFF,
            as_of_recorded_at_utc=BASE_TIME + timedelta(seconds=9),
        )
    assert _row_counts(database) == counts_before
    assert result["accepted_snapshot"]["complete_member_count"] == 3
    assert result["accepted_snapshot"]["supported_handoff_count"] == 2
    assert result["candidate_overlay"]["state"] == "not_selected"
    assert result["candidate_snapshot_options"]["auto_selected"] is False
    options = result["candidate_snapshot_options"]["options"]
    assert [item["revision_no"] for item in options] == [2, 1]
    assert result["industry_map"]["map_revision_id"] == str(exact_map_id)
    assert result["industry_map"]["map_revision_id"] != str(newer_id)
    assert result["industry_map"]["latest_fallback_used"] is False
    assert result["writes_performed"] is False


def test_one_visible_option_is_never_auto_selected(database) -> None:
    seeded = seed_industry_research_result_demo(database)
    with database() as session:
        result = IndustryResearchResultQueryService(session).get_assembled_result(
            UUID(seeded["output_link_revision_id"]),
            as_of_cutoff=CUTOFF,
            as_of_recorded_at_utc=BASE_TIME + timedelta(seconds=4),
        )
    assert len(result["candidate_snapshot_options"]["options"]) == 1
    assert result["candidate_snapshot_options"]["auto_selected"] is False
    assert result["candidate_overlay"]["state"] == "not_selected"


def test_selected_overlay_joins_only_exact_beneficiary_revisions(database) -> None:
    seeded = seed_industry_research_result_demo(database)
    counts_before = _row_counts(database)
    with database() as session:
        result = IndustryResearchResultQueryService(session).get_assembled_result(
            UUID(seeded["output_link_revision_id"]),
            as_of_cutoff=CUTOFF,
            as_of_recorded_at_utc=seeded["as_of_recorded_at_utc"],
            investment_candidate_snapshot_revision_id=UUID(
                seeded["second_snapshot_revision_id"]
            ),
        )
    assert _row_counts(database) == counts_before
    assert result["candidate_overlay"]["state"] == "selected"
    snapshot = result["candidate_overlay"]["snapshot"]
    assert snapshot["candidate_pool_revision_id"] == seeded[
        "candidate_pool_revision_id"
    ]
    assert snapshot["member_count"] == 2
    assert {item["candidate_status"] for item in snapshot["members"]} == {
        "evidence_insufficient"
    }
    complete = result["accepted_snapshot"]["members"]
    assert len(complete) == 3
    assert sum(item["candidate_overlay"] is not None for item in complete) == 2
    assert any(
        item["assessment_status"] != "supported"
        and item["candidate_overlay"] is None
        for item in complete
    )


def test_exact_pool_mismatch_blocks_only_optional_overlay(database) -> None:
    seeded = seed_industry_research_result_demo(database)
    mismatch_snapshot_id = _other_pool_snapshot(database, seeded)
    counts_before = _row_counts(database)
    with database() as session:
        result = IndustryResearchResultQueryService(session).get_assembled_result(
            UUID(seeded["output_link_revision_id"]),
            as_of_cutoff=CUTOFF,
            as_of_recorded_at_utc=BASE_TIME + timedelta(seconds=9),
            investment_candidate_snapshot_revision_id=UUID(mismatch_snapshot_id),
        )
    assert _row_counts(database) == counts_before
    assert result["accepted_snapshot"]["complete_member_count"] == 3
    assert result["candidate_overlay"] == {
        "state": "blocked_exact_pool_mismatch",
        "snapshot_revision_id": mismatch_snapshot_id,
        "snapshot": None,
        "blocked_reason": "exact_pool_mismatch",
    }


def test_zero_supported_result_has_no_candidate_overlay(database) -> None:
    seeded = seed_industry_research_result_demo(database, zero_supported=True)
    with database() as session:
        result = IndustryResearchResultQueryService(session).get_assembled_result(
            UUID(seeded["output_link_revision_id"]),
            as_of_cutoff=CUTOFF,
            as_of_recorded_at_utc=seeded["as_of_recorded_at_utc"],
        )
    assert result["accepted_snapshot"]["complete_member_count"] == 2
    assert result["accepted_snapshot"]["supported_handoff_count"] == 0
    assert result["candidate_snapshot_options"]["options"] == []
    assert result["candidate_overlay"]["state"] == (
        "unavailable_zero_supported"
    )


def test_api_exposes_exact_optional_selector_without_writes(database, client) -> None:
    seeded = seed_industry_research_result_demo(database)
    counts_before = _row_counts(database)
    response = client.get(
        "/industry-analysis/api/output-link-revisions/"
        f"{seeded['output_link_revision_id']}/assembled-result",
        params={
            "as_of_cutoff": CUTOFF.isoformat(),
            "as_of_recorded_at_utc": seeded[
                "as_of_recorded_at_utc"
            ].isoformat(),
            "investment_candidate_snapshot_revision_id": seeded[
                "second_snapshot_revision_id"
            ],
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["candidate_overlay"]["state"] == "selected"
    assert body["writes_performed"] is False
    assert _row_counts(database) == counts_before
