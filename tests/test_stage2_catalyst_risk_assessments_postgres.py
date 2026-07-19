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
from industry_alpha.stage2_assessments_commands import Stage2AssessmentCommandService
from industry_alpha.stage2_assessments_fixtures import build_stage2_assessment_fixture
from industry_alpha.stage2_assessments_models import (
    Stage2CatalystAssessmentRevision, Stage2CatalystClaimLink,
    Stage2CatalystExpectationLink, Stage2CatalystHypothesisLink,
    Stage2CatalystValuationLink, Stage2RiskAssessmentRevision,
    Stage2RiskClaimLink, Stage2RiskExpectationLink, Stage2RiskHypothesisLink,
    Stage2RiskValuationLink,
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
def clean_assessments(postgres_database_url: str) -> Iterator[None]:
    engine = build_engine(postgres_database_url)
    try:
        with engine.begin() as connection:
            connection.execute(text("TRUNCATE research_cases, ingestion_runs CASCADE"))
        yield
    finally:
        engine.dispose()


def _inputs(factory, revision_id):
    with factory() as session:
        revision = session.get(Stage2CatalystAssessmentRevision, revision_id)
        hypothesis = session.scalar(select(Stage2CatalystHypothesisLink.hypothesis_revision_id).where(Stage2CatalystHypothesisLink.catalyst_revision_id == revision.id))
        expectation = session.scalar(select(Stage2CatalystExpectationLink.expectation_revision_id).where(Stage2CatalystExpectationLink.catalyst_revision_id == revision.id))
        valuation = session.scalar(select(Stage2CatalystValuationLink.valuation_revision_id).where(Stage2CatalystValuationLink.catalyst_revision_id == revision.id))
        claim = session.scalar(select(Stage2CatalystClaimLink.claim_revision_id).where(Stage2CatalystClaimLink.catalyst_revision_id == revision.id))
    return revision.company_research_revision_id, hypothesis, expectation, valuation, claim


def test_postgres_v06c_migration_round_trip(postgres_database_url: str):
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", postgres_database_url)
    engine = build_engine(postgres_database_url)
    try:
        assert "stage2_catalyst_assessments" in inspect(engine).get_table_names()
        command.downgrade(config, "20260719_0009")
        assert "stage2_catalyst_assessments" not in inspect(engine).get_table_names()
        assert "stage2_valuation_snapshots" in inspect(engine).get_table_names()
        command.upgrade(config, "20260719_0010")
        with engine.connect() as connection:
            assert connection.scalar(text("SELECT version_num FROM alembic_version")) == "20260719_0010"
    finally:
        engine.dispose()


def test_postgres_concurrent_catalyst_revision_numbers(postgres_database_url: str):
    engine = build_engine(postgres_database_url)
    factory = build_session_factory(engine)
    fixture = build_stage2_assessment_fixture(factory)
    research, hypothesis, expectation, valuation, claim = _inputs(factory, fixture.later_catalyst_revision_id)

    def append(index: int):
        return Stage2AssessmentCommandService(factory).append_catalyst_revision(
            fixture.supported_catalyst_id,
            company_research_revision_id=research,
            hypothesis_revision_ids=(hypothesis,), expectation_revision_ids=(expectation,),
            valuation_revision_ids=(valuation,), claim_revision_ids=(claim,),
            catalyst_category="demand", subject=f"Concurrent catalyst revision {index}",
            expected_observation_window="尚未获得可靠公开证据", status="disputed", confidence="low",
            trigger_observation_criteria="Primary evidence must resolve the contradiction.",
            basis="Concurrent append preserves one exact frozen boundary.", uncertainty="No outcome is fabricated.",
            information_cutoff_date=date(2026, 7, 20),
            recorded_at_utc=datetime(2026, 7, 20, 12, tzinfo=timezone.utc),
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(append, (1, 2)))
    assert sorted(item.revision_no for item in results) == [3, 4]
    with factory() as session:
        revisions = list(session.scalars(select(Stage2CatalystAssessmentRevision).where(Stage2CatalystAssessmentRevision.catalyst_id == fixture.supported_catalyst_id).order_by(Stage2CatalystAssessmentRevision.revision_no)))
    assert [item.revision_no for item in revisions] == [1, 2, 3, 4]
    assert revisions[-1].supersedes_revision_id == revisions[-2].id
    engine.dispose()


def test_postgres_concurrent_risk_revision_numbers(postgres_database_url: str):
    engine = build_engine(postgres_database_url)
    factory = build_session_factory(engine)
    fixture = build_stage2_assessment_fixture(factory)
    with factory() as session:
        revision = session.get(Stage2RiskAssessmentRevision, fixture.later_risk_revision_id)
        hypothesis = session.scalar(select(Stage2RiskHypothesisLink.hypothesis_revision_id).where(Stage2RiskHypothesisLink.risk_revision_id == revision.id))
        expectation = session.scalar(select(Stage2RiskExpectationLink.expectation_revision_id).where(Stage2RiskExpectationLink.risk_revision_id == revision.id))
        valuation = session.scalar(select(Stage2RiskValuationLink.valuation_revision_id).where(Stage2RiskValuationLink.risk_revision_id == revision.id))
        claim = session.scalar(select(Stage2RiskClaimLink.claim_revision_id).where(Stage2RiskClaimLink.risk_revision_id == revision.id))

    def append(index: int):
        return Stage2AssessmentCommandService(factory).append_risk_revision(
            fixture.supported_risk_id,
            company_research_revision_id=revision.company_research_revision_id,
            hypothesis_revision_ids=(hypothesis,), expectation_revision_ids=(expectation,),
            valuation_revision_ids=(valuation,), claim_revision_ids=(claim,),
            risk_category="execution", subject=f"Concurrent risk revision {index}",
            downside_path="The bounded mechanism may fail to reach reported revenue.",
            thesis_invalidation_condition="Primary attributable evidence resolves the mechanism against the thesis.",
            mitigants="尚未获得可靠公开证据", status="disputed", confidence="low",
            basis="Concurrent append preserves one exact disputed boundary.",
            uncertainty="No loss estimate or recommendation is produced.",
            information_cutoff_date=date(2026, 7, 20),
            recorded_at_utc=datetime(2026, 7, 20, 13, tzinfo=timezone.utc),
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(append, (1, 2)))
    assert sorted(item.revision_no for item in results) == [3, 4]
    with factory() as session:
        revisions = list(session.scalars(select(Stage2RiskAssessmentRevision).where(Stage2RiskAssessmentRevision.risk_id == fixture.supported_risk_id).order_by(Stage2RiskAssessmentRevision.revision_no)))
    assert [item.revision_no for item in revisions] == [1, 2, 3, 4]
    engine.dispose()


def test_postgres_fixture_semantics_repeat_on_clean_database(postgres_database_url: str):
    engine = build_engine(postgres_database_url)
    factory = build_session_factory(engine)
    results = []
    try:
        for _ in range(2):
            with engine.begin() as connection:
                connection.execute(text("TRUNCATE research_cases, ingestion_runs CASCADE"))
            fixture = build_stage2_assessment_fixture(factory)
            with factory() as session:
                rows = list(session.scalars(select(Stage2CatalystAssessmentRevision).where(Stage2CatalystAssessmentRevision.catalyst_id == fixture.supported_catalyst_id).order_by(Stage2CatalystAssessmentRevision.revision_no)))
            results.append(([item.revision_no for item in rows], rows[1].supersedes_revision_id == rows[0].id))
    finally:
        engine.dispose()
    assert results == [([1, 2], True), ([1, 2], True)]
