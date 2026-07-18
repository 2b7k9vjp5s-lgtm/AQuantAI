from __future__ import annotations

import os
from datetime import date, datetime, timezone

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import MetaData, Table, create_engine, inspect, insert, select
from sqlalchemy.engine import make_url

from backend.database.series import build_snapshot_series_identity


def _postgres_url() -> str:
    database_url = os.getenv("TEST_DATABASE_URL", "").strip()
    if not database_url:
        pytest.skip("TEST_DATABASE_URL is not configured")
    database_name = make_url(database_url).database or ""
    if "test" not in database_name.lower():
        pytest.fail("TEST_DATABASE_URL must target a database whose name contains 'test'.")
    return database_url


def test_upgrade_from_v03a_backfills_deterministic_snapshot_series_identity() -> None:
    database_url = _postgres_url()
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", database_url)
    command.downgrade(config, "base")
    command.upgrade(config, "20260718_0001")
    engine = create_engine(database_url)
    try:
        assert "series_key" not in {column["name"] for column in inspect(engine).get_columns("ingestion_runs")}
        metadata = MetaData()
        runs = Table("ingestion_runs", metadata, autoload_with=engine)
        daily_price = Table("daily_price", metadata, autoload_with=engine)
        with engine.begin() as connection:
            run_id = connection.execute(
                insert(runs)
                .values(
                    batch_identifier="a" * 64,
                    provider="fixture",
                    dataset="market_data_bundle",
                    imported_at=datetime(2026, 7, 18, tzinfo=timezone.utc),
                    completed_at=datetime(2026, 7, 18, tzinfo=timezone.utc),
                    requested_start_date=date(2026, 7, 9),
                    requested_end_date=date(2026, 7, 9),
                    information_cutoff_date=date(2026, 7, 9),
                    requested_scope={
                        "datasets": ["daily_price", "stock_basic", "trade_calendar"],
                        "stock_codes": ["000001"],
                        "stock_code_semantics": "exact",
                        "snapshot_mode": "complete",
                    },
                    snapshot_mode="complete",
                    contract_version="1.0",
                    status="succeeded",
                    row_count_received=1,
                    row_count_written=1,
                    dataset_counts={"stock_basic": 0, "daily_price": 1, "trade_calendar": 0},
                )
                .returning(runs.c.id)
            ).scalar_one()
            connection.execute(
                insert(daily_price).values(
                    ingestion_run_id=run_id,
                    trade_date=date(2026, 7, 9),
                    stock_code="000001",
                    open=10.0,
                    high=10.8,
                    low=9.9,
                    close=10.5,
                    volume=1000.0,
                    amount=10500.0,
                    adjust_type="qfq",
                    source="fixture",
                )
            )
        engine.dispose()

        command.upgrade(config, "head")
        engine = create_engine(database_url)
        columns = {column["name"] for column in inspect(engine).get_columns("ingestion_runs")}
        assert {"series_key", "series_identity", "provider_request_metadata", "adapter_version"} <= columns
        expected = build_snapshot_series_identity(
            provider="fixture",
            dataset="market_data_bundle",
            contract_version="1.0",
            datasets=["daily_price", "stock_basic", "trade_calendar"],
            stock_codes=["000001"],
            requested_start_date="20260709",
            requested_end_date="20260709",
            adjust_type="qfq",
        )
        metadata = MetaData()
        upgraded_runs = Table("ingestion_runs", metadata, autoload_with=engine)
        with engine.connect() as connection:
            row = connection.execute(select(upgraded_runs)).mappings().one()
        assert row["series_key"] == expected.series_key
        assert row["series_identity"] == expected.canonical
        assert row["adapter_version"] == "v0.3a-backfill"
        assert row["provider_request_metadata"] == {
            "migration_backfill": "20260718_0002",
            "network_access": False,
        }
        indexes = {index["name"]: index for index in inspect(engine).get_indexes("ingestion_runs")}
        assert "ix_ingestion_runs_series_cutoff" in indexes
        assert indexes["uq_ingestion_runs_successful_batch"]["column_names"] == [
            "batch_identifier",
            "series_key",
        ]
    finally:
        engine.dispose()
        command.downgrade(config, "base")
