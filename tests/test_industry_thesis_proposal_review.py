from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from uuid import UUID

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.pool import StaticPool

from backend.database.canonical_price_models import ListedInstrument
from backend.database.engine import build_session_factory
from backend.database.models import Base
import industry_alpha.stage1_models  # noqa: F401 - register output-link FK targets
from industry_alpha.industry_thesis_commands import IndustryThesisCommandService
from industry_alpha.industry_thesis_models import (
    IndustryThesisCandidateRevision,
    IndustryThesisOutputLinkIdentity,
    IndustryThesisSessionRevision,
)
from industry_alpha.industry_thesis_review import (
    ACCEPTANCE_PLAN_VERSION,
    IndustryThesisProposalReviewService,
    IndustryThesisReviewedPlanQueryService,
)
from industry_alpha.industry_thesis_rules import BUILDER_VERSION, IndustryThesisError

UTC = timezone.utc
BASE_TIME = datetime(2026, 7, 22, 23, 0, tzinfo=UTC)
CUTOFF = date(2026, 7, 22)


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
        "revision_note": "initial offline thesis",
    }


def _proposal(
    *,
    source_kind: str,
    source_reference: dict,
    label: str,
    identity_state: str,
    instrument_id: UUID | None = None,
):
    result = {
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
        "rationale": {"reason": "explicit local test input"},
        "uncertainty": {
            "state": (
                "none"
                if identity_state == "exact_accepted_identity"
                else "identity_pending"
            )
        },
    }
    if instrument_id is not None:
        result["proposed_listed_instrument_id"] = str(instrument_id)
    return result


def _seed_three(database):
    with database.begin() as session:
        instrument = ListedInstrument(
            instrument_key="fixture-review-company-a",
            created_at_utc=BASE_TIME,
        )
        session.add(instrument)
        session.flush()
        instrument_id = instrument.id

    commands = IndustryThesisCommandService(database, clock=lambda: BASE_TIME)
    created = commands.create_session(_session_input())
    build_service = IndustryThesisCommandService(
        database,
        clock=lambda: BASE_TIME + timedelta(seconds=1),
    )
    committed = build_service.build_candidates(
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
    return created, committed, instrument_id


def _review_input(created, committed):
    rows = {row["company_label_original"]: row for row in committed["candidates"]}
    return {
        "session_revision_id": created["session_revision_id"],
        "expected_session_latest_revision_number": 1,
        "acceptance_plan_version": ACCEPTANCE_PLAN_VERSION,
        "decisions": [
            {
                "candidate_revision_id": rows["Company C"]["candidate_revision_id"],
                "expected_latest_revision_number": 1,
                "decision": "unresolved",
                "rationale": {"reason": "identity remains unresolved"},
                "uncertainty": {"state": "identity_pending"},
            },
            {
                "candidate_revision_id": rows["Company A"]["candidate_revision_id"],
                "expected_latest_revision_number": 1,
                "decision": "selected_for_acceptance",
                "final_proposed_exposure_type": "direct",
                "rationale": {"reason": "exact local identity and direct benefit path"},
                "uncertainty": {"state": "reviewed_local_scope"},
            },
            {
                "candidate_revision_id": rows["Company B"]["candidate_revision_id"],
                "expected_latest_revision_number": 1,
                "decision": "rejected_by_user",
                "rationale": {"reason": "ambiguous identity"},
                "uncertainty": {"state": "not_selected"},
            },
        ],
        "revision_note": "completed explicit three-candidate review",
    }


def test_three_candidate_review_freezes_deterministic_plan(database) -> None:
    created, committed, instrument_id = _seed_three(database)
    raw = _review_input(created, committed)

    dry = IndustryThesisProposalReviewService(
        database,
        clock=lambda: BASE_TIME + timedelta(seconds=2),
    ).review_candidates(raw, dry_run=True)
    committed_review = IndustryThesisProposalReviewService(
        database,
        clock=lambda: BASE_TIME + timedelta(seconds=2),
    ).review_candidates(raw)

    assert dry["acceptance_plan"] == committed_review["acceptance_plan"]
    assert dry["reviewed_session_revision_id"] == committed_review[
        "reviewed_session_revision_id"
    ]
    plan = committed_review["acceptance_plan"]
    assert len(plan["selected_candidates"]) == 1
    assert plan["selected_candidates"][0]["proposed_listed_instrument_id"] == str(
        instrument_id
    )
    assert len(plan["rejected_candidate_revision_ids"]) == 1
    assert len(plan["unresolved_candidate_revision_ids"]) == 1

    with database() as session:
        assert session.scalar(
            select(func.count()).select_from(IndustryThesisSessionRevision)
        ) == 2
        assert session.scalar(
            select(func.count()).select_from(IndustryThesisCandidateRevision)
        ) == 6
        assert session.scalar(
            select(func.count()).select_from(IndustryThesisOutputLinkIdentity)
        ) == 0
        states = set(
            session.scalars(
                select(IndustryThesisCandidateRevision.review_state).where(
                    IndustryThesisCandidateRevision.session_revision_id
                    == UUID(committed_review["reviewed_session_revision_id"])
                )
            )
        )
        assert states == {
            "selected_for_acceptance",
            "rejected_by_user",
            "unresolved",
        }
        query = IndustryThesisReviewedPlanQueryService(session)
        read = query.get_reviewed_plan(
            UUID(committed_review["reviewed_session_revision_id"]),
            as_of_cutoff=CUTOFF,
            as_of_recorded_at_utc=BASE_TIME + timedelta(seconds=3),
        )
        assert read["acceptance_plan_fingerprint_sha256"] == committed_review[
            "acceptance_plan_fingerprint_sha256"
        ]


def test_review_order_does_not_change_plan_or_fingerprint(database) -> None:
    created, committed, _ = _seed_three(database)
    raw = _review_input(created, committed)
    reverse = dict(raw)
    reverse["decisions"] = list(reversed(raw["decisions"]))

    first = IndustryThesisProposalReviewService(
        database,
        clock=lambda: BASE_TIME + timedelta(seconds=2),
    ).review_candidates(raw, dry_run=True)
    second = IndustryThesisProposalReviewService(
        database,
        clock=lambda: BASE_TIME + timedelta(seconds=2),
    ).review_candidates(reverse, dry_run=True)

    assert first["acceptance_plan"] == second["acceptance_plan"]
    assert first["acceptance_plan_fingerprint_sha256"] == second[
        "acceptance_plan_fingerprint_sha256"
    ]


def test_incomplete_stale_and_ambiguous_selection_fail_atomically(database) -> None:
    created, committed, _ = _seed_three(database)
    raw = _review_input(created, committed)

    incomplete = dict(raw)
    incomplete["decisions"] = raw["decisions"][:-1]
    service = IndustryThesisProposalReviewService(
        database,
        clock=lambda: BASE_TIME + timedelta(seconds=2),
    )
    with pytest.raises(IndustryThesisError, match="complete exact latest"):
        service.review_candidates(incomplete)

    ambiguous_selected = _review_input(created, committed)
    for decision in ambiguous_selected["decisions"]:
        if decision["decision"] == "rejected_by_user":
            decision["decision"] = "selected_for_acceptance"
            decision["final_proposed_exposure_type"] = "conditional"
    with pytest.raises(IndustryThesisError, match="exact accepted identity"):
        service.review_candidates(ambiguous_selected)

    stale = _review_input(created, committed)
    stale["decisions"][0]["expected_latest_revision_number"] = 2
    with pytest.raises(IndustryThesisError, match="expected latest candidate"):
        service.review_candidates(stale)

    with database() as session:
        assert session.scalar(
            select(func.count()).select_from(IndustryThesisSessionRevision)
        ) == 1
        assert session.scalar(
            select(func.count()).select_from(IndustryThesisCandidateRevision)
        ) == 3


def test_duplicate_selected_exact_identity_is_rejected(database) -> None:
    with database.begin() as session:
        instrument = ListedInstrument(
            instrument_key="fixture-review-duplicate",
            created_at_utc=BASE_TIME,
        )
        session.add(instrument)
        session.flush()
        instrument_id = instrument.id

    commands = IndustryThesisCommandService(database, clock=lambda: BASE_TIME)
    created = commands.create_session(_session_input())
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
                _proposal(
                    source_kind="accepted_local_mapping",
                    source_reference={"mapping_key": "duplicate-a"},
                    label="Duplicate A",
                    identity_state="exact_accepted_identity",
                    instrument_id=instrument_id,
                ),
                _proposal(
                    source_kind="accepted_local_mapping",
                    source_reference={"mapping_key": "duplicate-b"},
                    label="Duplicate B",
                    identity_state="exact_accepted_identity",
                    instrument_id=instrument_id,
                ),
            ],
        }
    )
    raw = {
        "session_revision_id": created["session_revision_id"],
        "expected_session_latest_revision_number": 1,
        "acceptance_plan_version": ACCEPTANCE_PLAN_VERSION,
        "decisions": [
            {
                "candidate_revision_id": row["candidate_revision_id"],
                "expected_latest_revision_number": 1,
                "decision": "selected_for_acceptance",
                "final_proposed_exposure_type": "direct",
                "rationale": {"reason": "test"},
                "uncertainty": {"state": "none"},
            }
            for row in built["candidates"]
        ],
        "revision_note": "duplicate identity test",
    }
    with pytest.raises(IndustryThesisError, match="same exact persisted identity"):
        IndustryThesisProposalReviewService(
            database,
            clock=lambda: BASE_TIME + timedelta(seconds=2),
        ).review_candidates(raw)
