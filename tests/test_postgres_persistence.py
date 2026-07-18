from __future__ import annotations

import os
from collections.abc import Iterator

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import inspect, select
from sqlalchemy.engine import make_url
from sqlalchemy.exc import IntegrityError

from backend.database.engine import build_engine, build_session_factory
from backend.database.market_data import MarketDataPersistenceService, MarketDataRepository
from backend.database.models import IngestionRun, StockBasicRecord
from datasource.fixtures import (
    FIXTURE_CUTOFF_DATE,
    FIXTURE_END_DATE,
    FIXTURE_PROVIDER,
    FIXTURE_SCOPE,
    FIXTURE_START_DATE,
    build_market_data_fixture,
)


@pytest.fixture(scope="module")
def postgres_database_url() -> Iterator[str]:
    database_url = os.getenv("TEST_DATABASE_URL", "").strip()
    if not database_url:
        pytest.skip("TEST_DATABASE_URL is not configured")
    database_name = make_url(database_url).database or ""
    if "test" not in database_name.lower():
        pytest.fail("TEST_DATABASE_URL must target a database whose name contains 'test'.")

    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", database_url)
    command.downgrade(config, "base")
    command.upgrade(config, "head")
    yield database_url
    command.downgrade(config, "base")


def test_clean_postgres_migration_creates_expected_tables(postgres_database_url: str) -> None:
    engine = build_engine(postgres_database_url)
    try:
        tables = set(inspect(engine).get_table_names())
    finally:
        engine.dispose()
    assert {"alembic_version", "ingestion_runs", "stock_basic", "daily_price", "trade_calendar"} <= tables


def test_postgres_fixture_import_constraints_and_idempotency(postgres_database_url: str) -> None:
    engine = build_engine(postgres_database_url)
    session_factory = build_session_factory(engine)
    service = MarketDataPersistenceService(session_factory)
    try:
        first = service.ingest_bundle(
            build_market_data_fixture(),
            provider=FIXTURE_PROVIDER,
            requested_start_date=FIXTURE_START_DATE,
            requested_end_date=FIXTURE_END_DATE,
            information_cutoff_date=FIXTURE_CUTOFF_DATE,
            requested_scope=FIXTURE_SCOPE,
        )
        second = service.ingest_bundle(
            build_market_data_fixture(),
            provider=FIXTURE_PROVIDER,
            requested_start_date=FIXTURE_START_DATE,
            requested_end_date=FIXTURE_END_DATE,
            information_cutoff_date=FIXTURE_CUTOFF_DATE,
            requested_scope=FIXTURE_SCOPE,
        )
        assert first.rows_written == 8
        assert second.rows_written == 0
        assert second.ingestion_run_id == first.ingestion_run_id

        with session_factory() as session:
            assert len(MarketDataRepository(session).read_daily_price(FIXTURE_PROVIDER)) == 4
            run = session.get(IngestionRun, first.ingestion_run_id)
            assert run is not None
            duplicate = StockBasicRecord(
                ingestion_run_id=run.id,
                stock_code="000001",
                stock_name="Duplicate",
                exchange="SZ",
                industry="Banking",
                listing_date=None,
                status="active",
                source=FIXTURE_PROVIDER,
            )
            session.add(duplicate)
            with pytest.raises(IntegrityError):
                session.commit()
            session.rollback()

            invalid_foreign_key = StockBasicRecord(
                ingestion_run_id=999999999,
                stock_code="000002",
                stock_name="Invalid provenance",
                exchange="SZ",
                industry="Banking",
                listing_date=None,
                status="active",
                source=FIXTURE_PROVIDER,
            )
            session.add(invalid_foreign_key)
            with pytest.raises(IntegrityError):
                session.commit()
            session.rollback()
            assert session.scalar(select(IngestionRun.id).where(IngestionRun.id == first.ingestion_run_id))
    finally:
        engine.dispose()
