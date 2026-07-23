from __future__ import annotations

from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone
import os
from uuid import UUID

from alembic import command
from alembic.config import Config
import pytest
from sqlalchemy import func, select, text
from sqlalchemy.engine import make_url

from backend.database import build_engine, build_session_factory
from industry_alpha.industry_thesis_commands import IndustryThesisCommandService
from industry_alpha.industry_thesis_models import (
    IndustryThesisCandidateIdentity,
    IndustryThesisCandidateRevision,
    IndustryThesisSessionIdentity,
    IndustryThesisSessionRevision,
)
from industry_alpha.industry_thesis_review import (
    ACCEPTANCE_PLAN_VERSION,
    IndustryThesisProposalReviewService,
)
from industry_alpha.industry_thesis_rules import BUILDER_VERSION, IndustryThesisError

UTC = timezone.utc
BASE_TIME = datetime(2026, 7, 22, 23, 30, tzinfo=UTC)


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
    engine = build_engine(database_url)
    try:
        with engine.begin() as connection:
            connection.execute(
                text("TRUNCATE industry_thesis_session_identities CASCADE")
            )
    finally:
        engine.dispose()
    command.downgrade(config, "base")


@pytest.fixture(autouse=True)
def clean_industry_thesis(postgres_database_url: str) -> Iterator[None]:
    engine = build_engine(postgres_database_url)
    try:
        with engine.begin() as connection:
            connection.execute(
                text("TRUNCATE industry_thesis_session_identities CASCADE")
            )
        yield
    finally:
        with engine.begin() as connection:
            connection.execute(
                text("TRUNCATE industry_thesis_session_identities CASCADE")
            )
        engine.dispose()


def _session_input() -> dict:
    return {
        "thesis_text_original": "PostgreSQL proposal review concurrency",
        "thesis_title_reviewed": "PostgreSQL review",
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
        "information_cutoff_date": date(2026, 7, 22).isoformat(),
        "revision_note": "PostgreSQL review fixture",
    }


def test_postgres_concurrent_proposal_review_is_expected_latest_protected(
    postgres_database_url: str,
) -> None:
    engine = build_engine(postgres_database_url)
    factory = build_session_factory(engine)
    try:
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
                "allowed_source_kinds": ["user_seed"],
                "proposals": [
                    {
                        "source_kind": "user_seed",
                        "source_reference": {"seed_key": "postgres-unresolved"},
                        "company_label_original": "PostgreSQL Candidate",
                        "benefit_path_text": "Explicit offline candidate for concurrency.",
                        "proposed_exposure_type": "unknown",
                        "proposal_confidence": "low",
                        "identity_state": "unresolved_identity",
                        "review_state": "proposed",
                        "rationale": {"reason": "concurrency fixture"},
                        "uncertainty": {"state": "identity_pending"},
                    }
                ],
            }
        )
        candidate_revision_id = built["candidates"][0]["candidate_revision_id"]
        review_input = {
            "session_revision_id": created["session_revision_id"],
            "expected_session_latest_revision_number": 1,
            "acceptance_plan_version": ACCEPTANCE_PLAN_VERSION,
            "decisions": [
                {
                    "candidate_revision_id": candidate_revision_id,
                    "expected_latest_revision_number": 1,
                    "decision": "unresolved",
                    "rationale": {"reason": "still unresolved"},
                    "uncertainty": {"state": "identity_pending"},
                }
            ],
            "revision_note": "concurrent PostgreSQL review",
        }

        def review(index: int):
            service = IndustryThesisProposalReviewService(
                factory,
                clock=lambda: BASE_TIME + timedelta(seconds=2 + index),
            )
            try:
                return service.review_candidates(review_input)
            except IndustryThesisError as exc:
                return exc.code

        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(review, (0, 1)))

        assert sum(isinstance(item, dict) for item in results) == 1
        assert "industry_thesis_revision_conflict" in results
        with factory() as session:
            session_identity = session.get(
                IndustryThesisSessionIdentity,
                UUID(created["session_id"]),
            )
            assert session_identity.latest_revision_number == 2
            candidate_identity = session.scalar(
                select(IndustryThesisCandidateIdentity)
            )
            assert candidate_identity.latest_revision_number == 2
            assert session.scalar(
                select(func.count()).select_from(IndustryThesisSessionRevision)
            ) == 2
            assert session.scalar(
                select(func.count()).select_from(IndustryThesisCandidateRevision)
            ) == 2
    finally:
        engine.dispose()
