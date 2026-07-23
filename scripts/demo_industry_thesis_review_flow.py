"""Deterministic offline three-candidate Industry Thesis review demo."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from backend.database.canonical_price_models import ListedInstrument
from backend.database.engine import build_session_factory
from backend.database.models import Base
import industry_alpha.stage1_models  # noqa: F401 - register output-link FK targets
from industry_alpha.industry_thesis_commands import IndustryThesisCommandService
from industry_alpha.industry_thesis_review import (
    ACCEPTANCE_PLAN_VERSION,
    IndustryThesisProposalReviewService,
    IndustryThesisReviewedPlanQueryService,
)
from industry_alpha.industry_thesis_rules import BUILDER_VERSION

UTC = timezone.utc
BASE_TIME = datetime(2026, 7, 22, 23, 0, tzinfo=UTC)
CUTOFF = date(2026, 7, 22)


def _session_input() -> dict[str, Any]:
    return {
        "thesis_text_original": "先进材料需求扩张与关键工艺瓶颈",
        "thesis_title_reviewed": "先进材料产业链",
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
        "revision_note": "offline fixture thesis",
    }


def _proposal(
    *,
    source_kind: str,
    source_reference: dict[str, str],
    label: str,
    identity_state: str,
    instrument_id: UUID | None = None,
) -> dict[str, Any]:
    proposal: dict[str, Any] = {
        "source_kind": source_kind,
        "source_reference": source_reference,
        "company_label_original": label,
        "benefit_path_text": f"{label} participates in the reviewed synthetic chain.",
        "proposed_exposure_type": (
            "direct" if identity_state == "exact_accepted_identity" else "unknown"
        ),
        "proposal_confidence": "medium",
        "identity_state": identity_state,
        "review_state": "proposed",
        "rationale": {"reason": "explicit local fixture input"},
        "uncertainty": {
            "state": (
                "none"
                if identity_state == "exact_accepted_identity"
                else "identity_pending"
            )
        },
    }
    if instrument_id is not None:
        proposal["proposed_listed_instrument_id"] = str(instrument_id)
    return proposal


def build_industry_thesis_review_demo_payload() -> dict[str, Any]:
    """Run create/build/review/read entirely in memory and return a small summary."""

    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = build_session_factory(engine)
    try:
        with factory.begin() as session:
            instrument = ListedInstrument(
                instrument_key="fixture-review-company-a",
                created_at_utc=BASE_TIME,
            )
            session.add(instrument)
            session.flush()
            instrument_id = instrument.id

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
                "allowed_source_kinds": ["user_seed", "accepted_local_mapping"],
                "proposals": [
                    _proposal(
                        source_kind="user_seed",
                        source_reference={"seed_key": "company-c"},
                        label="Company C",
                        identity_state="unresolved_identity",
                    ),
                    _proposal(
                        source_kind="accepted_local_mapping",
                        source_reference={"mapping_key": "company-a-product-x"},
                        label="Company A",
                        identity_state="exact_accepted_identity",
                        instrument_id=instrument_id,
                    ),
                    _proposal(
                        source_kind="user_seed",
                        source_reference={"seed_key": "company-b"},
                        label="Company B",
                        identity_state="ambiguous_identity",
                    ),
                ],
            }
        )
        rows = {row["company_label_original"]: row for row in built["candidates"]}
        reviewed = IndustryThesisProposalReviewService(
            factory,
            clock=lambda: BASE_TIME + timedelta(seconds=2),
        ).review_candidates(
            {
                "session_revision_id": created["session_revision_id"],
                "expected_session_latest_revision_number": 1,
                "acceptance_plan_version": ACCEPTANCE_PLAN_VERSION,
                "decisions": [
                    {
                        "candidate_revision_id": rows["Company A"][
                            "candidate_revision_id"
                        ],
                        "expected_latest_revision_number": 1,
                        "decision": "selected_for_acceptance",
                        "final_proposed_exposure_type": "direct",
                        "rationale": {"reason": "exact identity and direct path"},
                        "uncertainty": {"state": "reviewed_local_scope"},
                    },
                    {
                        "candidate_revision_id": rows["Company B"][
                            "candidate_revision_id"
                        ],
                        "expected_latest_revision_number": 1,
                        "decision": "rejected_by_user",
                        "rationale": {"reason": "ambiguous identity"},
                        "uncertainty": {"state": "not_selected"},
                    },
                    {
                        "candidate_revision_id": rows["Company C"][
                            "candidate_revision_id"
                        ],
                        "expected_latest_revision_number": 1,
                        "decision": "unresolved",
                        "rationale": {"reason": "identity remains unresolved"},
                        "uncertainty": {"state": "identity_pending"},
                    },
                ],
                "revision_note": "completed fixture three-candidate review",
            }
        )
        with factory() as session:
            read = IndustryThesisReviewedPlanQueryService(session).get_reviewed_plan(
                UUID(reviewed["reviewed_session_revision_id"]),
                as_of_cutoff=CUTOFF,
                as_of_recorded_at_utc=BASE_TIME + timedelta(seconds=3),
            )
        plan = read["acceptance_plan"]
        return {
            "workflow_state": read["workflow_state"],
            "candidate_count": reviewed["candidate_count"],
            "selected_count": len(plan["selected_candidates"]),
            "rejected_count": len(plan["rejected_candidate_revision_ids"]),
            "unresolved_count": len(plan["unresolved_candidate_revision_ids"]),
            "acceptance_plan_fingerprint_sha256": read[
                "acceptance_plan_fingerprint_sha256"
            ],
        }
    finally:
        engine.dispose()


def main() -> None:
    import json

    print(
        json.dumps(
            build_industry_thesis_review_demo_payload(),
            indent=2,
            ensure_ascii=True,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
