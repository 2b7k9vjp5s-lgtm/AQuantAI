"""Production-boundary offline demo for exact industry research result assembly."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
import json
from typing import Any
from uuid import UUID

from sqlalchemy import create_engine, select
from sqlalchemy.pool import StaticPool

from backend.database.engine import build_session_factory
from backend.database.models import Base, StockBasicRecord
from industry_alpha.chain_map_models import IndustryMap, IndustryMapRevision
from industry_alpha.industry_research_result_query import (
    IndustryResearchResultQueryService,
)
from industry_alpha.industry_thesis_commands import IndustryThesisCommandService
from industry_alpha.industry_thesis_owner_acceptance import (
    IndustryThesisOwnerAcceptanceService,
)
from industry_alpha.industry_thesis_owner_acceptance_contracts import (
    OWNER_ACCEPTANCE_PLAN_VERSION,
)
from industry_alpha.industry_thesis_review import (
    ACCEPTANCE_PLAN_VERSION,
    IndustryThesisProposalReviewService,
)
from industry_alpha.industry_thesis_rules import BUILDER_VERSION
from industry_alpha.investment_candidate_commands import (
    InvestmentCandidateCommandService,
)
from industry_alpha.investment_candidate_rules import PURPOSE_CODE, RULE_VERSION
from industry_alpha.stage1_fixtures import build_stage1_beneficiary_fixture
from industry_alpha.stage1_models import (
    Stage1Beneficiary,
    Stage1BeneficiaryRevision,
    Stage1CandidatePoolMembership,
    Stage1CandidatePoolRevision,
)

UTC = timezone.utc
CUTOFF = date(2026, 7, 9)
BASE_TIME = datetime(2026, 7, 10, 12, tzinfo=UTC)


def _session_input() -> dict[str, Any]:
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
        "revision_note": "offline result-assembly demo",
    }


def _candidate_manifest(factory, pool_revision_id: UUID) -> tuple[UUID, list[dict[str, Any]]]:
    with factory() as session:
        pool_revision = session.get(Stage1CandidatePoolRevision, pool_revision_id)
        if pool_revision is None:
            raise RuntimeError("accepted candidate-pool revision is missing")
        memberships = list(
            session.scalars(
                select(Stage1CandidatePoolMembership)
                .where(
                    Stage1CandidatePoolMembership.candidate_pool_revision_id
                    == pool_revision.id
                )
                .order_by(Stage1CandidatePoolMembership.id)
            )
        )
        return pool_revision.candidate_pool_id, [
            {
                "candidate_pool_membership_id": str(row.id),
                "beneficiary_id": str(row.beneficiary_id),
                "beneficiary_revision_id": str(row.beneficiary_revision_id),
                "company_research_revision_id": None,
                "typed_beneficiary_revision_id": None,
                "canonical_price_revision_id": None,
                "comparison_eligibility_revision_id": None,
                "component_revision_ids": {},
            }
            for row in memberships
        ]


def seed_industry_research_result_demo(
    factory, *, zero_supported: bool = False
) -> dict[str, Any]:
    """Persist one accepted result and, when supported, two exact snapshots."""

    fixture = build_stage1_beneficiary_fixture(factory)
    selected_ids = (
        (fixture.draft_beneficiary_id, fixture.disputed_beneficiary_id)
        if zero_supported
        else (
            fixture.direct_beneficiary_id,
            fixture.draft_beneficiary_id,
            fixture.secondary_beneficiary_id,
        )
    )
    with factory() as session:
        first = session.get(Stage1Beneficiary, selected_ids[0])
        if first is None:
            raise RuntimeError("Stage 1 demo beneficiary is missing")
        industry_map = session.get(IndustryMap, first.map_id)
        map_revision = session.scalar(
            select(IndustryMapRevision)
            .where(IndustryMapRevision.map_id == industry_map.id)
            .order_by(IndustryMapRevision.revision_no.desc())
        )
        owner_rows = []
        for beneficiary_id in selected_ids:
            beneficiary = session.get(Stage1Beneficiary, beneficiary_id)
            revision = session.scalar(
                select(Stage1BeneficiaryRevision)
                .where(Stage1BeneficiaryRevision.beneficiary_id == beneficiary.id)
                .order_by(Stage1BeneficiaryRevision.revision_no.desc())
            )
            stock = session.get(StockBasicRecord, revision.stock_basic_record_id)
            owner_rows.append((beneficiary, revision, stock))

    created = IndustryThesisCommandService(
        factory,
        clock=lambda: BASE_TIME,
    ).create_session(_session_input())
    built = IndustryThesisCommandService(
        factory,
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
                    "source_reference": {"demo_binding": str(index)},
                    "proposed_stock_basic_record_id": revision.stock_basic_record_id,
                    "company_label_original": stock.stock_name,
                    "product_or_service_fit": "Synthetic demo product fit.",
                    "industry_position": "Synthetic demo chain position.",
                    "benefit_path_text": "Evidence-backed synthetic demo path.",
                    "proposed_exposure_type": (
                        "direct",
                        "conditional",
                        "indirect",
                    )[index],
                    "proposal_confidence": "medium",
                    "identity_state": "exact_accepted_identity",
                    "review_state": "proposed",
                    "rationale": {"reason": "exact local stock_basic"},
                    "uncertainty": {"state": "review_required"},
                }
                for index, (_beneficiary, revision, stock) in enumerate(owner_rows)
            ],
        }
    )
    reviewed = IndustryThesisProposalReviewService(
        factory,
        clock=lambda: BASE_TIME + timedelta(seconds=2),
    ).review_candidates(
        {
            "session_revision_id": created["session_revision_id"],
            "expected_session_latest_revision_number": 1,
            "acceptance_plan_version": ACCEPTANCE_PLAN_VERSION,
            "owner_context": {"industry_map_revision_id": str(map_revision.id)},
            "decisions": [
                {
                    "candidate_revision_id": item["candidate_revision_id"],
                    "expected_latest_revision_number": 1,
                    "decision": "selected_for_acceptance",
                    "final_proposed_exposure_type": item[
                        "proposed_exposure_type"
                    ],
                    "rationale": {"reason": "explicit reviewed demo decision"},
                    "uncertainty": {"state": "reviewed_local_scope"},
                }
                for item in built["candidates"]
            ],
            "revision_note": "reviewed all exact demo candidates",
        }
    )
    by_stock = {
        item["proposed_stock_basic_record_id"]: item["candidate_revision_id"]
        for item in reviewed["acceptance_plan"]["selected_candidates"]
    }
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
                "reviewed_candidate_revision_id": by_stock[
                    revision.stock_basic_record_id
                ],
                "sequence": index,
                "stage1_operation": "reuse_exact_beneficiary_revision",
                "stage1": {
                    "beneficiary_id": str(beneficiary.id),
                    "beneficiary_revision_id": str(revision.id),
                    "stock_basic_record_id": revision.stock_basic_record_id,
                },
                "semantic_operation": "none",
                "semantic": None,
                "readiness_note": "Typed semantics remains an explicit gap.",
            }
            for index, (beneficiary, revision, _stock) in enumerate(owner_rows)
        ],
        "candidate_pool_operation": (
            {"mode": "none_no_supported_members"}
            if zero_supported
            else {
                "mode": "create_supported_handoff",
                "pool_key": "result-assembly-demo-supported",
                "title": "Result assembly demo supported handoff",
                "scope": "Exact supported accepted members only.",
            }
        ),
        "output_title": "Result assembly demo accepted output",
        "output_scope": "Exact reviewed synthetic members only.",
        "information_cutoff_date": CUTOFF.isoformat(),
        "revision_note": "commit result-assembly demo acceptance",
        "owner_acceptance_plan_version": OWNER_ACCEPTANCE_PLAN_VERSION,
    }
    acceptance = IndustryThesisOwnerAcceptanceService(
        factory,
        clock=lambda: BASE_TIME + timedelta(seconds=3),
    )
    preview = acceptance.preview(raw)
    if not preview["commit_ready"]:
        raise RuntimeError("offline result-assembly preview unexpectedly blocked")
    committed = acceptance.commit(
        {
            **raw,
            "preview_fingerprint_sha256": preview["preview_fingerprint_sha256"],
        }
    )
    first_snapshot_revision_id = None
    second_snapshot_revision_id = None
    pool_revision_text = committed["accepted_candidate_pool_revision_id"]
    if pool_revision_text is not None:
        pool_revision_id = UUID(pool_revision_text)
        pool_id, members = _candidate_manifest(factory, pool_revision_id)
        candidate = InvestmentCandidateCommandService(factory)
        first_snapshot = candidate.record_snapshot(
            {
                "candidate_pool_id": str(pool_id),
                "candidate_pool_revision_id": str(pool_revision_id),
                "purpose_code": PURPOSE_CODE,
                "rule_version": RULE_VERSION,
                "snapshot_key": "result-assembly-demo-current",
                "expected_latest_revision_id": None,
                "information_cutoff_date": CUTOFF.isoformat(),
                "recorded_at_utc": (BASE_TIME + timedelta(seconds=4)).isoformat(),
                "recorded_by": "offline-demo",
                "members": members,
            }
        )
        second_snapshot = candidate.record_snapshot(
            {
                "candidate_pool_id": str(pool_id),
                "candidate_pool_revision_id": str(pool_revision_id),
                "purpose_code": PURPOSE_CODE,
                "rule_version": RULE_VERSION,
                "snapshot_key": "result-assembly-demo-current",
                "expected_latest_revision_id": first_snapshot["snapshot_revision_id"],
                "information_cutoff_date": CUTOFF.isoformat(),
                "recorded_at_utc": (BASE_TIME + timedelta(seconds=5)).isoformat(),
                "recorded_by": "offline-demo",
                "members": members,
            }
        )
        first_snapshot_revision_id = first_snapshot["snapshot_revision_id"]
        second_snapshot_revision_id = second_snapshot["snapshot_revision_id"]
    return {
        "output_link_revision_id": committed["output_link_revision_id"],
        "accepted_session_revision_id": committed["accepted_session_revision_id"],
        "session_id": created["session_id"],
        "industry_map_revision_id": str(map_revision.id),
        "candidate_pool_revision_id": pool_revision_text,
        "first_snapshot_revision_id": first_snapshot_revision_id,
        "second_snapshot_revision_id": second_snapshot_revision_id,
        "as_of_cutoff": CUTOFF,
        "as_of_recorded_at_utc": BASE_TIME + timedelta(seconds=6),
    }


def run_demo() -> dict[str, Any]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = build_session_factory(engine)
    try:
        seeded = seed_industry_research_result_demo(factory)
        with factory() as session:
            service = IndustryResearchResultQueryService(session)
            unselected = service.get_assembled_result(
                UUID(seeded["output_link_revision_id"]),
                as_of_cutoff=seeded["as_of_cutoff"],
                as_of_recorded_at_utc=seeded["as_of_recorded_at_utc"],
            )
            selected = service.get_assembled_result(
                UUID(seeded["output_link_revision_id"]),
                as_of_cutoff=seeded["as_of_cutoff"],
                as_of_recorded_at_utc=seeded["as_of_recorded_at_utc"],
                investment_candidate_snapshot_revision_id=UUID(
                    seeded["second_snapshot_revision_id"]
                ),
            )
        assert unselected["candidate_overlay"]["state"] == "not_selected"
        assert unselected["candidate_snapshot_options"]["auto_selected"] is False
        assert len(unselected["candidate_snapshot_options"]["options"]) == 2
        assert selected["candidate_overlay"]["state"] == "selected"
        assert selected["accepted_snapshot"]["complete_member_count"] == 3
        assert selected["candidate_overlay"]["snapshot"]["member_count"] == 2
        assert sum(
            item["candidate_overlay"] is not None
            for item in selected["accepted_snapshot"]["members"]
        ) == 2
        assert selected["industry_map"]["map_revision_id"] == seeded[
            "industry_map_revision_id"
        ]
        assert selected["industry_map"]["latest_fallback_used"] is False
        assert selected["writes_performed"] is False
        return {
            "result_contract_version": selected["result_contract_version"],
            "complete_accepted_members": selected["accepted_snapshot"][
                "complete_member_count"
            ],
            "supported_handoff_members": selected["accepted_snapshot"][
                "supported_handoff_count"
            ],
            "candidate_snapshot_options": len(
                unselected["candidate_snapshot_options"]["options"]
            ),
            "auto_selected": unselected["candidate_snapshot_options"][
                "auto_selected"
            ],
            "selected_overlay_members": selected["candidate_overlay"]["snapshot"][
                "member_count"
            ],
            "exact_map_revision": selected["industry_map"]["map_revision_id"],
            "latest_map_fallback": selected["industry_map"][
                "latest_fallback_used"
            ],
            "writes_performed": selected["writes_performed"],
            "external_network": False,
            "candidate_recomputation": False,
        }
    finally:
        engine.dispose()


def main() -> None:
    print(json.dumps(run_demo(), ensure_ascii=False, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
