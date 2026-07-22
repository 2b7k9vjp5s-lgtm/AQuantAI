from __future__ import annotations

from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
import os

from alembic import command
from alembic.config import Config
import pytest
from sqlalchemy import func, inspect, select, text
from sqlalchemy.engine import make_url

from backend.database import build_engine, build_session_factory
from backend.database.canonical_price import CanonicalPriceCommandService, CanonicalPriceError
from backend.database.canonical_price_models import ListedInstrument, ListedInstrumentRevision


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
def clean_canonical_price(postgres_database_url: str) -> Iterator[None]:
    engine = build_engine(postgres_database_url)
    try:
        with engine.begin() as connection:
            connection.execute(text("TRUNCATE listed_instruments CASCADE"))
        yield
    finally:
        with engine.begin() as connection:
            connection.execute(text("TRUNCATE listed_instruments CASCADE"))
        engine.dispose()


def _instrument_input() -> dict:
    return {
        "instrument_key": "postgres-concurrent-instrument",
        "expected_latest_revision_id": None,
        "canonical_symbol": "000001",
        "security_type": "common_equity",
        "market_code": "CN_A",
        "exchange_code_namespace": "ISO_MIC",
        "exchange_code": "XSHE",
        "currency_code": "CNY",
        "listing_date": "1991-04-03",
        "delisting_date": None,
        "listing_status": "active",
        "recorded_by": "postgres-test",
        "information_cutoff_date": "2026-07-22",
        "recorded_at_utc": "2026-07-22T10:00:00Z",
    }


def test_postgres_0012_to_head_and_empty_round_trip(postgres_database_url: str):
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", postgres_database_url)
    engine = build_engine(postgres_database_url)
    try:
        command.downgrade(config, "20260721_0012")
        assert "listed_instruments" not in inspect(engine).get_table_names()
        command.upgrade(config, "head")
        assert set(
            name for name in inspect(engine).get_table_names() if name.startswith("canonical_price")
        ) == {
            "canonical_price_series",
            "canonical_price_series_revisions",
            "canonical_prices",
            "canonical_price_revisions",
        }
        with engine.connect() as connection:
            assert connection.scalar(text("SELECT version_num FROM alembic_version")) == "20260722_0013"
    finally:
        engine.dispose()


def test_postgres_concurrent_first_revision_fails_closed(postgres_database_url: str):
    engine = build_engine(postgres_database_url)
    factory = build_session_factory(engine)

    def record(_: int):
        try:
            return CanonicalPriceCommandService(factory).record_listed_instrument(_instrument_input())
        except CanonicalPriceError as exc:
            return exc.code

    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(record, (1, 2)))
        assert sum(isinstance(item, dict) for item in results) == 1
        assert "canonical_revision_conflict" in results
        with factory() as session:
            assert session.scalar(select(func.count()).select_from(ListedInstrument)) == 1
            assert session.scalar(select(func.count()).select_from(ListedInstrumentRevision)) == 1
    finally:
        engine.dispose()
