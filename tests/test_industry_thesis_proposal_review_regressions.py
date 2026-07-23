from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from uuid import UUID

import pytest
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from backend.database.canonical_price_models import ListedInstrument
from backend.database.engine import build_session_factory
from backend.database.models import Base, IngestionRun, StockBasicRecord
import industry_alpha.stage1_models  # noqa: F401 - register output-link FK targets
from industry_alpha.industry_thesis_commands import IndustryThesisCommandService
from industry_alpha.industry_thesis_review import (
    ACCEPTANCE_PLAN_VERSION,
    IndustryThesisProposalReviewService,
    IndustryThesisReviewedPlanQueryService,
)
from industry_alpha.industry_thesis_rules import (
    BUILDER_VERSION,
    IndustryThesisError,
    IndustryThesisNotFound,
)

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


def _session_input() -> dict:
    return {
        "thesis_text_original": "review parity and visibility regression",
        "thesis_title_reviewed": "review regression",
        "driver_type": "unknown",
        "analysis_horizon_kind": "unknown",
        "market_scope": [
            {
                "market_namespace": "CN_A",
                "exchange_namespace": None,
                "security_type": "common_equity",
                "include_status": "active",
                "listed_instrument_ids": [],
            }
        ],
        "chain_boundary": {},
        "exclusions": [],
        "seed_companies": [],
        "seed_products": [],
        "seed_technologies": [],
        "seed_bottlenecks": [],
        "draft_graph": {},
        "coverage_state": "coverage_unknown",
        "workflow_state": "candidate_build_ready",
        "information_cutoff_date": CUTOFF.isoformat(),
        "revision_note": "regression fixture",
    }


def _seed_single_exact(database):
    with database.begin() as session:
        instrument = ListedInstrument(
            instrument_key="review-regression-instrument",
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
                    "source_reference": {"mapping_key": "review-regression"},
                    "proposed_listed_instrument_id": str(instrument_id),
                    "company_label_original": "Regression Company",
                    "benefit_path_text": "Explicit deterministic regression path.",
                    "proposed_exposure_type": "direct",
                    "proposal_confidence": "medium",
                    "identity_state": "exact_accepted_identity",
                    "review_state": "proposed",
                    "rationale": {"reason": "regression fixture"},
                    "uncertainty": {"state": "none"},
                }
            ],
        }
    )
    review_input = {
        "session_revision_id": created["session_revision_id"],
        "expected_session_latest_revision_number": 1,
        "acceptance_plan_version": ACCEPTANCE_PLAN_VERSION,
        "decisions": [
            {
                "candidate_revision_id": built["candidates"][0][
                    "candidate_revision_id"
                ],
                "expected_latest_revision_number": 1,
                "decision": "selected_for_acceptance",
                "final_proposed_exposure_type": "direct",
                "rationale": {"reason": "exact local identity"},
                "uncertainty": {"state": "reviewed_local_scope"},
            }
        ],
        "revision_note": "review regression candidate",
    }
    return review_input


def test_dry_run_and_commit_plan_match_across_different_clocks(database) -> None:
    review_input = _seed_single_exact(database)
    dry = IndustryThesisProposalReviewService(
        database,
        clock=lambda: BASE_TIME + timedelta(seconds=2),
    ).review_candidates(review_input, dry_run=True)
    committed = IndustryThesisProposalReviewService(
        database,
        clock=lambda: BASE_TIME + timedelta(minutes=10),
    ).review_candidates(review_input)

    assert dry["acceptance_plan"] == committed["acceptance_plan"]
    assert dry["acceptance_plan_fingerprint_sha256"] == committed[
        "acceptance_plan_fingerprint_sha256"
    ]
    assert dry["session_recorded_at_utc"] != committed["session_recorded_at_utc"]
    assert dry["candidate_recorded_at_utc"] != committed["candidate_recorded_at_utc"]


def test_intermediate_recorded_boundary_returns_not_visible(database) -> None:
    review_input = _seed_single_exact(database)
    committed = IndustryThesisProposalReviewService(
        database,
        clock=lambda: BASE_TIME + timedelta(seconds=2),
    ).review_candidates(review_input)

    with database() as session:
        query = IndustryThesisReviewedPlanQueryService(session)
        with pytest.raises(IndustryThesisNotFound) as exc_info:
            query.get_reviewed_plan(
                UUID(committed["reviewed_session_revision_id"]),
                as_of_cutoff=CUTOFF,
                as_of_recorded_at_utc=datetime.fromisoformat(
                    committed["session_recorded_at_utc"]
                ),
            )
    assert exc_info.value.code == "industry_thesis_not_visible"


def test_selected_candidate_rejects_two_unbound_identity_authorities(database) -> None:
    with database.begin() as session:
        instrument = ListedInstrument(
            instrument_key="review-regression-dual-identity",
            created_at_utc=BASE_TIME,
        )
        ingestion = IngestionRun(
            batch_identifier="review-regression-dual-identity",
            series_key="a" * 64,
            series_identity={"scope": "dual-identity-regression"},
            provider="fixture",
            dataset="stock_basic",
            completed_at=BASE_TIME,
            requested_start_date=CUTOFF,
            requested_end_date=CUTOFF,
            information_cutoff_date=CUTOFF,
            requested_scope={"market": "CN_A"},
            provider_request_metadata={},
            adapter_version="fixture-v1",
            snapshot_mode="complete",
            contract_version="fixture-v1",
            status="succeeded",
            row_count_received=1,
            row_count_written=1,
            dataset_counts={"stock_basic": 1},
        )
        session.add_all([instrument, ingestion])
        session.flush()
        stock = StockBasicRecord(
            ingestion_run_id=ingestion.id,
            stock_code="000001",
            stock_name="Dual Identity Company",
            exchange="SZSE",
            industry="fixture",
            listing_date=CUTOFF,
            status="active",
            source="fixture",
        )
        session.add(stock)
        session.flush()
        instrument_id = instrument.id
        stock_id = stock.id

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
                    "source_reference": {"mapping_key": "dual-authority"},
                    "proposed_stock_basic_record_id": stock_id,
                    "proposed_listed_instrument_id": str(instrument_id),
                    "company_label_original": "Dual Identity Company",
                    "benefit_path_text": "Two unbound identity authorities.",
                    "proposed_exposure_type": "direct",
                    "proposal_confidence": "medium",
                    "identity_state": "exact_accepted_identity",
                    "review_state": "proposed",
                    "rationale": {"reason": "regression fixture"},
                    "uncertainty": {"state": "none"},
                }
            ],
        }
    )
    raw = {
        "session_revision_id": created["session_revision_id"],
        "expected_session_latest_revision_number": 1,
        "acceptance_plan_version": ACCEPTANCE_PLAN_VERSION,
        "decisions": [
            {
                "candidate_revision_id": built["candidates"][0][
                    "candidate_revision_id"
                ],
                "expected_latest_revision_number": 1,
                "decision": "selected_for_acceptance",
                "final_proposed_exposure_type": "direct",
                "rationale": {"reason": "must fail closed"},
                "uncertainty": {"state": "identity_conflict"},
            }
        ],
        "revision_note": "dual identity authority rejection",
    }

    with pytest.raises(IndustryThesisError, match="exactly one authoritative"):
        IndustryThesisProposalReviewService(
            database,
            clock=lambda: BASE_TIME + timedelta(seconds=2),
        ).review_candidates(raw)
