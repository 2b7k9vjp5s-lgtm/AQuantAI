"""Fully offline Industry Thesis owner-acceptance golden-path demo."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import create_engine, select
from sqlalchemy.pool import StaticPool

from backend.database.engine import build_session_factory
from backend.database.models import Base, StockBasicRecord
from industry_alpha.chain_map_models import IndustryMap, IndustryMapRevision
from industry_alpha.industry_thesis_commands import IndustryThesisCommandService
from industry_alpha.industry_thesis_owner_acceptance import (
    IndustryThesisOwnerAcceptanceService,
)
from industry_alpha.industry_thesis_owner_acceptance_contracts import (
    OWNER_ACCEPTANCE_PLAN_VERSION,
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
from industry_alpha.stage1_models import Stage1Beneficiary, Stage1BeneficiaryRevision

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
        "revision_note": "offline owner-acceptance demo",
    }


def build_industry_thesis_owner_acceptance_demo_payload() -> dict[str, Any]:
    """Run reviewed-plan acceptance and exact reads entirely in memory."""

    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = build_session_factory(engine)
    try:
        fixture = build_stage1_beneficiary_fixture(factory)
        selected_ids = (
            fixture.direct_beneficiary_id,
            fixture.draft_beneficiary_id,
            fixture.secondary_beneficiary_id,
        )
        with factory() as session:
            first = session.get(Stage1Beneficiary, selected_ids[0])
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
                    .where(
                        Stage1BeneficiaryRevision.beneficiary_id == beneficiary.id
                    )
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
                        "proposed_stock_basic_record_id": (
                            revision.stock_basic_record_id
                        ),
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
                    for index, (_beneficiary, revision, stock) in enumerate(
                        owner_rows
                    )
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
                "owner_context": {
                    "industry_map_revision_id": str(map_revision.id),
                },
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
            "reviewed_session_revision_id": reviewed[
                "reviewed_session_revision_id"
            ],
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
            "candidate_pool_operation": {
                "mode": "create_supported_handoff",
                "pool_key": "owner-acceptance-demo-supported",
                "title": "Owner acceptance demo supported handoff",
                "scope": "Exact supported accepted members only.",
            },
            "output_title": "Owner acceptance demo result",
            "output_scope": "Exact reviewed synthetic members only.",
            "information_cutoff_date": CUTOFF.isoformat(),
            "revision_note": "commit owner-acceptance demo",
            "owner_acceptance_plan_version": OWNER_ACCEPTANCE_PLAN_VERSION,
        }
        service = IndustryThesisOwnerAcceptanceService(
            factory,
            clock=lambda: BASE_TIME + timedelta(seconds=3),
        )
        preview = service.preview(raw)
        if not preview["commit_ready"]:
            raise RuntimeError("offline owner-acceptance preview unexpectedly blocked")
        committed = service.commit(
            {
                **raw,
                "preview_fingerprint_sha256": preview[
                    "preview_fingerprint_sha256"
                ],
            }
        )
        with factory() as session:
            exact = IndustryThesisAcceptedOutputQueryService(session).get_result(
                UUID(committed["output_link_revision_id"]),
                as_of_cutoff=CUTOFF,
                as_of_recorded_at_utc=BASE_TIME + timedelta(days=1),
            )
        return {
            "workflow_state": "accepted_outputs_linked",
            "complete_member_count": exact["complete_member_count"],
            "supported_handoff_count": exact["supported_handoff_count"],
            "accepted_candidate_pool_revision_present": (
                exact["accepted_candidate_pool_revision_id"] is not None
            ),
            "assessment_statuses": [
                item["assessment_status"] for item in exact["members"]
            ],
            "ranking_applied": exact["ranking_applied"],
            "owner_acceptance_plan_fingerprint_sha256": committed[
                "owner_acceptance_plan_fingerprint_sha256"
            ],
            "owner_transaction_id": committed["owner_transaction_id"],
        }
    finally:
        engine.dispose()


def main() -> None:
    import json

    print(
        json.dumps(
            build_industry_thesis_owner_acceptance_demo_payload(),
            indent=2,
            ensure_ascii=True,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
