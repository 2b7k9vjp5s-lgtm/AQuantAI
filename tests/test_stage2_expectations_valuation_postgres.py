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

from backend.database.engine import build_engine, build_session_factory
from industry_alpha.stage2_expectations_commands import Stage2ExpectationCommandService
from industry_alpha.stage2_expectations_fixtures import (
    build_stage2_expectation_valuation_fixture,
)
from industry_alpha.stage2_expectations_models import (
    Stage2MarketExpectationRevision,
    Stage2ValuationSnapshotRevision,
)
from industry_alpha.stage2_models import (
    Stage2CompanyResearchRevision,
    Stage2HypothesisClaimLink,
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
def clean_stage2_expectations(postgres_database_url: str) -> Iterator[None]:
    engine = build_engine(postgres_database_url)
    try:
        with engine.begin() as connection:
            connection.execute(text("TRUNCATE research_cases, ingestion_runs CASCADE"))
        yield
    finally:
        engine.dispose()


def utc(day: int, hour: int = 10) -> datetime:
    return datetime(2026, 7, day, hour, tzinfo=timezone.utc)


def inputs(factory, research_id):
    with factory() as session:
        research_revision = session.scalar(
            select(Stage2CompanyResearchRevision)
            .where(Stage2CompanyResearchRevision.company_research_id == research_id)
            .order_by(Stage2CompanyResearchRevision.revision_no.desc())
        )
        hypothesis_revision_id = session.scalar(
            select(Stage2ResearchHypothesisLink.hypothesis_revision_id).where(
                Stage2ResearchHypothesisLink.company_research_revision_id
                == research_revision.id
            )
        )
        claim_revision_id = session.scalar(
            select(Stage2HypothesisClaimLink.claim_revision_id).where(
                Stage2HypothesisClaimLink.hypothesis_revision_id == hypothesis_revision_id
            )
        )
    return research_revision.id, hypothesis_revision_id, claim_revision_id


def test_postgres_v06b_migration_from_v06a_and_round_trip(postgres_database_url: str):
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", postgres_database_url)
    engine = build_engine(postgres_database_url)
    try:
        assert "stage2_market_expectations" in inspect(engine).get_table_names()
        command.downgrade(config, "20260719_0008")
        tables = inspect(engine).get_table_names()
        assert "stage2_market_expectations" not in tables
        assert "stage2_company_research" in tables
        command.upgrade(config, "head")
        assert "stage2_valuation_snapshots" in inspect(engine).get_table_names()
        with engine.connect() as connection:
            assert connection.scalar(text("SELECT version_num FROM alembic_version")) == "20260719_0009"
    finally:
        engine.dispose()


def test_postgres_concurrent_expectation_revision_numbers(postgres_database_url: str):
    engine = build_engine(postgres_database_url)
    factory = build_session_factory(engine)
    fixture = build_stage2_expectation_valuation_fixture(factory)
    revision_id, hypothesis_revision_id, claim_revision_id = inputs(
        factory, fixture.stage2.supported_research_id
    )

    def append(index: int):
        return Stage2ExpectationCommandService(factory).append_expectation_revision(
            fixture.expectation_id,
            company_research_revision_id=revision_id,
            hypothesis_revision_ids=(hypothesis_revision_id,),
            claim_revision_ids=(claim_revision_id,),
            subject=f"Concurrent expectation revision {index}",
            period_horizon="future reporting period",
            expectation_kind="research_assumption",
            direction="positive",
            status="supported",
            confidence="medium",
            basis="Concurrent append keeps deterministic revision numbers.",
            information_cutoff_date=date(2026, 7, 17),
            recorded_at_utc=utc(17),
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(append, (1, 2)))
    assert sorted(item.revision_no for item in results) == [3, 4]
    with factory() as session:
        rows = list(
            session.scalars(
                select(Stage2MarketExpectationRevision)
                .where(
                    Stage2MarketExpectationRevision.expectation_id
                    == fixture.expectation_id
                )
                .order_by(Stage2MarketExpectationRevision.revision_no)
            )
        )
    assert [item.revision_no for item in rows] == [1, 2, 3, 4]
    engine.dispose()


def test_postgres_concurrent_valuation_revision_numbers(postgres_database_url: str):
    engine = build_engine(postgres_database_url)
    factory = build_session_factory(engine)
    fixture = build_stage2_expectation_valuation_fixture(factory)
    revision_id, hypothesis_revision_id, claim_revision_id = inputs(
        factory, fixture.stage2.supported_research_id
    )

    def append(index: int):
        return Stage2ExpectationCommandService(factory).append_valuation_revision(
            fixture.valuation_id,
            company_research_revision_id=revision_id,
            hypothesis_revision_ids=(hypothesis_revision_id,),
            claim_revision_ids=(claim_revision_id,),
            valuation_method="market_price_context",
            metric_context=f"Concurrent valuation observation {index}",
            observed_value="10.2",
            missing_data_reason=None,
            unit="close",
            currency="CNY",
            comparison_basis="Same fixture price context.",
            assumptions="No fair value, target price, or expected return is derived.",
            status="supported",
            confidence="low",
            information_cutoff_date=date(2026, 7, 17),
            daily_price_id=fixture.daily_price_id,
            recorded_at_utc=utc(17),
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(append, (1, 2)))
    assert sorted(item.revision_no for item in results) == [2, 3]
    with factory() as session:
        rows = list(
            session.scalars(
                select(Stage2ValuationSnapshotRevision)
                .where(Stage2ValuationSnapshotRevision.valuation_id == fixture.valuation_id)
                .order_by(Stage2ValuationSnapshotRevision.revision_no)
            )
        )
    assert [item.revision_no for item in rows] == [1, 2, 3]
    engine.dispose()
