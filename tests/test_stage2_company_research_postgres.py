from __future__ import annotations

import os
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timezone

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import inspect, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import IntegrityError

from backend.database.engine import build_engine, build_session_factory
from industry_alpha.errors import EvidenceLedgerImmutableError
from industry_alpha.stage2_commands import Stage2CompanyResearchCommandService
from industry_alpha.stage2_fixtures import build_stage2_company_research_fixture
from industry_alpha.stage2_models import (
    Stage2CompanyResearch,
    Stage2CompanyResearchRevision,
    Stage2FinancialHypothesisRevision,
    Stage2ResearchHypothesisLink,
)


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
def clean_stage2(postgres_database_url: str) -> Iterator[None]:
    engine = build_engine(postgres_database_url)
    try:
        with engine.begin() as connection:
            connection.execute(text("TRUNCATE research_cases, ingestion_runs CASCADE"))
        yield
    finally:
        engine.dispose()


def utc(day: int, hour: int = 10) -> datetime:
    return datetime(2026, 7, day, hour, tzinfo=timezone.utc)


def test_stage2_migration_from_v05c_and_round_trip(postgres_database_url: str):
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", postgres_database_url)
    engine = build_engine(postgres_database_url)
    try:
        assert "stage2_company_research" in inspect(engine).get_table_names()
        command.downgrade(config, "20260719_0007")
        tables = inspect(engine).get_table_names()
        assert "stage2_company_research" not in tables
        assert "stage1_candidate_pool_memberships" in tables
        command.upgrade(config, "head")
        assert "stage2_verification_items" in inspect(engine).get_table_names()
        with engine.connect() as connection:
            assert connection.scalar(text("SELECT version_num FROM alembic_version")) == "20260719_0008"
    finally:
        engine.dispose()


def test_postgres_concurrent_research_revision_numbers(postgres_database_url: str):
    engine = build_engine(postgres_database_url)
    factory = build_session_factory(engine)
    fixture = build_stage2_company_research_fixture(factory)

    def append(index: int):
        return Stage2CompanyResearchCommandService(factory).append_research_revision(
            fixture.draft_research_id,
            workflow_state="open",
            conclusion_status="insufficient_evidence",
            research_question=f"Concurrent research revision {index}?",
            summary="Still incomplete.",
            information_cutoff_date=date(2026, 7, 16),
            recorded_at_utc=utc(16),
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(append, (1, 2)))
    assert sorted(item.revision_no for item in results) == [2, 3]
    engine.dispose()


def test_postgres_concurrent_hypothesis_revision_numbers(postgres_database_url: str):
    engine = build_engine(postgres_database_url)
    factory = build_session_factory(engine)
    fixture = build_stage2_company_research_fixture(factory)
    with factory() as session:
        prior = session.scalar(
            select(Stage2FinancialHypothesisRevision)
            .where(
                Stage2FinancialHypothesisRevision.hypothesis_id
                == fixture.supported_hypothesis_id
            )
            .order_by(Stage2FinancialHypothesisRevision.revision_no.desc())
        )
        from industry_alpha.stage2_models import Stage2HypothesisClaimLink

        claims = tuple(
            session.scalars(
                select(Stage2HypothesisClaimLink.claim_revision_id).where(
                    Stage2HypothesisClaimLink.hypothesis_revision_id == prior.id
                )
            )
        )

    def append(index: int):
        return Stage2CompanyResearchCommandService(factory).append_hypothesis_revision(
            fixture.supported_hypothesis_id,
            hypothesis_status="supported",
            mechanism=f"Concurrent bounded mechanism {index}.",
            direction="positive",
            operating_metric="shipped units",
            financial_statement_line="revenue",
            expected_lag_horizon="two reporting periods",
            confidence="medium",
            basis="The exact frozen A-grade claim remains the bounded basis.",
            information_cutoff_date=date(2026, 7, 16),
            claim_revision_ids=claims,
            recorded_at_utc=utc(16),
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(append, (1, 2)))
    assert sorted(item.revision_no for item in results) == [3, 4]
    engine.dispose()


def test_postgres_append_only_guard(postgres_database_url: str):
    engine = build_engine(postgres_database_url)
    factory = build_session_factory(engine)
    fixture = build_stage2_company_research_fixture(factory)
    with factory() as session:
        row = session.get(Stage2CompanyResearch, fixture.supported_research_id)
        row.stock_code = "999999"
        with pytest.raises(EvidenceLedgerImmutableError):
            session.flush()
    with factory() as session:
        revision = session.scalar(select(Stage2CompanyResearchRevision))
        session.delete(revision)
        with pytest.raises(EvidenceLedgerImmutableError):
            session.flush()
    engine.dispose()


def test_postgres_exact_hypothesis_revision_fk(postgres_database_url: str):
    engine = build_engine(postgres_database_url)
    factory = build_session_factory(engine)
    fixture = build_stage2_company_research_fixture(factory)
    with factory() as session:
        research_revision = session.scalar(
            select(Stage2CompanyResearchRevision).where(
                Stage2CompanyResearchRevision.company_research_id
                == fixture.draft_research_id,
                Stage2CompanyResearchRevision.revision_no == 1,
            )
        )
        supported_revision = session.scalar(
            select(Stage2FinancialHypothesisRevision).where(
                Stage2FinancialHypothesisRevision.hypothesis_id
                == fixture.supported_hypothesis_id,
                Stage2FinancialHypothesisRevision.revision_no == 1,
            )
        )
        session.add(
            Stage2ResearchHypothesisLink(
                company_research_revision_id=research_revision.id,
                hypothesis_id=fixture.draft_hypothesis_id,
                hypothesis_revision_id=supported_revision.id,
                recorded_at_utc=utc(16),
            )
        )
        with pytest.raises(IntegrityError):
            session.flush()
    engine.dispose()
