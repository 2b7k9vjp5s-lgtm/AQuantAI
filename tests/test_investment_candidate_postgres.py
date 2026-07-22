from __future__ import annotations

from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timezone
import os
from uuid import UUID

from alembic import command
from alembic.config import Config
import pytest
from sqlalchemy import func, inspect, select, text
from sqlalchemy.engine import make_url

from backend.database import build_engine, build_session_factory
from industry_alpha.investment_candidate_commands import InvestmentCandidateCommandService
from industry_alpha.investment_candidate_models import (
    INVESTMENT_CANDIDATE_MODELS,
    InvestmentCandidateComponentAssessment,
    InvestmentCandidateComponentRevision,
)
from industry_alpha.investment_candidate_rules import InvestmentCandidateError
from industry_alpha.stage2_expectations_fixtures import (
    build_stage2_expectation_valuation_fixture,
)
from industry_alpha.stage2_models import (
    Stage2CompanyResearch,
    Stage2CompanyResearchRevision,
)

UTC = timezone.utc
EXPECTED_TABLES = {model.__tablename__ for model in INVESTMENT_CANDIDATE_MODELS}


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
def clean_investment_candidate(postgres_database_url: str) -> Iterator[None]:
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


def _config(database_url: str) -> Config:
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", database_url)
    return config


def _component_input(factory) -> dict:
    fixture = build_stage2_expectation_valuation_fixture(factory)
    with factory() as session:
        research = session.get(
            Stage2CompanyResearch, fixture.stage2.supported_research_id
        )
        revision = session.scalars(
            select(Stage2CompanyResearchRevision)
            .where(Stage2CompanyResearchRevision.company_research_id == research.id)
            .order_by(Stage2CompanyResearchRevision.revision_no.desc())
        ).first()
    return {
        "assessment_key": "postgres-concurrent-industry-opportunity",
        "beneficiary_id": str(research.beneficiary_id),
        "beneficiary_revision_id": str(research.beneficiary_revision_id),
        "company_research_revision_id": str(revision.id),
        "component_code": "industry_opportunity",
        "assessment_state": "missing",
        "verification_state": "verified",
        "verification_material": False,
        "verification_item_code": None,
        "verification_question": None,
        "score_text": None,
        "missing_reason": "No accepted component assessment exists at this boundary.",
        "rationale": "The missing state is explicit and must not be imputed.",
        "falsification_condition": "A later accepted component revision may replace this missing state.",
        "falsification_state": "inactive",
        "information_cutoff_date": date(2026, 7, 22).isoformat(),
        "recorded_at_utc": datetime(2026, 7, 22, 18, tzinfo=UTC).isoformat(),
        "recorded_by": "postgres-test",
        "expected_latest_revision_id": None,
        "inputs": [],
    }


def test_postgres_0013_to_0014_and_empty_round_trip(
    postgres_database_url: str,
) -> None:
    config = _config(postgres_database_url)
    engine = build_engine(postgres_database_url)
    try:
        command.downgrade(config, "20260722_0013")
        assert EXPECTED_TABLES.isdisjoint(inspect(engine).get_table_names())
        command.upgrade(config, "head")
        assert EXPECTED_TABLES.issubset(inspect(engine).get_table_names())
        with engine.connect() as connection:
            assert (
                connection.scalar(text("SELECT version_num FROM alembic_version"))
                == "20260722_0015"
            )
        command.downgrade(config, "20260722_0013")
        assert EXPECTED_TABLES.isdisjoint(inspect(engine).get_table_names())
        command.upgrade(config, "head")
    finally:
        engine.dispose()


def test_postgres_populated_downgrade_refuses_before_any_drop(
    postgres_database_url: str,
) -> None:
    config = _config(postgres_database_url)
    engine = build_engine(postgres_database_url)
    factory = build_session_factory(engine)
    try:
        payload = _component_input(factory)
        InvestmentCandidateCommandService(factory).record_component(payload)
        with pytest.raises(RuntimeError, match="Cannot downgrade Investment Candidate"):
            command.downgrade(config, "20260722_0013")
        assert EXPECTED_TABLES.issubset(inspect(engine).get_table_names())
        with engine.connect() as connection:
            assert (
                connection.scalar(text("SELECT version_num FROM alembic_version"))
                == "20260722_0015"
            )
    finally:
        engine.dispose()


def test_postgres_concurrent_first_component_revision_fails_closed(
    postgres_database_url: str,
) -> None:
    engine = build_engine(postgres_database_url)
    factory = build_session_factory(engine)
    payload = _component_input(factory)

    def record(_: int):
        try:
            return InvestmentCandidateCommandService(factory).record_component(payload)
        except InvestmentCandidateError as exc:
            return exc.code

    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(record, (1, 2)))
        assert sum(isinstance(item, dict) for item in results) == 1
        assert "investment_candidate_revision_conflict" in results
        with factory() as session:
            assert session.scalar(
                select(func.count()).select_from(
                    InvestmentCandidateComponentAssessment
                )
            ) == 1
            assert session.scalar(
                select(func.count()).select_from(
                    InvestmentCandidateComponentRevision
                )
            ) == 1
            revision = session.scalar(select(InvestmentCandidateComponentRevision))
            assert revision.beneficiary_revision_id == UUID(
                payload["beneficiary_revision_id"]
            )
    finally:
        engine.dispose()
