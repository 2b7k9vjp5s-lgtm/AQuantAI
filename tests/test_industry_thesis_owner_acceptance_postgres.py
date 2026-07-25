from __future__ import annotations

from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import os
from threading import RLock
from uuid import uuid4

from alembic import command
from alembic.config import Config
import pytest
from sqlalchemy import func, select, text
from sqlalchemy.engine import make_url

from backend.database import build_engine, build_session_factory
from industry_alpha.chain_map_models import IndustryMap, IndustryMapRevision
import industry_alpha.industry_thesis_owner_acceptance as acceptance_module
from industry_alpha.industry_thesis_models import (
    IndustryThesisCandidateIdentity,
    IndustryThesisCandidateRevision,
    IndustryThesisOutputLinkRevision,
    IndustryThesisSessionIdentity,
    IndustryThesisSessionRevision,
)
from industry_alpha.industry_thesis_owner_acceptance import (
    IndustryThesisOwnerAcceptanceService,
)
from industry_alpha.industry_thesis_owner_acceptance_contracts import (
    OWNER_ACCEPTANCE_PLAN_VERSION,
)
from industry_alpha.industry_thesis_rules import canonical_json_text, fingerprint
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
                text("TRUNCATE research_cases, ingestion_runs RESTART IDENTITY CASCADE")
            )
        yield
    finally:
        with engine.begin() as connection:
            connection.execute(
                text("TRUNCATE research_cases, ingestion_runs RESTART IDENTITY CASCADE")
            )
        engine.dispose()


def _reviewed_fixture(factory):
    fixture = build_stage1_beneficiary_fixture(factory)
    with factory.begin() as session:
        beneficiary = session.get(
            Stage1Beneficiary,
            fixture.direct_beneficiary_id,
        )
        beneficiary_revision = session.scalar(
            select(Stage1BeneficiaryRevision)
            .where(Stage1BeneficiaryRevision.beneficiary_id == beneficiary.id)
            .order_by(Stage1BeneficiaryRevision.revision_no.desc())
        )
        industry_map = session.get(IndustryMap, beneficiary.map_id)
        map_revision = session.scalar(
            select(IndustryMapRevision)
            .where(IndustryMapRevision.map_id == industry_map.id)
            .order_by(IndustryMapRevision.revision_no.desc())
        )
        recorded = max(
            beneficiary_revision.recorded_at_utc.astimezone(UTC),
            map_revision.recorded_at_utc.astimezone(UTC),
        ) + timedelta(seconds=1)
        session_identity = IndustryThesisSessionIdentity(
            created_recorded_utc=recorded,
            created_by_kind="local_user",
            state="active",
            latest_revision_number=1,
        )
        session.add(session_identity)
        session.flush()
        candidate_identity = IndustryThesisCandidateIdentity(
            session_id=session_identity.id,
            candidate_key="d" * 64,
            created_recorded_utc=recorded,
            latest_revision_number=1,
        )
        session.add(candidate_identity)
        session.flush()
        reviewed_revision_id = uuid4()
        candidate_revision_id = uuid4()
        reviewed_plan_base = {
            "acceptance_plan_version": "aquantai.industry-thesis-acceptance-plan.v1",
            "reviewed_session_revision_id": str(reviewed_revision_id),
            "selected_candidates": [
                {
                    "candidate_revision_id": str(candidate_revision_id),
                    "proposed_stock_basic_record_id": (
                        beneficiary_revision.stock_basic_record_id
                    ),
                }
            ],
            "rejected_candidates": [],
            "unresolved_candidates": [],
        }
        reviewed_plan = {
            **reviewed_plan_base,
            "acceptance_plan_fingerprint_sha256": fingerprint(reviewed_plan_base),
        }
        reviewed = IndustryThesisSessionRevision(
            id=reviewed_revision_id,
            session_id=session_identity.id,
            revision_number=1,
            thesis_text_original="PostgreSQL owner acceptance exact fixture",
            thesis_title_reviewed="PostgreSQL owner acceptance",
            driver_type="demand_expansion",
            analysis_horizon_kind="medium_term",
            analysis_start_date=None,
            analysis_end_date=None,
            market_scope_json=canonical_json_text(
                [
                    {
                        "market_namespace": "CN_A",
                        "exchange_namespace": None,
                        "security_type": "common_equity",
                        "include_status": "active",
                        "listed_instrument_ids": [],
                    }
                ],
                "market scope",
            ),
            chain_boundary_json=canonical_json_text({}, "chain boundary"),
            exclusions_json=canonical_json_text([], "exclusions"),
            seed_companies_json=canonical_json_text([], "seed companies"),
            seed_products_json=canonical_json_text([], "seed products"),
            seed_technologies_json=canonical_json_text([], "seed technologies"),
            seed_bottlenecks_json=canonical_json_text([], "seed bottlenecks"),
            draft_graph_json=canonical_json_text(
                {
                    "base_draft_graph": {},
                    "acceptance_plan_preview": reviewed_plan,
                },
                "reviewed draft graph",
            ),
            coverage_state="partial_local_coverage",
            workflow_state="reviewed_plan_ready",
            information_cutoff_date=beneficiary_revision.information_cutoff_date,
            recorded_at_utc=recorded,
            input_fingerprint_sha256="e" * 64,
            supersedes_revision_id=None,
            revision_note="Exact PostgreSQL reviewed-plan fixture.",
        )
        candidate_revision = IndustryThesisCandidateRevision(
            id=candidate_revision_id,
            candidate_id=candidate_identity.id,
            session_revision_id=reviewed_revision_id,
            revision_number=1,
            source_kind="accepted_local_mapping",
            source_reference_json=canonical_json_text(
                {"fixture": "postgres-owner-acceptance"},
                "source reference",
            ),
            proposed_stock_basic_record_id=beneficiary_revision.stock_basic_record_id,
            proposed_listed_instrument_id=None,
            company_label_original="PostgreSQL owner acceptance fixture",
            product_or_service_fit="Synthetic exact fixture.",
            industry_position="Synthetic exact chain position.",
            benefit_path_text="Exact accepted local Stage 1 path.",
            proposed_exposure_type="direct",
            proposal_confidence="medium",
            identity_state="exact_accepted_identity",
            review_state="selected_for_acceptance",
            rationale_json=canonical_json_text(
                {"reason": "exact local identity"},
                "candidate rationale",
            ),
            uncertainty_json=canonical_json_text(
                {"state": "reviewed"},
                "candidate uncertainty",
            ),
            manifest_fingerprint_sha256=None,
            information_cutoff_date=beneficiary_revision.information_cutoff_date,
            recorded_at_utc=recorded,
            supersedes_revision_id=None,
        )
        session.add_all((reviewed, candidate_revision))
        session.flush()
        raw = {
            "reviewed_session_revision_id": str(reviewed.id),
            "expected_session_latest_revision_number": 1,
            "reviewed_plan_fingerprint_sha256": reviewed_plan[
                "acceptance_plan_fingerprint_sha256"
            ],
            "research_case_id": str(industry_map.case_id),
            "map_mode": "reuse_exact_existing_map_revision",
            "industry_map_id": str(industry_map.id),
            "industry_map_revision_id": str(map_revision.id),
            "candidate_owner_bindings": [
                {
                    "reviewed_candidate_revision_id": str(candidate_revision.id),
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
