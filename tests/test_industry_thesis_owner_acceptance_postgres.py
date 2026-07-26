from __future__ import annotations

from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone
import os
from threading import RLock

from alembic import command
from alembic.config import Config
import pytest
from sqlalchemy import func, select, text
from sqlalchemy.engine import make_url

from backend.database import build_engine, build_session_factory
from backend.database.models import StockBasicRecord
from industry_alpha.chain_map_models import IndustryMap, IndustryMapRevision
import industry_alpha.industry_thesis_owner_acceptance as acceptance_module
from industry_alpha.industry_thesis_commands import IndustryThesisCommandService
from industry_alpha.industry_thesis_models import (
    IndustryThesisOutputLinkRevision,
    IndustryThesisSessionRevision,
)
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
from industry_alpha.stage1_fixtures import build_stage1_beneficiary_fixture
from industry_alpha.stage1_models import (
    Stage1Beneficiary,
    Stage1BeneficiaryRevision,
    Stage1CandidatePool,
)

UTC = timezone.utc


@pytest.fixture(scope="module")
def postgres_database_url() -> Iterator[str]:
    database_url = os.getenv("TEST_DATABASE_URL", "").strip()
    if not database_url:
        pytest.skip("TEST_DATABASE_URL is not configured")
    if "test" not in (make_url(database_url).database or "").lower():
        pytest.fail("TEST_DATABASE_URL must target a database whose name contains 'test'.")
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", database_url)
    command.downgrade(config, "base")
    command.upgrade(config, "head")
    yield database_url
    command.downgrade(config, "base")


@pytest.fixture(autouse=True)
def clean_owner_acceptance(postgres_database_url: str) -> Iterator[None]:
    engine = build_engine(postgres_database_url)
    try:
        with engine.begin() as connection:
            connection.execute(
                text(
                    "TRUNCATE industry_thesis_session_identities, "
                    "research_cases, ingestion_runs RESTART IDENTITY CASCADE"
                )
            )
        yield
    finally:
        with engine.begin() as connection:
            connection.execute(
                text(
                    "TRUNCATE industry_thesis_session_identities, "
                    "research_cases, ingestion_runs RESTART IDENTITY CASCADE"
                )
            )
        engine.dispose()


def _stored_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _session_input(cutoff: date) -> dict:
    return {
        "thesis_text_original": "PostgreSQL owner acceptance exact fixture",
        "thesis_title_reviewed": "PostgreSQL owner acceptance",
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
        "chain_boundary": {"included": ["fixture-chain"]},
        "exclusions": [],
        "seed_companies": [],
        "seed_products": ["fixture-product"],
        "seed_technologies": [],
        "seed_bottlenecks": ["fixture-bottleneck"],
        "draft_graph": {"nodes": [], "relationships": []},
        "coverage_state": "partial_local_coverage",
        "workflow_state": "candidate_build_ready",
        "information_cutoff_date": cutoff.isoformat(),
        "revision_note": "Exact PostgreSQL reviewed-plan fixture.",
    }


def _reviewed_fixture(factory):
    fixture = build_stage1_beneficiary_fixture(factory)
    with factory() as session:
        beneficiary = session.get(
            Stage1Beneficiary,
            fixture.direct_beneficiary_id,
        )
        assert beneficiary is not None
        beneficiary_revision = session.scalar(
            select(Stage1BeneficiaryRevision)
            .where(Stage1BeneficiaryRevision.beneficiary_id == beneficiary.id)
            .order_by(Stage1BeneficiaryRevision.revision_no.desc())
        )
        assert beneficiary_revision is not None
        stock = session.get(
            StockBasicRecord,
            beneficiary_revision.stock_basic_record_id,
        )
        industry_map = session.get(IndustryMap, beneficiary.map_id)
        assert stock is not None and industry_map is not None
        map_revision = session.scalar(
            select(IndustryMapRevision)
            .where(IndustryMapRevision.map_id == industry_map.id)
            .order_by(IndustryMapRevision.revision_no.desc())
        )
        assert map_revision is not None
        base_recorded = max(
            _stored_utc(beneficiary_revision.recorded_at_utc),
            _stored_utc(map_revision.recorded_at_utc),
        )

    created = IndustryThesisCommandService(
        factory,
        clock=lambda: base_recorded + timedelta(seconds=1),
    ).create_session(_session_input(beneficiary_revision.information_cutoff_date))
    built = IndustryThesisCommandService(
        factory,
        clock=lambda: base_recorded + timedelta(seconds=2),
    ).build_candidates(
        {
            "session_revision_id": created["session_revision_id"],
            "expected_session_latest_revision_number": 1,
            "builder_version": BUILDER_VERSION,
            "allowed_source_kinds": ["accepted_local_mapping"],
            "proposals": [
                {
                    "source_kind": "accepted_local_mapping",
                    "source_reference": {
                        "fixture_binding": "postgres-owner-acceptance"
                    },
                    "proposed_stock_basic_record_id": (
                        beneficiary_revision.stock_basic_record_id
                    ),
                    "company_label_original": stock.stock_name,
                    "product_or_service_fit": "Synthetic exact fixture.",
                    "industry_position": "Synthetic exact chain position.",
                    "benefit_path_text": "Exact accepted local Stage 1 path.",
                    "proposed_exposure_type": "direct",
                    "proposal_confidence": "medium",
                    "identity_state": "exact_accepted_identity",
                    "review_state": "proposed",
                    "rationale": {"reason": "exact local identity"},
                    "uncertainty": {"state": "review_required"},
                }
            ],
        }
    )
    candidate = built["candidates"][0]
    review = IndustryThesisProposalReviewService(
        factory,
        clock=lambda: base_recorded + timedelta(seconds=3),
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
                    "candidate_revision_id": candidate["candidate_revision_id"],
                    "expected_latest_revision_number": 1,
                    "decision": "selected_for_acceptance",
                    "final_proposed_exposure_type": "direct",
                    "rationale": {"reason": "explicit owner-acceptance fixture"},
                    "uncertainty": {"state": "reviewed_local_scope"},
                }
            ],
            "revision_note": "selected exact owner-bound candidate",
        }
    )
    raw = {
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
        "candidate_owner_bindings": [
            {
                "reviewed_candidate_revision_id": review["acceptance_plan"][
                    "selected_candidates"
                ][0]["candidate_revision_id"],
                "sequence": 0,
                "stage1_operation": "reuse_exact_beneficiary_revision",
                "stage1": {
                    "beneficiary_id": str(beneficiary.id),
                    "beneficiary_revision_id": str(beneficiary_revision.id),
                    "stock_basic_record_id": (
                        beneficiary_revision.stock_basic_record_id
                    ),
                },
                "semantic_operation": "none",
                "semantic": None,
                "readiness_note": "Semantic profile remains explicitly absent.",
            }
        ],
        "candidate_pool_operation": {
            "mode": "create_supported_handoff",
            "pool_key": "postgres-owner-acceptance-supported",
            "title": "PostgreSQL supported handoff",
            "scope": "Exact supported accepted member only.",
        },
        "output_title": "PostgreSQL exact accepted result",
        "output_scope": "Exact reviewed synthetic member only.",
        "information_cutoff_date": (
            beneficiary_revision.information_cutoff_date.isoformat()
        ),
        "revision_note": "Atomic PostgreSQL owner acceptance.",
        "owner_acceptance_plan_version": OWNER_ACCEPTANCE_PLAN_VERSION,
    }
    recorded = max(
        datetime.fromisoformat(review["session_recorded_at_utc"]),
        datetime.fromisoformat(review["candidate_recorded_at_utc"]),
    )
    return raw, recorded


def test_postgres_identical_concurrent_commit_serializes_to_one_output(
    postgres_database_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine = build_engine(postgres_database_url)
    factory = build_session_factory(engine)
    raw, recorded = _reviewed_fixture(factory)
    service = IndustryThesisOwnerAcceptanceService(
        factory,
        clock=lambda: recorded + timedelta(seconds=1),
    )
    preview = service.preview(raw)
    assert preview["commit_ready"] is True
    commit_input = {
        **raw,
        "preview_fingerprint_sha256": preview["preview_fingerprint_sha256"],
    }
    with factory() as session:
        before_pools = session.scalar(
            select(func.count()).select_from(Stage1CandidatePool)
        )

    # Each commit receives an independent in-process lock. Correctness must come
    # from PostgreSQL row locks and uniqueness constraints, not Python serialization.
    monkeypatch.setattr(acceptance_module, "_lock", lambda _key: RLock())

    def commit(_: int):
        return IndustryThesisOwnerAcceptanceService(
            factory,
            clock=lambda: recorded + timedelta(seconds=1),
        ).commit(commit_input)

    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(commit, (1, 2)))
        assert sorted(item["idempotent_replay"] for item in results) == [False, True]
        assert len({item["output_link_revision_id"] for item in results}) == 1
        assert len({item["accepted_session_revision_id"] for item in results}) == 1
        with factory() as session:
            assert session.scalar(
                select(func.count()).select_from(IndustryThesisOutputLinkRevision)
            ) == 1
            assert session.scalar(
                select(func.count())
                .select_from(IndustryThesisSessionRevision)
                .where(
                    IndustryThesisSessionRevision.workflow_state
                    == "accepted_outputs_linked"
                )
            ) == 1
            assert session.scalar(
                select(func.count()).select_from(Stage1CandidatePool)
            ) == before_pools + 1
    finally:
        engine.dispose()
