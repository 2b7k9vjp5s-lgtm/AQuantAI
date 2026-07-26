from __future__ import annotations

from copy import deepcopy
import inspect
import re
from datetime import date, datetime, timedelta, timezone
from uuid import UUID, uuid4

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.pool import StaticPool

from backend.database.canonical_price_models import ListedInstrument
from backend.database.engine import build_session_factory
from backend.database.models import Base, StockBasicRecord
from industry_alpha.chain_map_models import IndustryMap, IndustryMapRevision
from industry_alpha.industry_thesis_commands import IndustryThesisCommandService
from industry_alpha.industry_thesis_models import (
    IndustryThesisOutputLinkIdentity,
    IndustryThesisOutputLinkRevision,
    IndustryThesisSessionRevision,
)
from industry_alpha.industry_thesis_owner_acceptance import (
    IndustryThesisOwnerAcceptanceService,
)
from industry_alpha.industry_thesis_owner_acceptance_contracts import (
    OWNER_ACCEPTANCE_PLAN_VERSION,
    IndustryThesisOwnerAcceptanceError,
    normalize_owner_acceptance_plan,
)
from industry_alpha.industry_thesis_owner_acceptance_query import (
    IndustryThesisAcceptedOutputQueryService,
)
from industry_alpha.industry_thesis_review import (
    ACCEPTANCE_PLAN_VERSION,
    IndustryThesisProposalReviewService,
)
from industry_alpha.industry_thesis_rules import BUILDER_VERSION
from industry_alpha.stage1_fixtures import build_stage1_beneficiary_fixture
from industry_alpha.stage1_models import (
    Stage1Beneficiary,
    Stage1BeneficiaryAssertionLink,
    Stage1BeneficiaryClaimLink,
    Stage1BeneficiaryRevision,
    Stage1CandidatePool,
)
from industry_alpha.stage1_owner_port import Stage1OwnerWritePort
from industry_alpha.beneficiary_semantics_owner_port import (
    BeneficiarySemanticOwnerWritePort,
)

UTC = timezone.utc
CUTOFF = date(2026, 7, 9)
BASE_TIME = datetime(2026, 7, 10, 12, tzinfo=UTC)


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


def _session_input():
    return {
        "thesis_text_original": "合成材料需求扩张与工艺瓶颈",
        "thesis_title_reviewed": "合成材料产业研究",
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
        "chain_boundary": {"included": ["materials", "processing"]},
        "exclusions": [],
        "seed_companies": [],
        "seed_products": ["synthetic-material"],
        "seed_technologies": [],
        "seed_bottlenecks": ["purification"],
        "draft_graph": {"nodes": [], "relationships": []},
        "coverage_state": "partial_local_coverage",
        "workflow_state": "candidate_build_ready",
        "information_cutoff_date": CUTOFF.isoformat(),
        "revision_note": "offline owner-acceptance fixture",
    }


def _stage1_rows(database, beneficiary_ids: tuple[UUID, ...]):
    with database() as session:
        industry_map = session.get(
            IndustryMap,
            session.get(Stage1Beneficiary, beneficiary_ids[0]).map_id,
        )
        map_revision = session.scalar(
            select(IndustryMapRevision)
            .where(IndustryMapRevision.map_id == industry_map.id)
            .order_by(IndustryMapRevision.revision_no.desc())
        )
        rows = []
        for beneficiary_id in beneficiary_ids:
            beneficiary = session.get(Stage1Beneficiary, beneficiary_id)
            revision = session.scalar(
                select(Stage1BeneficiaryRevision)
                .where(Stage1BeneficiaryRevision.beneficiary_id == beneficiary.id)
                .order_by(Stage1BeneficiaryRevision.revision_no.desc())
            )
            stock = session.get(StockBasicRecord, revision.stock_basic_record_id)
            rows.append((beneficiary, revision, stock))
        return industry_map, map_revision, rows


def _build_reviewed(
    database,
    *,
    beneficiary_ids: tuple[UUID, ...],
) -> tuple[dict, IndustryMap, IndustryMapRevision, list[tuple]]:
    industry_map, map_revision, owner_rows = _stage1_rows(database, beneficiary_ids)
    commands = IndustryThesisCommandService(database, clock=lambda: BASE_TIME)
    created = commands.create_session(_session_input())
    proposals = []
    for index, (_beneficiary, revision, stock) in enumerate(owner_rows):
        proposals.append(
            {
                "source_kind": "accepted_local_mapping",
                "source_reference": {"fixture_binding": f"owner-{index}"},
                "proposed_stock_basic_record_id": revision.stock_basic_record_id,
                "company_label_original": stock.stock_name,
                "product_or_service_fit": "Synthetic fixture product fit.",
                "industry_position": "Synthetic fixture chain position.",
                "benefit_path_text": "Synthetic fixture evidence-backed benefit path.",
                "proposed_exposure_type": ("direct", "conditional", "indirect")[index % 3],
                "proposal_confidence": "medium",
                "identity_state": "exact_accepted_identity",
                "review_state": "proposed",
                "rationale": {"reason": "explicit local stock_basic identity"},
                "uncertainty": {"state": "review_required"},
            }
        )
    built = IndustryThesisCommandService(
        database,
        clock=lambda: BASE_TIME + timedelta(seconds=1),
    ).build_candidates(
        {
            "session_revision_id": created["session_revision_id"],
            "expected_session_latest_revision_number": 1,
            "builder_version": BUILDER_VERSION,
            "allowed_source_kinds": ["accepted_local_mapping"],
            "proposals": proposals,
        }
    )
    review = IndustryThesisProposalReviewService(
        database,
        clock=lambda: BASE_TIME + timedelta(seconds=2),
    ).review_candidates(
        {
            "session_revision_id": created["session_revision_id"],
            "expected_session_latest_revision_number": 1,
            "acceptance_plan_version": ACCEPTANCE_PLAN_VERSION,
            "owner_context": {
                "industry_map_revision_id": str(map_revision.id),
            },
            "decisions": [
                {
                    "candidate_revision_id": item["candidate_revision_id"],
                    "expected_latest_revision_number": 1,
                    "decision": "selected_for_acceptance",
                    "final_proposed_exposure_type": item["proposed_exposure_type"],
                    "rationale": {"reason": "explicit owner-acceptance fixture"},
                    "uncertainty": {"state": "reviewed_local_scope"},
                }
                for item in built["candidates"]
            ],
            "revision_note": "selected exact owner-bound candidates",
        }
    )
    return review, industry_map, map_revision, owner_rows


def _acceptance_input(
    review: dict,
    industry_map: IndustryMap,
    map_revision: IndustryMapRevision,
    owner_rows: list[tuple],
    *,
    pool_mode: str,
) -> dict:
    by_stock = {
        item["proposed_stock_basic_record_id"]: item["candidate_revision_id"]
        for item in review["acceptance_plan"]["selected_candidates"]
    }
    bindings = []
    for sequence, (beneficiary, revision, _stock) in enumerate(owner_rows):
        bindings.append(
            {
                "reviewed_candidate_revision_id": by_stock[
                    revision.stock_basic_record_id
                ],
                "sequence": sequence,
                "stage1_operation": "reuse_exact_beneficiary_revision",
                "stage1": {
                    "beneficiary_id": str(beneficiary.id),
                    "beneficiary_revision_id": str(revision.id),
                    "stock_basic_record_id": revision.stock_basic_record_id,
                },
                "semantic_operation": "none",
                "semantic": None,
                "readiness_note": "Fixture readiness remains explicit.",
            }
        )
    pool_operation = {"mode": "none_no_supported_members"}
    if pool_mode == "create_supported_handoff":
        pool_operation = {
            "mode": "create_supported_handoff",
            "pool_key": "thesis-owner-acceptance-supported",
            "title": "Accepted supported handoff",
            "scope": "Exact supported accepted members only.",
        }
    return {
        "reviewed_session_revision_id": review["reviewed_session_revision_id"],
        "expected_session_latest_revision_number": review[
            "reviewed_session_revision_number"
        ],
        "reviewed_plan_fingerprint_sha256": review[
            "acceptance_plan_fingerprint_sha256"
        ],
        "research_case_id": str(industry_map.case_id),
        "map_mode": "reuse_exact_existing_map_revision",
        "industry_map_id": str(industry_map.id),
        "industry_map_revision_id": str(map_revision.id),
        "candidate_owner_bindings": bindings,
        "candidate_pool_operation": pool_operation,
        "output_title": "Synthetic accepted result",
        "output_scope": "Only the exact reviewed local fixture members.",
        "information_cutoff_date": CUTOFF.isoformat(),
        "revision_note": "accept exact owner outputs",
        "owner_acceptance_plan_version": OWNER_ACCEPTANCE_PLAN_VERSION,
    }


def _counts(database) -> tuple[int, int, int, int]:
    with database() as session:
        return (
            session.scalar(
                select(func.count()).select_from(IndustryThesisSessionRevision)
            ),
            session.scalar(
                select(func.count()).select_from(IndustryThesisOutputLinkIdentity)
            ),
            session.scalar(
                select(func.count()).select_from(IndustryThesisOutputLinkRevision)
            ),
            session.scalar(select(func.count()).select_from(Stage1CandidatePool)),
        )


def test_three_member_golden_path_preview_commit_exact_reads_and_replay(database):
    fixture = build_stage1_beneficiary_fixture(database)
    review, industry_map, map_revision, rows = _build_reviewed(
        database,
        beneficiary_ids=(
            fixture.direct_beneficiary_id,
            fixture.draft_beneficiary_id,
            fixture.secondary_beneficiary_id,
        ),
    )
    raw = _acceptance_input(
        review,
        industry_map,
        map_revision,
        rows,
        pool_mode="create_supported_handoff",
    )
    before = _counts(database)
    service = IndustryThesisOwnerAcceptanceService(
        database,
        clock=lambda: BASE_TIME + timedelta(seconds=3),
    )
    preview = service.preview(raw)
    assert preview["commit_ready"] is True
    assert preview["complete_universe_count"] == 3
    assert preview["supported_handoff_count"] == 2
    assert preview["accepted_session_revision_id"] is None
    assert preview["output_link_revision_id"] is None
    assert _counts(database) == before

    committed = service.commit(
        {
            **raw,
            "preview_fingerprint_sha256": preview["preview_fingerprint_sha256"],
        }
    )
    assert committed["idempotent_replay"] is False
    assert committed["complete_universe_count"] == 3
    assert committed["supported_handoff_count"] == 2
    assert committed["accepted_candidate_pool_revision_id"] is not None

    replay = service.commit(
        {
            **raw,
            "preview_fingerprint_sha256": preview["preview_fingerprint_sha256"],
        }
    )
    assert replay["idempotent_replay"] is True
    assert replay["output_link_revision_id"] == committed["output_link_revision_id"]
    assert replay["accepted_session_revision_id"] == committed[
        "accepted_session_revision_id"
    ]

    read_boundary = BASE_TIME + timedelta(days=1)
    with database() as session:
        query = IndustryThesisAcceptedOutputQueryService(session)
        output = query.get_output(
            UUID(committed["output_link_revision_id"]),
            as_of_cutoff=CUTOFF,
            as_of_recorded_at_utc=read_boundary,
        )
        result = query.get_result(
            UUID(committed["output_link_revision_id"]),
            as_of_cutoff=CUTOFF,
            as_of_recorded_at_utc=read_boundary,
        )
        readiness = query.get_readiness(
            UUID(committed["output_link_revision_id"]),
            as_of_cutoff=CUTOFF,
            as_of_recorded_at_utc=read_boundary,
        )

    assert output["accepted_candidate_pool_revision_id"] == committed[
        "accepted_candidate_pool_revision_id"
    ]
    assert result["title"] == "本次研究已接受的完整成员"
    assert result["complete_member_count"] == 3
    assert result["supported_handoff_count"] == 2
    assert result["ranking_applied"] is False
    statuses = [item["assessment_status"] for item in result["members"]]
    assert statuses == ["supported", "draft", "supported"]
    assert all(item["typed_semantics"]["state"] == "missing" for item in readiness["items"])
    assert readiness["creates_owner_state"] is False
    assert readiness["computes_score"] is False


def test_zero_supported_result_keeps_complete_members_and_null_pool(database):
    fixture = build_stage1_beneficiary_fixture(database)
    review, industry_map, map_revision, rows = _build_reviewed(
        database,
        beneficiary_ids=(
            fixture.draft_beneficiary_id,
            fixture.disputed_beneficiary_id,
        ),
    )
    raw = _acceptance_input(
        review,
        industry_map,
        map_revision,
        rows,
        pool_mode="none_no_supported_members",
    )
    service = IndustryThesisOwnerAcceptanceService(
        database,
        clock=lambda: BASE_TIME + timedelta(seconds=3),
    )
    preview = service.preview(raw)
    assert preview["commit_ready"] is True
    assert preview["supported_handoff_count"] == 0
    committed = service.commit(
        {
            **raw,
            "preview_fingerprint_sha256": preview["preview_fingerprint_sha256"],
        }
    )
    assert committed["accepted_candidate_pool_revision_id"] is None
    with database() as session:
        output = IndustryThesisAcceptedOutputQueryService(session).get_result(
            UUID(committed["output_link_revision_id"]),
            as_of_cutoff=CUTOFF,
            as_of_recorded_at_utc=BASE_TIME + timedelta(days=1),
        )
    assert output["complete_member_count"] == 2
    assert output["supported_handoff_count"] == 0
    assert output["accepted_candidate_pool_revision_id"] is None
    assert [item["assessment_status"] for item in output["members"]] == [
        "draft",
        "disputed",
    ]


def test_listed_instrument_only_preview_blocks_before_any_owner_write(database):
    fixture = build_stage1_beneficiary_fixture(database)
    industry_map, map_revision, rows = _stage1_rows(
        database,
        (fixture.direct_beneficiary_id,),
    )
    with database.begin() as session:
        instrument = ListedInstrument(
            instrument_key="owner-acceptance-listed-only",
            created_at_utc=BASE_TIME,
        )
        session.add(instrument)
        session.flush()
        instrument_id = instrument.id
    created = IndustryThesisCommandService(
        database,
        clock=lambda: BASE_TIME,
    ).create_session(_session_input())
    built = IndustryThesisCommandService(
        database,
        clock=lambda: BASE_TIME + timedelta(seconds=1),
    ).build_candidates(
        {
            "session_revision_id": created["session_revision_id"],
            "expected_session_latest_revision_number": 1,
            "builder_version": BUILDER_VERSION,
            "allowed_source_kinds": ["accepted_local_mapping"],
            "proposals": [
                {
                    "source_kind": "accepted_local_mapping",
                    "source_reference": {"fixture_binding": "listed-only"},
                    "proposed_listed_instrument_id": str(instrument_id),
                    "company_label_original": "Listed Instrument Only",
                    "benefit_path_text": "No accepted stock_basic owner identity.",
                    "proposed_exposure_type": "direct",
                    "proposal_confidence": "medium",
                    "identity_state": "exact_accepted_identity",
                    "review_state": "proposed",
                    "rationale": {"reason": "listed instrument only"},
                    "uncertainty": {"state": "stock_basic_missing"},
                }
            ],
        }
    )
    reviewed = IndustryThesisProposalReviewService(
        database,
        clock=lambda: BASE_TIME + timedelta(seconds=2),
    ).review_candidates(
        {
            "session_revision_id": created["session_revision_id"],
            "expected_session_latest_revision_number": 1,
            "acceptance_plan_version": ACCEPTANCE_PLAN_VERSION,
            "owner_context": {
                "industry_map_revision_id": str(map_revision.id),
            },
            "decisions": [
                {
                    "candidate_revision_id": built["candidates"][0][
                        "candidate_revision_id"
                    ],
                    "expected_latest_revision_number": 1,
                    "decision": "selected_for_acceptance",
                    "final_proposed_exposure_type": "direct",
                    "rationale": {"reason": "explicitly reviewed"},
                    "uncertainty": {"state": "stock_basic_missing"},
                }
            ],
            "revision_note": "listed-only blocked fixture",
        }
    )
    beneficiary, revision, _stock = rows[0]
    raw = {
        "reviewed_session_revision_id": reviewed["reviewed_session_revision_id"],
        "expected_session_latest_revision_number": reviewed[
            "reviewed_session_revision_number"
        ],
        "reviewed_plan_fingerprint_sha256": reviewed[
            "acceptance_plan_fingerprint_sha256"
        ],
        "research_case_id": str(industry_map.case_id),
        "map_mode": "reuse_exact_existing_map_revision",
        "industry_map_id": str(industry_map.id),
        "industry_map_revision_id": str(map_revision.id),
        "candidate_owner_bindings": [
            {
                "reviewed_candidate_revision_id": reviewed["acceptance_plan"][
                    "selected_candidates"
                ][0]["candidate_revision_id"],
                "sequence": 0,
                "stage1_operation": "reuse_exact_beneficiary_revision",
                "stage1": {
                    "beneficiary_id": str(beneficiary.id),
                    "beneficiary_revision_id": str(revision.id),
                    "stock_basic_record_id": revision.stock_basic_record_id,
                },
                "semantic_operation": "none",
                "semantic": None,
                "readiness_note": "Blocked until stock_basic is explicit.",
            }
        ],
        "candidate_pool_operation": {
            "mode": "create_supported_handoff",
            "pool_key": "should-not-exist",
            "title": "Should not exist",
            "scope": "Blocked before writes.",
        },
        "output_title": "Blocked",
        "output_scope": "Blocked",
        "information_cutoff_date": CUTOFF.isoformat(),
        "revision_note": "blocked",
        "owner_acceptance_plan_version": OWNER_ACCEPTANCE_PLAN_VERSION,
    }
    before = _counts(database)
    preview = IndustryThesisOwnerAcceptanceService(
        database,
        clock=lambda: BASE_TIME + timedelta(seconds=3),
    ).preview(raw)
    assert preview["commit_ready"] is False
    assert preview["preview_fingerprint_sha256"] is None
    assert preview["blocked_reasons"][0]["code"] == (
        "INDUSTRY_THESIS_ACCEPTANCE_LISTED_INSTRUMENT_ONLY"
    )
    assert _counts(database) == before


def test_contract_rejects_unknown_nested_fields_and_rejected_stage1_status():
    base = {
        "reviewed_session_revision_id": str(uuid4()),
        "expected_session_latest_revision_number": 1,
        "reviewed_plan_fingerprint_sha256": "a" * 64,
        "research_case_id": str(uuid4()),
        "map_mode": "reuse_exact_existing_map_revision",
        "industry_map_id": str(uuid4()),
        "industry_map_revision_id": str(uuid4()),
        "candidate_owner_bindings": [
            {
                "reviewed_candidate_revision_id": str(uuid4()),
                "sequence": 0,
                "stage1_operation": "create_beneficiary_identity_and_revision",
                "stage1": {
                    "stock_basic_record_id": 1,
                    "source": "fixture",
                    "stock_code": "000001",
                    "legacy_beneficiary_kind": "direct",
                    "assessment_status": "draft",
                    "rationale_summary": "Explicit fixture rationale.",
                    "map_assertion_revisions": [
                        {
                            "assertion_kind": "node",
                            "assertion_revision_id": str(uuid4()),
                        }
                    ],
                    "claim_revision_ids": [str(uuid4())],
                },
                "semantic_operation": "none",
                "semantic": None,
                "readiness_note": "Explicit.",
            }
        ],
        "candidate_pool_operation": {"mode": "none_no_supported_members"},
        "output_title": "Fixture",
        "output_scope": "Fixture",
        "information_cutoff_date": "2026-07-09",
        "revision_note": "Fixture",
        "owner_acceptance_plan_version": OWNER_ACCEPTANCE_PLAN_VERSION,
    }
    unknown = deepcopy(base)
    unknown["candidate_owner_bindings"][0]["stage1"]["unexpected"] = True
    with pytest.raises(Exception) as caught:
        normalize_owner_acceptance_plan(unknown)
    assert getattr(caught.value, "code", None) == "industry_thesis_unknown_field"

    rejected = deepcopy(base)
    rejected["candidate_owner_bindings"][0]["stage1"][
        "assessment_status"
    ] = "rejected"
    with pytest.raises(IndustryThesisOwnerAcceptanceError) as caught:
        normalize_owner_acceptance_plan(rejected)
    assert caught.value.code == "INDUSTRY_THESIS_ACCEPTANCE_STATUS_REJECTED"


def test_owner_ports_never_open_commit_or_rollback_transactions():
    for port in (Stage1OwnerWritePort, BeneficiarySemanticOwnerWritePort):
        source = inspect.getsource(port)
        assert "session_factory.begin" not in source
        assert re.search(r"\.commit\s*\(", source) is None
        assert re.search(r"\.rollback\s*\(", source) is None


def test_late_pool_conflict_rolls_back_appended_stage1_and_thesis_rows(database):
    fixture = build_stage1_beneficiary_fixture(database)
    review, industry_map, map_revision, rows = _build_reviewed(
        database,
        beneficiary_ids=(fixture.direct_beneficiary_id,),
    )
    raw = _acceptance_input(
        review,
        industry_map,
        map_revision,
        rows,
        pool_mode="create_supported_handoff",
    )
    beneficiary, revision, _stock = rows[0]
    with database() as session:
        assertion_links = list(
            session.scalars(
                select(Stage1BeneficiaryAssertionLink).where(
                    Stage1BeneficiaryAssertionLink.beneficiary_revision_id
                    == revision.id
                )
            )
        )
        claim_ids = list(
            session.scalars(
                select(Stage1BeneficiaryClaimLink.claim_revision_id).where(
                    Stage1BeneficiaryClaimLink.beneficiary_revision_id
                    == revision.id
                )
            )
        )
        existing_pool = session.get(Stage1CandidatePool, fixture.candidate_pool_id)
        before_stage1 = session.scalar(
            select(func.count()).select_from(Stage1BeneficiaryRevision)
        )
    assertions = []
    for link in assertion_links:
        for kind in ("node", "relationship", "observation"):
            revision_id = getattr(link, f"{kind}_revision_id")
            if revision_id is not None:
                assertions.append(
                    {
                        "assertion_kind": kind,
                        "assertion_revision_id": str(revision_id),
                    }
                )
    raw["candidate_owner_bindings"][0]["stage1_operation"] = (
        "append_beneficiary_revision"
    )
    raw["candidate_owner_bindings"][0]["stage1"] = {
        "beneficiary_id": str(beneficiary.id),
        "expected_latest_revision_id": str(revision.id),
        "stock_basic_record_id": revision.stock_basic_record_id,
        "source": beneficiary.source,
        "stock_code": beneficiary.stock_code,
        "legacy_beneficiary_kind": revision.beneficiary_kind,
        "assessment_status": "supported",
        "rationale_summary": "This append must roll back after the later pool conflict.",
        "map_assertion_revisions": assertions,
        "claim_revision_ids": [str(value) for value in claim_ids],
    }
    raw["candidate_pool_operation"]["pool_key"] = existing_pool.pool_key
    normalized = normalize_owner_acceptance_plan(raw)
    before = _counts(database)
    with pytest.raises(IndustryThesisOwnerAcceptanceError) as caught:
        IndustryThesisOwnerAcceptanceService(
            database,
            clock=lambda: BASE_TIME + timedelta(seconds=3),
        ).commit(
            {
                **raw,
                "preview_fingerprint_sha256": normalized[
                    "owner_acceptance_plan_fingerprint_sha256"
                ],
            }
        )
    assert caught.value.code == "INDUSTRY_THESIS_ACCEPTANCE_OWNER_REVISION_CONFLICT"
    assert _counts(database) == before
    with database() as session:
        assert session.scalar(
            select(func.count()).select_from(Stage1BeneficiaryRevision)
        ) == before_stage1
