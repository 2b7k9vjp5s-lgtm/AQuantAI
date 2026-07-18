from __future__ import annotations

import socket
from collections.abc import Callable, Iterator
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from sqlalchemy import create_engine, event, func, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from backend.database.engine import build_session_factory
from backend.database.market_data import (
    FAILED,
    MarketDataPersistenceService,
    MarketDataRepository,
    MarketDataValidationError,
)
from backend.database.models import Base, DailyPriceRecord, IngestionRun, StockBasicRecord, TradeCalendarRecord
from datasource.base import DAILY_PRICE_COLUMNS, STOCK_BASIC_COLUMNS, TRADE_CALENDAR_COLUMNS, MarketDataBundle
from datasource.fixtures import (
    FIXTURE_CUTOFF_DATE,
    FIXTURE_END_DATE,
    FIXTURE_PROVIDER,
    FIXTURE_SCOPE,
    FIXTURE_START_DATE,
    build_market_data_fixture,
)
from scripts.persist_fixture_market_data import persist_fixture_market_data


@pytest.fixture
def database() -> Iterator[tuple[Engine, sessionmaker[Session]]]:
    engine = create_engine("sqlite+pysqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def _enable_foreign_keys(dbapi_connection, _connection_record) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    yield engine, build_session_factory(engine)
    engine.dispose()


def _ingest(
    session_factory: sessionmaker[Session],
    bundle: MarketDataBundle | None = None,
    *,
    cutoff: str = FIXTURE_CUTOFF_DATE,
    scope: dict | None = None,
):
    return MarketDataPersistenceService(session_factory).ingest_bundle(
        bundle or build_market_data_fixture(),
        provider=FIXTURE_PROVIDER,
        requested_start_date=FIXTURE_START_DATE,
        requested_end_date=FIXTURE_END_DATE,
        information_cutoff_date=cutoff,
        requested_scope=scope or FIXTURE_SCOPE,
    )


def test_fixture_import_reconstructs_normalized_contracts_in_deterministic_order(database) -> None:
    _, session_factory = database
    bundle = build_market_data_fixture()
    shuffled = MarketDataBundle(
        stock_basic=bundle.stock_basic.iloc[::-1].reset_index(drop=True),
        daily_price=bundle.daily_price.iloc[::-1].reset_index(drop=True),
        trade_calendar=bundle.trade_calendar.iloc[::-1].reset_index(drop=True),
    )

    result = _ingest(session_factory, shuffled)

    assert result.status == "succeeded"
    assert result.rows_received == 8
    assert result.rows_written == 8
    with session_factory() as session:
        repository = MarketDataRepository(session)
        stock_basic = repository.read_stock_basic(FIXTURE_PROVIDER)
        daily_price = repository.read_daily_price(FIXTURE_PROVIDER)
        trade_calendar = repository.read_trade_calendar(FIXTURE_PROVIDER)

    assert list(stock_basic.columns) == STOCK_BASIC_COLUMNS
    assert stock_basic["stock_code"].tolist() == ["000001", "600000"]
    assert list(daily_price.columns) == DAILY_PRICE_COLUMNS
    assert daily_price[["trade_date", "stock_code"]].values.tolist() == [
        ["20260708", "000001"],
        ["20260708", "600000"],
        ["20260709", "000001"],
        ["20260709", "600000"],
    ]
    assert list(trade_calendar.columns) == TRADE_CALENDAR_COLUMNS
    assert trade_calendar["trade_date"].tolist() == ["20260708", "20260709"]


def test_second_import_is_idempotent_and_writes_no_rows(database) -> None:
    _, session_factory = database

    first = _ingest(session_factory)
    second = _ingest(session_factory)

    assert second.ingestion_run_id == first.ingestion_run_id
    assert second.batch_identifier == first.batch_identifier
    assert second.idempotent is True
    assert second.rows_written == 0
    with session_factory() as session:
        assert session.scalar(select(func.count()).select_from(IngestionRun)) == 1
        assert session.scalar(select(func.count()).select_from(StockBasicRecord)) == 2
        assert session.scalar(select(func.count()).select_from(DailyPriceRecord)) == 4
        assert session.scalar(select(func.count()).select_from(TradeCalendarRecord)) == 2


def test_ingestion_run_tracks_scope_cutoff_contract_and_counts(database) -> None:
    _, session_factory = database

    result = _ingest(session_factory)

    with session_factory() as session:
        run = session.get(IngestionRun, result.ingestion_run_id)
        assert run is not None
        assert run.provider == FIXTURE_PROVIDER
        assert run.dataset == "market_data_bundle"
        assert run.information_cutoff_date.strftime("%Y%m%d") == FIXTURE_CUTOFF_DATE
        assert run.requested_scope == {
            "datasets": ["daily_price", "stock_basic", "trade_calendar"],
            "stock_codes": ["000001", "600000"],
            "stock_code_semantics": "exact",
            "snapshot_mode": "complete",
        }
        assert run.snapshot_mode == "complete"
        assert run.contract_version == "1.0"
        assert run.dataset_counts == {"stock_basic": 2, "daily_price": 4, "trade_calendar": 2}
        assert run.row_count_received == 8
        assert run.row_count_written == 8


def _missing_stock_code(bundle: MarketDataBundle) -> None:
    bundle.stock_basic.loc[0, "stock_code"] = pd.NA


def _duplicate_daily_price(bundle: MarketDataBundle) -> None:
    bundle.daily_price.loc[len(bundle.daily_price)] = bundle.daily_price.iloc[0]


def _non_finite_price(bundle: MarketDataBundle) -> None:
    bundle.daily_price.loc[0, "close"] = np.inf


def _wrong_source(bundle: MarketDataBundle) -> None:
    bundle.trade_calendar.loc[0, "source"] = "other"


@pytest.mark.parametrize(
    "mutator",
    (_missing_stock_code, _duplicate_daily_price, _non_finite_price, _wrong_source),
)
def test_invalid_batches_are_rejected_without_market_rows(
    database, mutator: Callable[[MarketDataBundle], None]
) -> None:
    _, session_factory = database
    bundle = build_market_data_fixture()
    mutator(bundle)

    with pytest.raises(MarketDataValidationError):
        _ingest(session_factory, bundle)

    with session_factory() as session:
        run = session.scalar(select(IngestionRun))
        assert run is not None
        assert run.status == FAILED
        assert run.row_count_written == 0
        assert run.error_summary
        assert session.scalar(select(func.count()).select_from(StockBasicRecord)) == 0
        assert session.scalar(select(func.count()).select_from(DailyPriceRecord)) == 0
        assert session.scalar(select(func.count()).select_from(TradeCalendarRecord)) == 0


def test_database_failure_rolls_back_entire_batch(database) -> None:
    _, session_factory = database

    def fail_daily_insert(_mapper, _connection, _target) -> None:
        raise RuntimeError("injected daily insert failure")

    event.listen(DailyPriceRecord, "before_insert", fail_daily_insert)
    try:
        with pytest.raises(RuntimeError, match="injected daily insert failure"):
            _ingest(session_factory)
    finally:
        event.remove(DailyPriceRecord, "before_insert", fail_daily_insert)

    with session_factory() as session:
        run = session.scalar(select(IngestionRun))
        assert run is not None
        assert run.status == FAILED
        assert run.row_count_written == 0
        assert session.scalar(select(func.count()).select_from(StockBasicRecord)) == 0
        assert session.scalar(select(func.count()).select_from(DailyPriceRecord)) == 0
        assert session.scalar(select(func.count()).select_from(TradeCalendarRecord)) == 0


def test_failed_attempt_is_immutable_and_successful_retry_is_a_new_attempt(database) -> None:
    _, session_factory = database

    def fail_daily_insert(_mapper, _connection, _target) -> None:
        raise RuntimeError("injected first-attempt failure")

    event.listen(DailyPriceRecord, "before_insert", fail_daily_insert)
    try:
        with pytest.raises(RuntimeError, match="injected first-attempt failure"):
            _ingest(session_factory)
    finally:
        event.remove(DailyPriceRecord, "before_insert", fail_daily_insert)

    successful = _ingest(session_factory)
    duplicate = _ingest(session_factory)

    with session_factory() as session:
        runs = session.scalars(select(IngestionRun).order_by(IngestionRun.id)).all()
        assert len(runs) == 2
        failed, succeeded = runs
        assert failed.status == FAILED
        assert failed.completed_at is not None
        assert failed.error_summary == "RuntimeError: injected first-attempt failure"
        assert succeeded.status == "succeeded"
        assert failed.id != succeeded.id
        assert failed.batch_identifier == succeeded.batch_identifier
        assert duplicate.ingestion_run_id == succeeded.id == successful.ingestion_run_id
        assert duplicate.rows_written == 0
        assert duplicate.idempotent is True


def test_cutoff_then_completion_then_run_id_selects_current_and_as_of_versions(database) -> None:
    _, session_factory = database
    high_cutoff = build_market_data_fixture()
    high_cutoff.stock_basic.loc[0, "stock_name"] = "Cutoff 20260710"
    high = _ingest(session_factory, high_cutoff, cutoff="20260710")
    low_cutoff = build_market_data_fixture()
    low_cutoff.stock_basic.loc[0, "stock_name"] = "Cutoff 20260709 imported later"
    low = _ingest(session_factory, low_cutoff, cutoff="20260709")

    with session_factory() as session:
        repository = MarketDataRepository(session)
        current = repository.read_stock_basic(FIXTURE_PROVIDER)
        historical = repository.read_stock_basic(FIXTURE_PROVIDER, as_of_cutoff="20260709")
    assert current.loc[current["stock_code"] == "000001", "stock_name"].item() == "Cutoff 20260710"
    assert historical.loc[historical["stock_code"] == "000001", "stock_name"].item() == (
        "Cutoff 20260709 imported later"
    )

    same_cutoff_revision = build_market_data_fixture()
    same_cutoff_revision.stock_basic.loc[0, "stock_name"] = "Same-cutoff revision"
    revision = _ingest(session_factory, same_cutoff_revision, cutoff="20260710")
    tied_completion = datetime(2026, 7, 18, tzinfo=timezone.utc)
    with session_factory.begin() as session:
        session.get(IngestionRun, high.ingestion_run_id).completed_at = tied_completion
        session.get(IngestionRun, revision.ingestion_run_id).completed_at = tied_completion
    with session_factory() as session:
        repository = MarketDataRepository(session)
        current = repository.read_stock_basic(FIXTURE_PROVIDER)
        versions = repository.stock_basic_versions(FIXTURE_PROVIDER, "000001")
    assert current.loc[current["stock_code"] == "000001", "stock_name"].item() == "Same-cutoff revision"
    assert [version["ingestion_run_id"] for version in versions] == [
        low.ingestion_run_id,
        high.ingestion_run_id,
        revision.ingestion_run_id,
    ]
    assert len({version["batch_identifier"] for version in versions}) == 3


def test_complete_snapshot_does_not_carry_forward_keys_omitted_by_new_exact_scope(database) -> None:
    _, session_factory = database
    _ingest(session_factory)
    fixture = build_market_data_fixture()
    one_stock = MarketDataBundle(
        stock_basic=fixture.stock_basic.loc[fixture.stock_basic["stock_code"] == "000001"].copy(),
        daily_price=fixture.daily_price.loc[fixture.daily_price["stock_code"] == "000001"].copy(),
        trade_calendar=fixture.trade_calendar.copy(),
    )
    one_stock_scope = {
        "datasets": sorted(FIXTURE_SCOPE["datasets"]),
        "stock_codes": ["000001"],
    }

    _ingest(session_factory, one_stock, cutoff="20260710", scope=one_stock_scope)

    with session_factory() as session:
        repository = MarketDataRepository(session)
        current = repository.read_stock_basic(FIXTURE_PROVIDER)
        historical = repository.read_stock_basic(FIXTURE_PROVIDER, as_of_cutoff="20260709")
    assert current["stock_code"].tolist() == ["000001"]
    assert historical["stock_code"].tolist() == ["000001", "600000"]


def test_requested_stock_codes_are_an_exact_scope(database) -> None:
    _, session_factory = database
    one_stock_scope = {
        "datasets": sorted(FIXTURE_SCOPE["datasets"]),
        "stock_codes": ["000001"],
    }

    with pytest.raises(MarketDataValidationError, match="must exactly match"):
        _ingest(session_factory, scope=one_stock_scope)

    with session_factory() as session:
        assert session.scalar(select(func.count()).select_from(StockBasicRecord)) == 0
        assert session.scalar(select(func.count()).select_from(DailyPriceRecord)) == 0
        assert session.scalar(select(func.count()).select_from(TradeCalendarRecord)) == 0


def test_partial_scope_or_snapshot_semantics_are_rejected(database) -> None:
    _, session_factory = database
    incompatible_scope = {
        **FIXTURE_SCOPE,
        "stock_code_semantics": "upper_bound",
        "snapshot_mode": "partial",
    }

    with pytest.raises(MarketDataValidationError, match="stock_code_semantics must be 'exact'"):
        _ingest(session_factory, scope=incompatible_scope)


@pytest.mark.parametrize("calendar_failure", ["missing", "closed"])
def test_daily_price_calendar_reconciliation_rejects_entire_batch(database, calendar_failure: str) -> None:
    _, session_factory = database
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

    with pytest.raises(MarketDataValidationError, match=message):
        _ingest(session_factory, bundle)

    with session_factory() as session:
        assert session.scalar(select(func.count()).select_from(StockBasicRecord)) == 0
        assert session.scalar(select(func.count()).select_from(DailyPriceRecord)) == 0
        assert session.scalar(select(func.count()).select_from(TradeCalendarRecord)) == 0


def test_fixture_command_runs_twice_without_network_or_duplicate_rows(tmp_path: Path, monkeypatch) -> None:
    database_path = tmp_path / "fixture.sqlite3"
    database_url = f"sqlite+pysqlite:///{database_path.as_posix()}"
    engine = create_engine(database_url)
    Base.metadata.create_all(engine)
    engine.dispose()

    def reject_network(*_args, **_kwargs):
        raise AssertionError("fixture persistence attempted network access")

    monkeypatch.setattr(socket, "create_connection", reject_network)
    monkeypatch.setattr(socket.socket, "connect", reject_network)

    first = persist_fixture_market_data(database_url)
    second = persist_fixture_market_data(database_url)

    assert first["rows_written"] == 8
    assert first["idempotent"] is False
    assert second["rows_written"] == 0
    assert second["idempotent"] is True
    assert second["ingestion_run_id"] == first["ingestion_run_id"]
    assert second["readback_counts"] == {"stock_basic": 2, "daily_price": 4, "trade_calendar": 2}
