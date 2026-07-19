from __future__ import annotations

import os
from datetime import date, datetime, timezone

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from sqlalchemy import MetaData, Table, create_engine, inspect, insert, select
from sqlalchemy.engine import make_url

from backend.database.series import build_snapshot_series_identity


def _postgres_url() -> str:
    database_url = os.getenv("TEST_DATABASE_URL", "").strip()
    if not database_url:
        pytest.skip("TEST_DATABASE_URL is not configured")
    if "test" not in (make_url(database_url).database or "").lower():
        pytest.fail("TEST_DATABASE_URL must target a database whose name contains 'test'.")
    return database_url


def test_sector_migration_preserves_existing_runs_and_round_trips() -> None:
    database_url = _postgres_url()
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", database_url)
    command.downgrade(config, "base")
    command.upgrade(config, "20260718_0003")
    engine = create_engine(database_url)
    identity = build_snapshot_series_identity(
        provider="fixture",
        dataset="market_data_bundle",
        contract_version="1.0",
        datasets=["daily_price", "stock_basic", "trade_calendar"],
        stock_codes=["000001"],
        requested_start_date="20260709",
        requested_end_date="20260709",
        adjust_type="qfq",
    )
    try:
        runs = Table("ingestion_runs", MetaData(), autoload_with=engine)
        with engine.begin() as connection:
            run_id = connection.execute(insert(runs).values(
                batch_identifier="c" * 64,
                series_key=identity.series_key,
                series_identity=identity.canonical,
                provider="fixture",
                dataset="market_data_bundle",
                imported_at=datetime(2026, 7, 18, tzinfo=timezone.utc),
                completed_at=datetime(2026, 7, 18, tzinfo=timezone.utc),
                requested_start_date=date(2026, 7, 9),
                requested_end_date=date(2026, 7, 9),
                information_cutoff_date=date(2026, 7, 9),
                requested_scope={"datasets": ["daily_price"], "stock_codes": ["000001"]},
                provider_request_metadata={"network_access": False},
                adapter_version="fixture",
                snapshot_mode="complete",
                contract_version="1.0",
                status="succeeded",
                row_count_received=0,
                row_count_written=0,
                dataset_counts={},
            ).returning(runs.c.id)).scalar_one()
        engine.dispose()

        command.upgrade(config, "head")
        engine = create_engine(database_url)
        assert {"sector_definition", "sector_daily"}.issubset(inspect(engine).get_table_names())
        with engine.connect() as connection:
            current_runs = Table("ingestion_runs", MetaData(), autoload_with=engine)
            assert connection.scalar(select(sa.func.count()).select_from(current_runs)) == 1
            assert connection.scalar(sa.text("SELECT version_num FROM alembic_version")) == "20260719_0010"
        engine.dispose()

        command.downgrade(config, "20260718_0003")
        engine = create_engine(database_url)
        assert "sector_definition" not in inspect(engine).get_table_names()
        assert "sector_daily" not in inspect(engine).get_table_names()
        runs_after = Table("ingestion_runs", MetaData(), autoload_with=engine)
        with engine.connect() as connection:
            assert connection.scalar(select(sa.func.count()).select_from(runs_after)) == 1
            assert connection.scalar(select(runs_after.c.id)) == run_id
        engine.dispose()

        command.upgrade(config, "head")
        engine = create_engine(database_url)
        assert {"sector_definition", "sector_daily"}.issubset(inspect(engine).get_table_names())
    finally:
        engine.dispose()
        command.downgrade(config, "base")
