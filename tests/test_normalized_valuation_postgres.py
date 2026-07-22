from __future__ import annotations

from collections.abc import Iterator
import os
from uuid import uuid4

from alembic import command
from alembic.config import Config
import pytest
from sqlalchemy import inspect, text
from sqlalchemy.engine import make_url

from backend.database import build_engine
from industry_alpha.normalized_valuation_models import NORMALIZED_VALUATION_MODELS


EXPECTED_TABLES = {model.__tablename__ for model in NORMALIZED_VALUATION_MODELS}


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
def clean_normalized_valuation(postgres_database_url: str) -> Iterator[None]:
    engine = build_engine(postgres_database_url)
    try:
        with engine.begin() as connection:
            connection.execute(
                text(
                    "TRUNCATE structured_financial_observations, "
                    "normalized_valuation_metrics, valuation_comparison_sets, "
                    "normalized_expectation_gaps RESTART IDENTITY CASCADE"
                )
            )
        yield
    finally:
        with engine.begin() as connection:
            connection.execute(
                text(
                    "TRUNCATE structured_financial_observations, "
                    "normalized_valuation_metrics, valuation_comparison_sets, "
                    "normalized_expectation_gaps RESTART IDENTITY CASCADE"
                )
            )
        engine.dispose()


def _config(database_url: str) -> Config:
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", database_url)
    return config


def test_postgres_0014_to_0015_and_empty_round_trip(
    postgres_database_url: str,
) -> None:
    config = _config(postgres_database_url)
    engine = build_engine(postgres_database_url)
    try:
        command.downgrade(config, "20260722_0014")
        assert EXPECTED_TABLES.isdisjoint(inspect(engine).get_table_names())
        command.upgrade(config, "head")
        assert EXPECTED_TABLES.issubset(inspect(engine).get_table_names())
        with engine.connect() as connection:
            assert connection.scalar(
                text("SELECT version_num FROM alembic_version")
            ) == "20260722_0015"
        command.downgrade(config, "20260722_0014")
        assert EXPECTED_TABLES.isdisjoint(inspect(engine).get_table_names())
        command.upgrade(config, "head")
    finally:
        engine.dispose()


def test_postgres_populated_downgrade_refuses_before_any_drop(
    postgres_database_url: str,
) -> None:
    config = _config(postgres_database_url)
    engine = build_engine(postgres_database_url)
    try:
        with engine.begin() as connection:
            connection.execute(text("SET session_replication_role = 'replica'"))
            try:
                connection.execute(
                    text(
                        "INSERT INTO structured_financial_observations "
                        "(id, observation_key, company_research_id, instrument_id, metric_code, "
                        "source_kind, target_period_key, accounting_scope, currency_code, unit_code, "
                        "created_at_utc) VALUES "
                        "(:id, 'postgres-migration-test', :research, :instrument, 'revenue', "
                        "'actual', 'TTM-2026-06-30', 'consolidated', 'CNY', "
                        "'currency_amount', '2026-07-22 10:00:00+00')"
                    ),
                    {
                        "id": str(uuid4()),
                        "research": str(uuid4()),
                        "instrument": str(uuid4()),
                    },
                )
            finally:
                connection.execute(text("SET session_replication_role = 'origin'"))
        with pytest.raises(RuntimeError, match="Cannot downgrade Normalized Valuation"):
            command.downgrade(config, "20260722_0014")
        assert EXPECTED_TABLES.issubset(inspect(engine).get_table_names())
        with engine.connect() as connection:
            assert connection.scalar(
                text("SELECT version_num FROM alembic_version")
            ) == "20260722_0015"
    finally:
        engine.dispose()
