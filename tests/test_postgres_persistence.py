from __future__ import annotations

import os
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from threading import Barrier, local

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import func, inspect, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import IntegrityError

from backend.database.engine import build_engine, build_session_factory
import backend.database.market_data as market_data_module
from backend.database.market_data import FAILED, MarketDataPersistenceService, MarketDataRepository, MarketDataValidationError
from backend.database.models import DailyPriceRecord, IngestionRun, StockBasicRecord, TradeCalendarRecord
from datasource.base import MarketDataBundle
from datasource.fixtures import (
    FIXTURE_CUTOFF_DATE,
    FIXTURE_END_DATE,
    FIXTURE_PROVIDER,
    FIXTURE_SCOPE,
    FIXTURE_START_DATE,
    build_market_data_fixture,
)
from market_cockpit.fixtures import (
    COCKPIT_FIXTURE_ADJUST_TYPE,
    COCKPIT_FIXTURE_CURRENT_CUTOFF,
    COCKPIT_FIXTURE_END_DATE,
    COCKPIT_FIXTURE_HISTORICAL_CUTOFF,
    COCKPIT_FIXTURE_PROVIDER,
    COCKPIT_FIXTURE_SCOPE,
    COCKPIT_FIXTURE_START_DATE,
    build_market_cockpit_fixture,
)
from market_cockpit.repository import MarketCockpitRepository, MarketCockpitSelectionError
from market_cockpit.service import MarketCockpitService


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


@pytest.fixture(autouse=True)
def clean_postgres_tables(postgres_database_url: str) -> Iterator[None]:
    engine = build_engine(postgres_database_url)
    try:
        with engine.begin() as connection:
            connection.execute(
                text(
                    "TRUNCATE TABLE trade_calendar, daily_price, stock_basic, ingestion_runs "
                    "RESTART IDENTITY CASCADE"
                )
            )
        yield
    finally:
        engine.dispose()


def _ingest(
    service: MarketDataPersistenceService,
    bundle: MarketDataBundle | None = None,
    *,
    cutoff: str = FIXTURE_CUTOFF_DATE,
    scope: dict | None = None,
    start_date: str = FIXTURE_START_DATE,
    end_date: str = FIXTURE_END_DATE,
    adjust_type: str | None = None,
):
    return service.ingest_bundle(
        bundle or build_market_data_fixture(),
        provider=FIXTURE_PROVIDER,
        requested_start_date=start_date,
        requested_end_date=end_date,
        information_cutoff_date=cutoff,
        requested_scope=scope or FIXTURE_SCOPE,
        adjust_type=adjust_type,
    )


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
        first = _ingest(service)
        second = _ingest(service)
        assert first.rows_written == 8
        assert second.rows_written == 0
        assert second.ingestion_run_id == first.ingestion_run_id

        with session_factory() as session:
            assert len(
                MarketDataRepository(session).read_daily_price(
                    FIXTURE_PROVIDER,
                    series_key=first.series_key,
                )
            ) == 4
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


def test_postgres_cutoff_completion_and_run_id_version_order(postgres_database_url: str) -> None:
    engine = build_engine(postgres_database_url)
    session_factory = build_session_factory(engine)
    service = MarketDataPersistenceService(session_factory)
    try:
        high_bundle = build_market_data_fixture()
        high_bundle.stock_basic.loc[0, "stock_name"] = "Cutoff 20260710"
        high = _ingest(service, high_bundle, cutoff="20260710")
        low_bundle = build_market_data_fixture()
        low_bundle.stock_basic.loc[0, "stock_name"] = "Cutoff 20260709 imported later"
        _ingest(service, low_bundle, cutoff="20260709")

        with session_factory() as session:
            repository = MarketDataRepository(session)
            current = repository.read_stock_basic(FIXTURE_PROVIDER, series_key=high.series_key)
            historical = repository.read_stock_basic(
                FIXTURE_PROVIDER,
                series_key=high.series_key,
                as_of_cutoff="20260709",
            )
        assert current.loc[current["stock_code"] == "000001", "stock_name"].item() == "Cutoff 20260710"
        assert historical.loc[historical["stock_code"] == "000001", "stock_name"].item() == (
            "Cutoff 20260709 imported later"
        )

        revision_bundle = build_market_data_fixture()
        revision_bundle.stock_basic.loc[0, "stock_name"] = "Same-cutoff revision"
        revision = _ingest(service, revision_bundle, cutoff="20260710")
        tied_completion = datetime(2026, 7, 18, tzinfo=timezone.utc)
        with session_factory.begin() as session:
            high_run = session.get(IngestionRun, high.ingestion_run_id)
            revision_run = session.get(IngestionRun, revision.ingestion_run_id)
            assert high_run is not None and revision_run is not None
            high_run.completed_at = tied_completion
            revision_run.completed_at = tied_completion
        with session_factory() as session:
            current = MarketDataRepository(session).read_stock_basic(
                FIXTURE_PROVIDER,
                series_key=high.series_key,
            )
        assert current.loc[current["stock_code"] == "000001", "stock_name"].item() == "Same-cutoff revision"
    finally:
        engine.dispose()


def test_postgres_incompatible_scope_date_and_adjustment_series_are_isolated(
    postgres_database_url: str,
) -> None:
    engine = build_engine(postgres_database_url)
    session_factory = build_session_factory(engine)
    service = MarketDataPersistenceService(session_factory)
    try:
        full = _ingest(service)
        fixture = build_market_data_fixture()
        one_stock = MarketDataBundle(
            stock_basic=fixture.stock_basic.loc[fixture.stock_basic["stock_code"] == "000001"].copy(),
            daily_price=fixture.daily_price.loc[fixture.daily_price["stock_code"] == "000001"].copy(),
            trade_calendar=fixture.trade_calendar.copy(),
        )
        one_stock_result = _ingest(
            service,
            one_stock,
            scope={"datasets": list(FIXTURE_SCOPE["datasets"]), "stock_codes": ["000001"]},
        )
        one_day = MarketDataBundle(
            stock_basic=fixture.stock_basic.copy(),
            daily_price=fixture.daily_price.loc[fixture.daily_price["trade_date"] == "20260709"].copy(),
            trade_calendar=fixture.trade_calendar.loc[fixture.trade_calendar["trade_date"] == "20260709"].copy(),
        )
        one_day_result = _ingest(service, one_day, start_date="20260709", end_date="20260709")
        qfq = build_market_data_fixture()
        qfq.daily_price.loc[:, "adjust_type"] = "qfq"
        qfq_result = _ingest(service, qfq, adjust_type="qfq")

        assert len({full.series_key, one_stock_result.series_key, one_day_result.series_key, qfq_result.series_key}) == 4
        with session_factory() as session:
            repository = MarketDataRepository(session)
            assert len(repository.read_stock_basic(FIXTURE_PROVIDER, series_key=full.series_key)) == 2
            assert len(
                repository.read_stock_basic(FIXTURE_PROVIDER, series_key=one_stock_result.series_key)
            ) == 1
            assert len(repository.read_daily_price(FIXTURE_PROVIDER, series_key=one_day_result.series_key)) == 2
            assert set(
                repository.read_daily_price(FIXTURE_PROVIDER, series_key=qfq_result.series_key)["adjust_type"]
            ) == {"qfq"}
    finally:
        engine.dispose()


def test_postgres_failed_attempt_remains_auditable_when_retry_succeeds(
    postgres_database_url: str, monkeypatch
) -> None:
    engine = build_engine(postgres_database_url)
    session_factory = build_session_factory(engine)
    service = MarketDataPersistenceService(session_factory)
    original_insert = market_data_module._insert_bundle

    def fail_insert(*_args, **_kwargs) -> None:
        raise RuntimeError("injected PostgreSQL attempt failure")

    try:
        monkeypatch.setattr(market_data_module, "_insert_bundle", fail_insert)
        with pytest.raises(RuntimeError, match="injected PostgreSQL attempt failure"):
            _ingest(service)
        monkeypatch.setattr(market_data_module, "_insert_bundle", original_insert)

        successful = _ingest(service)
        duplicate = _ingest(service)
        with session_factory() as session:
            runs = session.scalars(select(IngestionRun).order_by(IngestionRun.id)).all()
            assert [run.status for run in runs] == [FAILED, "succeeded"]
            assert runs[0].completed_at is not None
            assert runs[0].error_summary == "RuntimeError: injected PostgreSQL attempt failure"
            assert runs[0].batch_identifier == runs[1].batch_identifier
            assert duplicate.ingestion_run_id == successful.ingestion_run_id == runs[1].id
            assert duplicate.rows_written == 0
            assert session.scalar(select(func.count()).select_from(StockBasicRecord)) == 2
    finally:
        monkeypatch.setattr(market_data_module, "_insert_bundle", original_insert)
        engine.dispose()


def test_postgres_concurrent_identical_batch_has_one_successful_version(
    postgres_database_url: str, monkeypatch
) -> None:
    engine = build_engine(postgres_database_url)
    session_factory = build_session_factory(engine)
    original_find = MarketDataPersistenceService._find_successful_run
    both_initial_checks_complete = Barrier(2)
    thread_state = local()

    def synchronized_initial_find(self, batch_identifier, series_key):
        result = original_find(self, batch_identifier, series_key)
        if not getattr(thread_state, "initial_check_complete", False):
            thread_state.initial_check_complete = True
            both_initial_checks_complete.wait(timeout=10)
        return result

    monkeypatch.setattr(MarketDataPersistenceService, "_find_successful_run", synchronized_initial_find)
    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(lambda _index: _ingest(MarketDataPersistenceService(session_factory)), range(2)))

        assert len({result.ingestion_run_id for result in results}) == 1
        assert sorted(result.rows_written for result in results) == [0, 8]
        assert sorted(result.idempotent for result in results) == [False, True]
        with session_factory() as session:
            runs = session.scalars(select(IngestionRun).order_by(IngestionRun.id)).all()
            assert [run.status for run in runs].count("succeeded") == 1
            assert [run.status for run in runs].count(FAILED) == 1
            assert session.scalar(select(func.count()).select_from(StockBasicRecord)) == 2
            assert session.scalar(select(func.count()).select_from(DailyPriceRecord)) == 4
            assert session.scalar(select(func.count()).select_from(TradeCalendarRecord)) == 2
    finally:
        monkeypatch.setattr(MarketDataPersistenceService, "_find_successful_run", original_find)
        engine.dispose()


@pytest.mark.parametrize("calendar_failure", ["missing", "closed"])
def test_postgres_calendar_reconciliation_rejects_entire_batch(
    postgres_database_url: str, calendar_failure: str
) -> None:
    engine = build_engine(postgres_database_url)
    session_factory = build_session_factory(engine)
    service = MarketDataPersistenceService(session_factory)
    bundle = build_market_data_fixture()
    if calendar_failure == "missing":
        bundle = MarketDataBundle(
            stock_basic=bundle.stock_basic,
            daily_price=bundle.daily_price,
            trade_calendar=bundle.trade_calendar.loc[bundle.trade_calendar["trade_date"] != "20260709"].copy(),
        )
        message = "missing from trade_calendar"
    else:
        bundle.trade_calendar.loc[bundle.trade_calendar["trade_date"] == "20260709", "is_open"] = False
        message = "must be open"
    try:
        with pytest.raises(MarketDataValidationError, match=message):
            _ingest(service, bundle)
        with session_factory() as session:
            assert session.scalar(select(func.count()).select_from(StockBasicRecord)) == 0
            assert session.scalar(select(func.count()).select_from(DailyPriceRecord)) == 0
            assert session.scalar(select(func.count()).select_from(TradeCalendarRecord)) == 0
    finally:
        engine.dispose()


def test_postgres_market_cockpit_current_and_historical_cutoff_use_one_series(
    postgres_database_url: str,
) -> None:
    engine = build_engine(postgres_database_url)
    session_factory = build_session_factory(engine)
    persistence = MarketDataPersistenceService(session_factory)
    try:
        historical = persistence.ingest_bundle(
            build_market_cockpit_fixture(revision="historical"),
            provider=COCKPIT_FIXTURE_PROVIDER,
            requested_start_date=COCKPIT_FIXTURE_START_DATE,
            requested_end_date=COCKPIT_FIXTURE_END_DATE,
            information_cutoff_date=COCKPIT_FIXTURE_HISTORICAL_CUTOFF,
            requested_scope=COCKPIT_FIXTURE_SCOPE,
            adjust_type=COCKPIT_FIXTURE_ADJUST_TYPE,
        )
        current = persistence.ingest_bundle(
            build_market_cockpit_fixture(revision="current"),
            provider=COCKPIT_FIXTURE_PROVIDER,
            requested_start_date=COCKPIT_FIXTURE_START_DATE,
            requested_end_date=COCKPIT_FIXTURE_END_DATE,
            information_cutoff_date=COCKPIT_FIXTURE_CURRENT_CUTOFF,
            requested_scope=COCKPIT_FIXTURE_SCOPE,
            adjust_type=COCKPIT_FIXTURE_ADJUST_TYPE,
        )
        assert current.series_key == historical.series_key

        with session_factory() as session:
            repository = MarketCockpitRepository(session)
            service = MarketCockpitService(repository)
            current_view = service.build_snapshot(series_key=current.series_key)
            historical_view = service.build_snapshot(
                series_key=current.series_key,
                as_of_cutoff=COCKPIT_FIXTURE_HISTORICAL_CUTOFF,
            )
            with pytest.raises(MarketCockpitSelectionError, match="provider-only"):
                repository.load_snapshot()

        assert current_view.provenance.ingestion_run_id == current.ingestion_run_id
        assert historical_view.provenance.ingestion_run_id == historical.ingestion_run_id
        assert current_view.provenance.series_key == historical_view.provenance.series_key
        assert current_view.provenance.adjust_type == "qfq"
        assert current_view.completeness_status == "ready"
        assert historical_view.completeness_status == "ready"
    finally:
        engine.dispose()
