from __future__ import annotations

import os
from collections.abc import Iterator

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import inspect, select, text
from sqlalchemy.engine import make_url

from backend.database.engine import build_engine, build_session_factory
from industry_alpha.errors import EvidenceLedgerImmutableError
from industry_alpha.stage2_assessments_models import Stage2CatalystAssessment
from industry_alpha.stage2_expectations_models import Stage2MarketExpectation
from industry_alpha.stage2_judgments_fixtures import build_stage2_judgment_fixture
from industry_alpha.stage2_judgments_models import Stage2IndustryJudgment
from industry_alpha.stage2_models import Stage2CompanyResearch


MUTATION_CASES = (
    (Stage2CompanyResearch, "stock_code", "999999"),
    (Stage2MarketExpectation, "expectation_key", "postgres-contract-expectation"),
    (Stage2CatalystAssessment, "catalyst_key", "postgres-contract-catalyst"),
    (Stage2IndustryJudgment, "judgment_key", "postgres-contract-judgment"),
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


def _first_row(session, model: type):
    row = session.scalars(select(model).order_by(model.id)).first()
    assert row is not None, model.__name__
    return row


def test_postgres_stage2_append_only_matrix(postgres_database_url: str):
    engine = build_engine(postgres_database_url)
    factory = build_session_factory(engine)
    try:
        build_stage2_judgment_fixture(factory)

        for model, field, replacement in MUTATION_CASES:
            with factory() as session:
                row = _first_row(session, model)
                identity = inspect(row).identity[0]
                original_value = getattr(row, field)
                setattr(row, field, replacement)
                expected_message = (
                    f"{model.__name__} rows are append-only and cannot be updated."
                )
                with pytest.raises(EvidenceLedgerImmutableError) as captured:
                    session.flush()
                assert type(captured.value) is EvidenceLedgerImmutableError
                assert str(captured.value) == expected_message
                session.rollback()

            with factory() as session:
                restored = session.get(model, identity)
                assert restored is not None
                assert getattr(restored, field) == original_value
                session.delete(restored)
                expected_message = (
                    f"{model.__name__} rows are append-only and cannot be deleted."
                )
                with pytest.raises(EvidenceLedgerImmutableError) as captured:
                    session.flush()
                assert type(captured.value) is EvidenceLedgerImmutableError
                assert str(captured.value) == expected_message
                session.rollback()

            with factory() as session:
                restored = session.get(model, identity)
                assert restored is not None
                assert getattr(restored, field) == original_value
    finally:
        engine.dispose()
